import base64
import gzip
import hashlib
import json
import time
from typing import Any, Optional

from config import settings
from services.redis.redis_client import redis_client


def _maybe_compress(s: str) -> str:
    """Compress string payload if enabled and size >= threshold.
    Store as safe string with prefix to allow transparent decompression.
    Format: "cmp:gzip:" + base64(gzip(payload))
    """
    try:
        if not settings.cache_compress:
            return s
        if len(s) < int(settings.cache_compress_min_bytes or 0):
            return s
        algo = (settings.cache_compression_algo or "gzip").lower()
        if algo != "gzip":
            # Solo soportamos gzip por ahora
            return s
        compressed = gzip.compress(s.encode("utf-8"), compresslevel=4)
        return "cmp:gzip:" + base64.b64encode(compressed).decode("ascii")
    except Exception:
        # Ante cualquier problema, fallback a sin compresión
        return s


def _maybe_decompress(s: str) -> str:
    """Detecta prefijo de compresión y devuelve el JSON en claro."""
    try:
        if isinstance(s, str) and s.startswith("cmp:gzip:"):
            b64 = s[len("cmp:gzip:") :]
            raw = base64.b64decode(b64)
            return gzip.decompress(raw).decode("utf-8")
        return s
    except Exception:
        # Si falla la descompresión, devolvemos tal cual para no romper flujo
        return s


def generate_cache_key(user_ip: str, data_json: dict[str, Any]) -> str:
    content = f"{user_ip}:{json.dumps(data_json, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()


def store_brochure(
    cache_key: str,
    brochure_html: str,
    data_json: dict[str, Any],
    user_ip: str,
    ttl_seconds: int = 3600,
) -> None:
    payload = {
        "brochure": brochure_html,
        "data": data_json,
        "user_ip": user_ip,
        "created_at": time.time(),
    }
    try:
        value = json.dumps(payload)
        value = _maybe_compress(value)
        redis_client.set(cache_key, value, ex=ttl_seconds)
    except Exception:
        # Si Redis no está disponible, simplemente no cacheamos
        pass


def get_brochure_payload(cache_key: str) -> Optional[dict[str, Any]]:
    try:
        data = redis_client.get(cache_key)
    except Exception:
        return None
    if not data:
        return None
    try:
        data_json_str = _maybe_decompress(data)
        return json.loads(data_json_str)
    except Exception:
        return None
