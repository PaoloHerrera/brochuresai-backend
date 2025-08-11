import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

headers = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}


"""
A class to scrape HTML content from a given URL and extract text using BeautifulSoup.
"""

class Scraper:

  """
  Initializes the Scraper with a URL.
  :param url: The URL to scrape.
  """
  def __init__(self, url: str):
    self.url = url
  
  """
  Fetches the HTML content from the URL.
  :return: The HTML content as a string.
  :raises Exception: If there is an error fetching the URL.
  """

  async def fetch(self):
    async with httpx.AsyncClient() as client:

      try:
        response = await client.get(self.url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
      except httpx.RequestError as e:
        raise Exception(f"Error fetching {self.url}: {e}")


  """
  Gets the content of the page, including title, text, and links.
  :return: A dictionary containing the URL, title, text, and links.
  :raises Exception: If there is an error processing the content.
  """

  async def get_content(self):

    html = await self.fetch()
    soup = BeautifulSoup(html, "html.parser")
  
    title = soup.title.string.strip() if soup.title and soup.title.string else "No title"

    for irrelevant in soup(["script", "style", "img", "input"]):
      irrelevant.decompose()
    
    if not soup.body:
      text = "No content"
    else:
      text = soup.body.get_text(separator="\n").strip()

    # Extract links
    links = set() # Use a set to avoid duplicate links
    for link in soup.find_all("a", href=True):
      full_url = urljoin(self.url, link["href"])
      links.add(full_url)

    return {
      "url": self.url,
      "title": title,
      "text": text,
      "links": list(links)
    }