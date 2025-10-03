import re
from urllib.parse import urlparse

# Tipos de redes sociales soportados para el LLM y límites
SOCIAL_TYPES: set[str] = {
    "twitter",
    "linkedin",
    "facebook",
    "instagram",
    "youtube",
    "tiktok",
    "github",
    "twitch",
    "kick",
    "discord",
    "social",
}


# Dominios de redes sociales reconocidas para inclusión cross-dominio
SOCIAL_DOMAINS: set[str] = {
    "twitter.com",
    "x.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "tiktok.com",
    "github.com",
    "twitch.tv",
    "kick.com",
    "discord.gg",
    "discord.com",
}


def normalize_domain(host: str) -> str:
    """Normaliza un host para comparación."""
    h = (host or "").lower()
    if h.startswith("www."):
        h = h[4:]
    if h.startswith("m."):
        h = h[2:]
    return h


def is_social_host(host: str) -> bool:
    """Determina si un host pertenece a un dominio social reconocido (incluye subdominios)."""
    h = normalize_domain(host)
    for d in SOCIAL_DOMAINS:
        if h == d or h.endswith("." + d):
            return True
    return False


def classify_social_type(domain: str) -> str:
    """Clasifica un dominio social en un tipo semántico (twitter, linkedin, etc.)."""
    d = normalize_domain(domain)
    if "twitter.com" in d or "x.com" in d:
        return "twitter"
    if "linkedin.com" in d:
        return "linkedin"
    if "facebook.com" in d:
        return "facebook"
    if "instagram.com" in d:
        return "instagram"
    if "youtube.com" in d:
        return "youtube"
    if "tiktok.com" in d:
        return "tiktok"
    if "github.com" in d:
        return "github"
    if "twitch.tv" in d:
        return "twitch"
    if "kick.com" in d:
        return "kick"
    if "discord.gg" in d or "discord.com" in d:
        return "discord"
    return "social"


def is_specific_social_media_link(url: str, company_domain: str) -> bool:
    """Determina si un enlace de red social es específico de una empresa.

    Considera rutas genéricas e inválidas por plataforma para evitar enlaces no
    representativos (login, feed, explore, etc.). Devuelve True solo si el path
    coincide con patrones típicos de perfiles/canales.
    """
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc
        path = parsed.path.strip("/")

        # Remover www. para comparación
        if domain.startswith("www."):
            domain = domain[4:]

        # Rutas genéricas a excluir
        generic_paths = {
            "login",
            "signup",
            "register",
            "home",
            "about",
            "help",
            "support",
            "privacy",
            "terms",
            "contact",
            "careers",
            "jobs",
            "press",
            "blog",
            "api",
            "developers",
            "business",
            "advertising",
            "settings",
            "logout",
            "search",
            "explore",
            "trending",
            "notifications",
            "messages",
            "feed",
            "timeline",
            "news",
            "events",
            "groups",
            "pages",
            "marketplace",
        }

        if path in generic_paths:
            return False
        if not path:
            return False

        social_patterns = {
            "twitter.com": {
                "valid": r"^[a-zA-Z0-9_]{1,15}$",
                "invalid": r"^(i/|intent/|share|oauth|search)",
            },
            "x.com": {
                "valid": r"^[a-zA-Z0-9_]{1,15}$",
                "invalid": r"^(i/|intent/|share|oauth|search)",
            },
            "linkedin.com": {
                "valid": r"^(company/[a-zA-Z0-9_-]+|in/[a-zA-Z0-9_-]+)$",
                "invalid": r"^(feed|messaging|notifications|jobs|learning|sales)",
            },
            "facebook.com": {
                "valid": r"^[a-zA-Z0-9._-]{5,}$",
                "invalid": r"^(watch|gaming|marketplace|groups|events|pages/create)",
            },
            "instagram.com": {
                "valid": r"^[a-zA-Z0-9._]{1,30}$",
                "invalid": r"^(explore|reels|stories|direct|accounts)",
            },
            "youtube.com": {
                "valid": r"^(@[a-zA-Z0-9_-]+|c/[a-zA-Z0-9_-]+|channel/[a-zA-Z0-9_-]+|user/[a-zA-Z0-9_-]+)$",
                "invalid": r"^(watch|playlist|results|feed|trending|gaming)",
            },
            "tiktok.com": {
                "valid": r"^@[a-zA-Z0-9._]{2,24}$",
                "invalid": r"^(foryou|following|live|discover|upload)",
            },
            "github.com": {
                "valid": r"^[a-zA-Z0-9_-]{1,39}$",
                "invalid": r"^(explore|trending|collections|topics|sponsors|marketplace)",
            },
            "twitch.tv": {
                "valid": r"^[a-zA-Z0-9_]{4,25}$",
                "invalid": r"^(directory|p/|downloads|jobs|security|mobile)",
            },
            "kick.com": {
                "valid": r"^[a-zA-Z0-9_-]{3,25}$",
                "invalid": r"^(categories|about|privacy|terms|support)",
            },
            "discord.gg": {
                "valid": r"^[a-zA-Z0-9]{6,12}$",
                "invalid": r"^(download|nitro|safety|company|branding)",
            },
            "discord.com": {
                "valid": r"^invite/[a-zA-Z0-9]{6,12}$",
                "invalid": r"^(download|nitro|safety|company|branding|channels|login)",
            },
        }

        if domain in social_patterns:
            pattern_config = social_patterns[domain]
            if re.match(pattern_config["invalid"], path):
                return False
            if re.match(pattern_config["valid"], path):
                return True
            return False

        return False
    except Exception:
        return False
