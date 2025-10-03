from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from services.common.config import (
    SCRAPER_DEFAULT_TIMEOUT,
    SCRAPER_LOG_VERBOSE,
    get_base_headers,
)
from services.common.link_utils import (
    filter_social_media_links,
    is_http_url,
    is_irrelevant_link,
    is_private_ip,
    normalize_url,
)
from services.common.social import is_social_host
from services.logging.dev_logger import get_logger

# Headers base ahora se construyen vía helper compartido en services.common.config

logger = get_logger(__name__)


def _is_social_host(host: str) -> bool:
    """Proxy a helper compartido para determinar si un host es social."""
    return is_social_host(host)


# --- Utilidades anti-SSRF y restricción de dominios ---
def _is_private_ip(host: str) -> bool:
    return is_private_ip(host)


def _is_http_url(url: str) -> bool:
    return is_http_url(url)


def _is_irrelevant_link(url: str, base_domain: str) -> bool:
    return is_irrelevant_link(url, base_domain)


def _normalize_url(url: str) -> str:
    return normalize_url(url)


def _score_link(url: str, base_domain: str) -> int:
    """Heurística simple para priorizar enlaces informativos relevantes.

    Preferimos:
    - Enlaces del mismo dominio/subdominio
    - Rutas con palabras clave típicas (about, careers, contact, etc.)
    - Menor profundidad de ruta
    Penalizamos:
    - Query string y fragmentos
    """
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        path = (parsed.path or "").lower()

        score = 0

        # Mismo dominio o subdominio
        if host == base_domain:
            score += 3
        elif host.endswith("." + base_domain) or base_domain.endswith("." + host):
            score += 2

        # Palabras clave comunes de páginas relevantes
        keywords = (
            "about",
            "company",
            "team",
            "careers",
            "jobs",
            "contact",
            "services",
            "solutions",
            "products",
            "clients",
            "portfolio",
            "press",
            "news",
            "blog",
        )
        if any(k in path for k in keywords):
            score += 2

        # Menor profundidad de ruta → mayor puntuación
        segments = [seg for seg in path.split("/") if seg]
        score += max(0, 3 - len(segments))

        # Penalizar query y fragmento
        if parsed.query:
            score -= 1
        if parsed.fragment:
            score -= 1

        return score
    except Exception:
        return 0


def _filter_social_media_links(
    links: list[str], company_domain: str
) -> tuple[list[str], list[str]]:
    """
    Separa enlaces en dos categorías: información relevante y redes sociales específicas.

    Args:
        links: Lista de enlaces extraídos
        company_domain: Dominio base de la empresa

    Returns:
        Tupla con (enlaces_info, enlaces_redes_sociales)
    """
    return filter_social_media_links(links, company_domain)


def _extract_title(soup: BeautifulSoup) -> str:
    """Extrae el título de la página desde <title> o encabezados H1/H2."""
    try:
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        for tag in ("h1", "h2"):
            el = soup.find(tag)
            if el:
                txt = el.get_text(strip=True)
                if txt:
                    return txt
        return ""
    except Exception:
        return ""


def _clean_soup(soup: BeautifulSoup) -> None:
    """Limpia el DOM eliminando elementos que no aportan al texto principal."""
    try:
        for tag in soup(["script", "style", "noscript", "iframe", "object", "embed"]):
            tag.decompose()
    except Exception:
        # Si falla la limpieza, continuamos con el DOM original
        pass


def _extract_text(soup: BeautifulSoup) -> str:
    """Extrae texto visible, normalizando espacios y saltos de línea."""
    try:
        raw = soup.get_text(separator="\n")
        lines = [line.strip() for line in raw.splitlines()]
        # Filtrar líneas vacías y colapsar espacios
        lines = [line for line in lines if line]
        return "\n".join(lines)
    except Exception:
        return ""


def _get_base_host(url: str) -> str:
    """Obtiene el host base (sin www) en minúsculas para comparaciones."""
    try:
        p = urlparse(url)
        host = (p.netloc or p.path or url).lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        return url.lower()


def _collect_links(
    soup: BeautifulSoup,
    base_url: str,
    base_host: str,
) -> set[str]:
    """Recopila enlaces válidos, resolviendo relativos y aplicando filtros básicos.

    - Resuelve enlaces relativos con urljoin
    - Descarta esquemas no http/https
    - Evita SSRF a IPs privadas/loopback
    - Elimina enlaces irrelevantes (feeds, assets, admin, etc.)
    - No aplica una cota superior; el control se realiza con relevancia y
      concurrencia en etapas posteriores
    """
    collected: set[str] = set()
    try:
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href:
                continue

            # Resolver relativos; mantener absolutos
            try:
                candidate = href if _is_http_url(href) else urljoin(base_url, href)
            except Exception:
                candidate = href

            if not _is_http_url(candidate):
                continue

            # Filtrar hosts privados/loopback por seguridad
            try:
                parsed = urlparse(candidate)
                host = parsed.hostname or ""
                if _is_private_ip(host):
                    continue
            except Exception:
                continue

            # Descartar enlaces irrelevantes
            if _is_irrelevant_link(candidate, base_host):
                continue

            collected.add(candidate)
    except Exception:
        # Si algo falla, devolvemos lo acumulado hasta el momento
        pass

    # Reordenar por relevancia para priorizar páginas informativas
    try:
        ranked = sorted(list(collected), key=lambda u: _score_link(u, base_host), reverse=True)
        return set(ranked)
    except Exception:
        return set(collected)


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

        headers = get_base_headers(self.accept_language)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.url,
                    headers=headers,
                    timeout=SCRAPER_DEFAULT_TIMEOUT,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return response.text
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                raise Exception(f"Error fetching {self.url}: {e}") from e

    """
  Gets the content of the page, including title, text, and links.
  :return: A dictionary containing the URL, title, text, and links.
  :raises Exception: If there is an error processing the content.
  """

    async def get_content(self):

        html = await self.fetch()
        soup = BeautifulSoup(html, "html.parser")

        title = _extract_title(soup)
        _clean_soup(soup)
        text = _extract_text(soup)

        base_host = _get_base_host(self.url)
        links = _collect_links(soup, self.url, base_host)

        # Separar enlaces en información y redes sociales específicas

        all_links = list(links)
        info_links, social_links = _filter_social_media_links(all_links, base_host)

        if SCRAPER_LOG_VERBOSE:
            logger.debug("Después del filtrado:")
            logger.debug("   • Enlaces de información: %d", len(info_links))
            logger.debug("   • Enlaces de redes sociales: %d", len(social_links))
            if info_links:
                logger.debug(
                    "   • Info links: %s%s",
                    info_links[:5],
                    "..." if len(info_links) > 5 else "",
                )
            if social_links:
                logger.debug("   • Social links: %s", social_links)

        return {
            "url": self.url,
            "title": title,
            "text": text,
            "info_links": info_links,
            "social_links": social_links,
            "all_links": all_links,
        }
