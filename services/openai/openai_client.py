import asyncio
import ipaddress
import json
from urllib.parse import urlparse

from openai import OpenAI

from config import settings
from services.openai.prompts import Prompts
from services.redis.redis_client import redis_client


class OpenAIClient:
    def __init__(self, scraper_cls):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.scraper_cls = scraper_cls
        self.prompts = Prompts()

    def get_client(self):
        return self.client

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
        # Validación perezosa: si no hay API key, devolver error claro
        if not self.client:
            return "Error: missing OpenAI API key"
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": self.prompts.get_links_system_prompt()},
                        {"role": "user", "content": self.prompts.get_links_user_prompt(content)},
                    ],
                ),
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

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
        # 1) Intentar obtener de Redis (TTL 1h) – clave incluye idioma
        cache_key = self._details_cache_key(url, accept_language)
        try:
            cached_details = redis_client.get(cache_key)
        except Exception:
            cached_details = None
        if cached_details:
            return cached_details

        # 2) Scrape + decisión de enlaces y ensamblado de detalles
        result = "Landing Page: \n"
        result_dict = await self.scraper_cls(url, accept_language=accept_language).get_content()
        links = await self.get_links(result_dict)

        # Si get_links falló por falta de API key u otro error, propagarlo
        if isinstance(links, str) and links.startswith("Error:"):
            return links

        print("Found links:", links)

        try:
            links_json = json.loads(links)
        except json.JSONDecodeError:
            print("Invalid JSON from model", links)
            return "Error: could not parse links from model"

        print("Links JSON: ", links_json)

        # Filtrar y limitar enlaces propuestos por el modelo
        try:
            base = urlparse(url)
            base_host = (base.hostname or "").lower()
        except Exception:
            base_host = ""

        MAX_LINKS = 8
        safe_links = []
        seen = set()
        for item in links_json.get("links", []):
            try:
                link_url = str(item.get("url", ""))
            except Exception:
                continue
            if not link_url or not self._is_http_url(link_url):
                continue
            parsed = urlparse(link_url)
            host = (parsed.hostname or "").lower()
            # Bloquear hosts privados/localhost
            try:
                # si es IP literal
                ip = ipaddress.ip_address(host)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                    continue
            except ValueError:
                lowered = host
                if lowered in {"localhost"} or lowered.endswith(".local"):
                    continue
            # Restringir al mismo host base (tolerando www)
            if not self._same_host(host, base_host):
                continue
            if link_url in seen:
                continue
            seen.add(link_url)
            safe_links.append(item)
            if len(safe_links) >= MAX_LINKS:
                break

        # Asynchronously scrape filtered links con el mismo Accept-Language
        tasks = [
            self.scraper_cls(link["url"], accept_language=accept_language).get_content()
            for link in safe_links
        ]
        pages = await asyncio.gather(*tasks, return_exceptions=True)

        for link, page in zip(safe_links, pages):
            if isinstance(page, Exception):
                print(f"Error scraping {link['url']}: {page}")
                continue
            result += f"\n\n{link['type']}\n{page.get('text', '')}"

        # Cachear los detalles compilados por 1h
        try:
            redis_client.set(cache_key, result, ex=3600)
        except Exception:
            pass

        return result

    async def create_brochure(self, company_name, url, language, brochure_type):
        # Validación perezosa: si no hay API key, devolver error claro
        if not self.client:
            return "Error: missing OpenAI API key"
        # Normaliza idioma para prompts y Accept-Language
        _, prompt_language, accept_language = self._normalize_language(language)

        # Obtener detalles (scraping) usando Accept-Language normalizado
        details = await self.get_all_details(url, accept_language=accept_language)
        if details.startswith("Error:"):
            return details

        # Construir prompt de sistema según el tipo de brochure
        if brochure_type == "funny":
            system_prompt = self.prompts.brochure_system_prompt_funny(prompt_language)
        else:
            system_prompt = self.prompts.brochure_system_prompt_professional(prompt_language)

        # Llamada a OpenAI de manera asíncrona con manejo de errores
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-5-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": self.prompts.get_brochure_user_prompt(
                                company_name, details, prompt_language
                            ),
                        },
                    ],
                ),
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"
