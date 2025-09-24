import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from config import settings
import ipaddress

BASE_HEADERS = {
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
  "Accept-Language": settings.scraper_accept_language,
  "Referer": "https://www.google.com/",
  "Connection": "keep-alive",
  "Upgrade-Insecure-Requests": "1"
}




# --- Utilidades anti-SSRF y restricción de dominios ---
def _is_private_ip(host: str) -> bool:
  try:
    # Resolver si es IPv4 literal
    ip = ipaddress.ip_address(host)
    return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
  except ValueError:
    # No es IP literal, puede ser hostname. No resolvemos DNS para mantener simple: bloqueamos hostnames especiales.
    lowered = host.lower()
    if lowered in {"localhost"} or lowered.endswith(".local"):
      return True
    return False


def _is_http_url(url: str) -> bool:
  try:
    p = urlparse(url)
    return p.scheme in ("http", "https") and bool(p.netloc)
  except Exception:
    return False

"""
A class to scrape HTML content from a given URL and extract text using BeautifulSoup.
"""
class Scraper:

  """
  Initializes the Scraper with a URL.
  :param url: The URL to scrape.
  :param accept_language: Optional override for Accept-Language header.
  """
  def __init__(self, url: str, accept_language: str | None = None):
    self.url = url
    self.accept_language = accept_language

  """
  Fetches the HTML content from the URL.
  :return: The HTML content as a string.
  :raises Exception: If there is an error fetching the URL.
  """

  async def fetch(self):
    # Validación simple para evitar SSRF hacia IPs/hosts internos
    if not _is_http_url(self.url):
      raise Exception(f"Invalid URL scheme or host: {self.url}")
    parsed = urlparse(self.url)
    if _is_private_ip(parsed.hostname or ""):
      raise Exception(f"Blocked private/loopback host: {parsed.hostname}")

    headers = dict(BASE_HEADERS)
    if self.accept_language:
      headers["Accept-Language"] = self.accept_language

    async with httpx.AsyncClient() as client:
      try:
        response = await client.get(self.url, headers=headers, timeout=10, follow_redirects=True)
        response.raise_for_status()
        return response.text
      except (httpx.RequestError, httpx.HTTPStatusError) as e:
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

    # Extract links (limitados y del mismo dominio registrable básico)
    links = set()
    try:
      base = urlparse(self.url)
      base_host = (base.hostname or "").lower()
    except Exception:
      base_host = ""

    MAX_LINKS = 8
    for link in soup.find_all("a", href=True):
      if len(links) >= MAX_LINKS:
        break
      full_url = urljoin(self.url, link["href"]) if link["href"] else None
      if not full_url or not _is_http_url(full_url):
        continue
      p = urlparse(full_url)
      host = (p.hostname or "").lower()
      # Evitar hosts privados/loopback
      if _is_private_ip(host):
        continue
      # Restringir a mismo host base (con y sin www)
      same = (host == base_host)
      if base_host.startswith("www."):
        same = same or (host == base_host[4:])
      if host.startswith("www."):
        same = same or (host[4:] == base_host)
      if not same:
        continue
      links.add(full_url)

    return {
      "url": self.url,
      "title": title,
      "text": text,
      "links": list(links)
    }