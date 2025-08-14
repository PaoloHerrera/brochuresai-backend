
class Prompts:
    def get_links_system_prompt(self) -> str:
        link_system_prompt = "You are provided with a list of links found on a webpage. \
        You are able to decide which of the links would be most relevant to include in a brochure about the company, \
        such as links to an About page, or a Company page, or Careers/Jobs pages.\n"
        link_system_prompt += "You should respond in JSON, but without the mark JSON as in this example:"
        link_system_prompt += """
        {
            "links": [
                {"type": "about page", "url": "https://full.url/goes/here/about"},
                {"type": "careers page", "url": "https://another.full.url/careers"}
            ]
        }
        """
        return link_system_prompt
    
    def get_links_user_prompt(self, content) -> str:
        user_prompt = f"Here is the list of links on the website of {content['url']} - "
        user_prompt += "please decide which of these are relevant web links for a brochure about the company, respond with the full https URL in JSON format. \
            Do not include Terms of Service, Privacy, email links.\n"
        user_prompt += "Links (some might be relative links):\n"
        user_prompt += "\n".join(content['links'])
        return user_prompt

    def brochure_system_prompt_professional(self, language: str) -> str:
        brochure_system_prompt = f"You are an assistant that analyzes the contents of several relevant pages from a company website \
        and creates a short brochure about the company for prospective customers, investors and recruits. Respond in HTML format with beautiful formatting and beauty CSS. \
        Use professional emojis if you want \
        The brochure must be written in {language}.  \
        Include details of company culture, customers and careers/jobs if you have the information.\n"
        brochure_system_prompt += "If you want add social media or external links, so you should add external links in HTML. If you can't don't do it. \n"
        brochure_system_prompt += "Omits your comments and HTML markdown, only give me the HTML and CSS.\n"
        brochure_system_prompt += "You must consider that the brochure will be a PDF document, so external links not must fail.\n"
        brochure_system_prompt += "Important: The brochure must be in only one page when it is printed, so don't use more than one page. Keep the brochure short and concise. Limit: 800-1000 words approximately.\n"

        return brochure_system_prompt

    def brochure_system_prompt_funny(self, language: str) -> str:
        brochure_system_prompt = f"You are an assistant that analyzes the contents of several relevant pages from a company website \
        and creates a short humorous, entertaining, jokey brochure about the company for prospective customers, investors and recruits. Respond in HTML format with beautiful formatting and beauty CSS.\
        Use funny emojis if you want \
        The brochure must be written in {language}.  \
        Include details of company culture, customers and careers/jobs if you have the information.\n"
        brochure_system_prompt += "If you want add social media or external links, so you should add external links in HTML. If you can't don't do it. \n"
        brochure_system_prompt += "Omits your comments and HTML markdown, only give me the HTML and CSS.\n"
        brochure_system_prompt += "You must consider that the brochure will be a PDF document, so external links not must fail.\n"
        brochure_system_prompt += "Important: The brochure must be in only one page when it is printed, so don't use more than one page. Keep the brochure short and concise. Limit: 800-1000 words approximately.\n"
        
        return brochure_system_prompt

    def get_brochure_user_prompt(self, company_name, details, language: str) -> str:
        user_prompt = f"You are looking at a company called: {company_name}\n"
        user_prompt += f"Here are the contents of its landing page and other relevant pages; use this information to build a short brochure of the company in beautiful HTML format and in {language} language.\n"
        user_prompt += details
        user_prompt = user_prompt[:30_000] # Truncate if more than 30,000 characters
        return user_prompt