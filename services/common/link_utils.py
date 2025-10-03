import ipaddress
import re
from urllib.parse import urlparse

from services.common.social import is_social_host, is_specific_social_media_link


def is_private_ip(host: str) -> bool:
    """Detecta IPs privadas/loopback o hostnames locales.

    No realiza resolución DNS para hostnames; bloquea "localhost" y dominios .local.
    """
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local
    except ValueError:
        lowered = (host or "").lower()
        if lowered in {"localhost"} or lowered.endswith(".local"):
            return True
        return False


def is_http_url(url: str) -> bool:
    """Valida que la URL tenga esquema http/https y netloc."""
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def is_irrelevant_link(url: str, base_domain: str) -> bool:
    """Heurística para descartar enlaces irrelevantes para el brochure."""
    try:
        parsed = urlparse(url.lower())
        path = parsed.path.strip("/")

        irrelevant_extensions = {
            ".rss",
            ".xml",
            ".json",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".zip",
            ".rar",
            ".tar",
            ".gz",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".svg",
            ".ico",
            ".css",
            ".js",
        }
        for ext in irrelevant_extensions:
            if path.endswith(ext):
                return True

        irrelevant_paths = {
            "rss",
            "rss.xml",
            "feed",
            "feed.xml",
            "sitemap",
            "sitemap.xml",
            "robots.txt",
            "favicon.ico",
            "apple-touch-icon",
            "manifest.json",
            "sw.js",
            "service-worker.js",
            "ads.txt",
            "security.txt",
            "wp-admin",
            "wp-content",
            "wp-includes",
            "admin",
            "login",
            "register",
            "signup",
            "logout",
            "password",
            "forgot",
            "terms",
            "privacy",
            "cookies",
            "legal",
            "disclaimer",
            "search",
            "tag",
            "tags",
            "category",
            "categories",
            "archive",
            "author",
            "date",
            "page",
            "comment",
            "comments",
        }
        if path in irrelevant_paths:
            return True

        irrelevant_patterns = [
            r"^rss/",
            r"^feed/",
            r"^api/",
            r"^wp-",
            r"^admin/",
            r"^user/",
            r"^account/",
            r"^profile/",
            r"^settings/",
            r"^dashboard/",
            r"^search\?",
            r"^tag/",
            r"^category/",
            r"^author/",
            r"^date/",
            r"^page/\d+",
            r"^comment",
            r"^\./.*",
            r"^#",
        ]

        full_url_lower = url.lower()
        if "/rss" in full_url_lower or ".rss" in full_url_lower:
            return True
        if "/./" in full_url_lower:
            return True

        for pattern in irrelevant_patterns:
            if re.match(pattern, path):
                return True

        return False
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normaliza URL para comparación de duplicados (sin fragmentos, sin trailing slash)."""
    try:
        parsed = urlparse(url.lower())
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if normalized.endswith("/") and len(parsed.path) > 1:
            normalized = normalized[:-1]
        return normalized
    except Exception:
        return url.lower()


def is_internal_host(domain: str, base_domain: str) -> bool:
    """Determina si `domain` pertenece al dominio base o a alguno de sus subdominios."""
    try:
        d = (domain or "").lower()
        b = (base_domain or "").lower()
        if d.startswith("www."):
            d = d[4:]
        if b.startswith("www."):
            b = b[4:]
        return d == b or d.endswith("." + b)
    except Exception:
        return False


def filter_social_media_links(links: list[str], company_domain: str) -> tuple[list[str], list[str]]:
    """Separa enlaces en información relevante y redes sociales específicas."""
    info_links: list[str] = []
    social_links: list[str] = []
    seen_urls: set[str] = set()

    for link in links:
        try:
            if is_irrelevant_link(link, company_domain):
                continue

            normalized = normalize_url(link)
            if normalized in seen_urls:
                continue
            seen_urls.add(normalized)

            parsed = urlparse(link.lower())
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]

            if is_social_host(domain):
                if is_specific_social_media_link(link, company_domain):
                    social_links.append(link)
            else:
                # Solo considerar enlaces informativos internos (mismo dominio o subdominios)
                if is_internal_host(domain, company_domain):
                    info_links.append(link)
                # Enlaces externos no sociales se descartan

        except Exception:
            # En caso de error, solo incluimos si no es irrelevante y es interno
            if not is_irrelevant_link(link, company_domain):
                try:
                    parsed = urlparse(link.lower())
                    domain = parsed.netloc
                    if domain.startswith("www."):
                        domain = domain[4:]
                    if is_internal_host(domain, company_domain):
                        info_links.append(link)
                except Exception:
                    # Si no podemos determinar, preferimos no incluir para evitar externos
                    pass

    return info_links, social_links
