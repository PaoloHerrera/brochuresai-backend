import json
import time
from typing import Any, Dict, Optional
from services.redis.redis_client import redis_client
import hashlib


def generate_cache_key(user_ip: str, data_json: Dict[str, Any]) -> str:
    content = f"{user_ip}:{json.dumps(data_json, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()


def store_brochure(cache_key: str, brochure_html: str, data_json: Dict[str, Any], user_ip: str, ttl_seconds: int = 3600) -> None:
    payload = {
        "brochure": brochure_html,
        "data": data_json,
        "user_ip": user_ip,
        "created_at": time.time(),
    }
    try:
        redis_client.set(cache_key, json.dumps(payload), ex=ttl_seconds)
    except Exception:
        # Si Redis no está disponible, simplemente no cacheamos
        pass


def get_brochure_payload(cache_key: str) -> Optional[Dict[str, Any]]:
    try:
        data = redis_client.get(cache_key)
    except Exception:
        return None
    if not data:
        return None
    try:
        return json.loads(data)
    except Exception:
        return None