import asyncio
import ipaddress
import json
from urllib.parse import urlparse

from openai import OpenAI

from config import settings
from services.common.config import (
    DETAILS_MAX_CHARS,
    OPENAI_DEFAULT_MODEL,
    SCRAPER_LOG_VERBOSE,
    SCRAPER_MAX_CONCURRENCY,
)
from services.common.social import SOCIAL_TYPES, classify_social_type
from services.logging.dev_logger import get_logger
from services.openai.prompts import Prompts
from services.redis.redis_client import redis_client

# Modelo por defecto y límites centralizados en services.common.config


def _classify_social_type(domain: str) -> str:
    # Wrapper para usar el helper compartido y mantener compatibilidad interna
    return classify_social_type(domain)


def _build_combined_links(info_urls: list[str], social_urls: list[str]) -> list[dict]:
    combined: list[dict] = [{"type": "info", "url": u} for u in info_urls]
    for u in social_urls:
        parsed = urlparse(u.lower())
        domain = parsed.netloc
        link_type = _classify_social_type(domain)
        combined.append({"type": link_type, "url": u})
    return combined


# Se eliminan límites máximos; el control se hace con concurrencia y presupuesto


def _build_social_block(social_links: list[dict]) -> str:
    if not social_links:
        return ""
    lines = ["Social Links:"]
    for s in social_links:
        lines.append(f"- {s['type']}: {s['url']}")
    return "\n".join(lines)


def _load_details_cache(cache_key: str):
    try:
        cached = redis_client.get(cache_key)
        if cached:
            try:
                parsed = json.loads(cached)
                if isinstance(parsed, dict) and "details" in parsed:
                    return parsed
            except Exception:
                return {"details": cached, "social_links": []}
    except Exception:
        pass
    return None


def _cache_details_payload(cache_key: str, details: str, social_links: list[dict]) -> None:
    try:
        payload = json.dumps({"details": details, "social_links": social_links})
        redis_client.set(cache_key, payload, ex=3600)
    except Exception:
        pass


def _log_links_preview(social_items: list[dict], info_items: list[dict], logger) -> None:
    try:
        info_preview = [i["url"] for i in info_items][:5]
        ellipsis = " ..." if len(info_items) > 5 else ""
        logger.debug(
            "Info links to scrape (%d): %s%s",
            len(info_items),
            info_preview,
            ellipsis,
        )
        logger.debug(
            "Social links to include (%d): %s",
            len(social_items),
            [s["url"] for s in social_items],
        )
    except Exception as e:
        logger.debug("Failed to log debug link lists: %s", e)


class OpenAIClient:
    def __init__(self, scraper_cls):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.scraper_cls = scraper_cls
        self.prompts = Prompts()
        self.logger = get_logger(__name__)

    def get_client(self):
        return self.client

    async def _run_chat_completion(self, messages: list[dict], model: str = OPENAI_DEFAULT_MODEL):
        # Validación centralizada de API key
        if not self.client:
            return "Error: missing OpenAI API key"
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                ),
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    def _normalize_language(self, language: str):
        s = (language or "").strip().lower()
        # Defaults
        default_prompt_lang = "English"
        default_accept_lang = settings.scraper_accept_language or "en-US,en;q=0.9"
        default_code = "en"

        # Simple normalization map by keywords
        mapping = [
            (("en", "english"), ("en", "English", "en-US,en;q=0.9")),
            (("es", "spanish", "español"), ("es", "Spanish", "es-ES,es;q=0.9")),
            (("pt", "portuguese", "português"), ("pt", "Portuguese", "pt-BR,pt;q=0.9")),
            (("fr", "french", "français"), ("fr", "French", "fr-FR,fr;q=0.9")),
            (("de", "german", "deutsch"), ("de", "German", "de-DE,de;q=0.9")),
            (("it", "italian", "italiano"), ("it", "Italian", "it-IT,it;q=0.9")),
        ]
        for keys, val in mapping:
            for k in keys:
                if s == k or s.startswith(k + "-"):
                    return val
        return (default_code, default_prompt_lang, default_accept_lang)

    async def get_links(self, content):
        messages = [
            {"role": "system", "content": self.prompts.get_links_system_prompt()},
            {"role": "user", "content": self.prompts.get_links_user_prompt(content)},
        ]
        return await self._run_chat_completion(messages)

    def _details_cache_key(self, url: str, accept_language: str | None) -> str:
        try:
            parsed = urlparse(url)
            host = (parsed.netloc or parsed.path or url).lower()
            if host.startswith("www."):
                host = host[4:]
            lang_token = (accept_language or settings.scraper_accept_language or "").replace(
                ",", "_"
            )
            return f"company:details:{host}:al:{lang_token}"
        except Exception:
            return f"company:details:{url}:al:{accept_language or 'default'}"

    # --- Utilidades para validar enlaces del LLM ---
    @staticmethod
    def _is_http_url(url: str) -> bool:
        try:
            p = urlparse(url)
            return p.scheme in ("http", "https") and bool(p.netloc)
        except Exception:
            return False

    @staticmethod
    def _is_private_or_local_host(host: str) -> bool:
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_private, ip.is_loopback, ip.is_reserved, ip.is_link_local
        except ValueError:
            lowered = (host or "").lower()
            if lowered in {"localhost"} or lowered.endswith(".local"):
                return True
            return False

    @staticmethod
    def _same_host(host: str, base_host: str) -> bool:
        h = (host or "").lower()
        b = (base_host or "").lower()
        if h == b:
            return True
        if b.startswith("www.") and h == b[4:]:
            return True
        if h.startswith("www.") and h[4:] == b:
            return True
        return False

    async def get_all_details(self, url, accept_language: str | None = None):
        cache_key = self._details_cache_key(url, accept_language)
        cached = _load_details_cache(cache_key)
        if cached:
            return cached

        result_text = "Landing Page: \n"
        result_dict = await self.scraper_cls(url, accept_language=accept_language).get_content()

        # Usar enlaces filtrados por el scraper (sin límites máximos)
        info_urls = result_dict.get("info_links", [])
        social_urls = result_dict.get("social_links", [])

        # Construir estructura que el LLM espera usando helper (solo clasificación, sin recorte)
        combined_links = _build_combined_links(info_urls, social_urls)

        # Separar por tipo sin aplicar límites
        social_items = [link for link in combined_links if link["type"] in SOCIAL_TYPES]
        info_items = [link for link in combined_links if link["type"] == "info"]

        # DEBUG: Enlaces que se van a scrapear y sociales que se enviarán al LLM
        if SCRAPER_LOG_VERBOSE:
            _log_links_preview(social_items, info_items, self.logger)

        # Scrape ONLY informational links; do NOT scrape social media URLs
        # Control de concurrencia: limitar número de scrapes simultáneos
        sem = asyncio.Semaphore(max(1, SCRAPER_MAX_CONCURRENCY))

        async def _bounded_get_content(item_url: str):
            async with sem:
                return await self.scraper_cls(
                    item_url, accept_language=accept_language
                ).get_content()

        info_tasks = [_bounded_get_content(item["url"]) for item in info_items]
        pages = await asyncio.gather(*info_tasks, return_exceptions=True)

        # Presupuesto total de texto para evitar payloads excesivos
        budget = max(1, DETAILS_MAX_CHARS)
        for item, page in zip(info_items, pages):
            if isinstance(page, Exception):
                self.logger.warning("Error scraping %s: %s", item["url"], page)
                continue
            chunk = f"\n\n{item['type']}\n{page.get('text', '')}"
            remaining = budget - len(result_text)
            if remaining <= 0:
                break
            if len(chunk) > remaining:
                result_text += chunk[:remaining]
                break
            else:
                result_text += chunk

        # No incluir los sociales en el texto de detalles; devolverlos por separado
        social_links = [{"type": s["type"], "url": s["url"]} for s in social_items]

        # Cachear los detalles compilados y sociales por 1h usando helper
        _cache_details_payload(cache_key, result_text, social_links)

        return {"details": result_text, "social_links": social_links}

    async def create_brochure(self, company_name, url, language, brochure_type):
        # Validación perezosa: si no hay API key, devolver error claro
        if not self.client:
            return "Error: missing OpenAI API key"
        # Normaliza idioma para prompts y Accept-Language
        _, prompt_language, accept_language = self._normalize_language(language)

        # Obtener detalles (scraping) usando Accept-Language normalizado
        details_payload = await self.get_all_details(url, accept_language=accept_language)
        # Backward compatibility: si viniera un string
        if isinstance(details_payload, str):
            if details_payload.startswith("Error:"):
                return details_payload
            details_text = details_payload
            social_links = []
        else:
            details_text = details_payload.get("details", "")
            social_links = details_payload.get("social_links", [])

        # Agregar la URL principal al contexto para el LLM
        details_with_url = f"Main website URL: {url}\n\n{details_text}"

        # Construir bloque de sociales independiente para el LLM
        social_block = _build_social_block(social_links)

        # Construir prompt de sistema según el tipo de brochure
        if brochure_type == "funny":
            system_prompt = self.prompts.brochure_system_prompt_funny(prompt_language)
        else:
            system_prompt = self.prompts.brochure_system_prompt_professional(prompt_language)

        # DEBUG: Vista previa de la sección de sociales justo antes de enviar al LLM
        if SCRAPER_LOG_VERBOSE:
            try:
                if social_block:
                    self.logger.debug("Social links block built; sending to LLM.")
                    _lines = social_block.splitlines()
                    _preview = "\n".join(_lines[:10])
                    self.logger.debug("Social links preview:\n%s", _preview)
                else:
                    self.logger.debug("No social links block; sending without socials.")
            except Exception as e:
                self.logger.debug("Failed to preview social links section: %s", e)

        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": self.prompts.get_brochure_user_prompt(
                    company_name, details_with_url, social_block, prompt_language
                ),
            },
        ]
        return await self._run_chat_completion(messages)
