import os

import redis


def get_redis_client():
    """Devuelve un cliente Redis simple basado en REDIS_URL.
    No hace ping ni aplica fallbacks: si Redis no está disponible, las llamadas
    que lo usen podrán capturar la excepción y continuar (fail-open donde aplique).
    """
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    return redis.Redis.from_url(redis_url, decode_responses=True)


# Cliente global
redis_client = get_redis_client()
