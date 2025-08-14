import json
import asyncio
from openai import OpenAI
from config import settings
from services.openai.prompts import Prompts
from services.scraper import Scraper

class OpenAIClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.open_ai_api_key)

    def get_client(self):
        return self.client

    async def get_links(self, content):
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model="gpt-5-mini",
                messages=[
                    {"role": "system", "content": Prompts().get_links_system_prompt()},
                    {"role": "user", "content": Prompts().get_links_user_prompt(content)}
                ]
            )
        )
        return response.choices[0].message.content

    async def get_all_details(self, url):
        result = "Landing Page: \n"
        result_dict = await Scraper(url).get_content()
        links = await self.get_links(result_dict)
        
        print("Found links:", links)

        links_json = json.loads(links)

        print("Links JSON: ", links_json)

        
        ## Asynchronously scrape all links
        tasks = [
            Scraper(link["url"]).get_content()
            for link in links_json["links"]
        ]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        for link, page in zip(links_json["links"], pages):
            if isinstance(page, Exception):
                print(f"Error scraping {link['url']}: {page}")
                continue
            result += f"\n\n{link['type']}\n{page.get('text', '')}"
        
        ## Add the links to the result
        result += "\n\nLinks: \n"
        result += "{links}"
        return result

    async def create_brochure(self, company_name, url, language, brochure_type):
        if brochure_type == "funny":
            system_prompt = Prompts().brochure_system_prompt_funny(language)
        else:
            system_prompt = Prompts().brochure_system_prompt_professional(language)

        details = await self.get_all_details(url)
        response = self.client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": Prompts().get_brochure_user_prompt(company_name, details, language)}
            ],
        )
        result = response.choices[0].message.content
        return result