import redis
import os

def get_redis_client():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    client = redis.Redis.from_url(
      redis_url,
      decode_responses=True,
      socket_timeout=5,
      socket_connect_timeout=5,
      retry_on_timeout=True,
    )

    return client

# Global Redis client
redis_client = get_redis_client()

def test_redis_connection() -> bool:
  try:
    print("Testing Redis connection...")
    redis_client.ping()
    print("Redis connection successful.")
    return True
  except redis.exceptions.ConnectionError as e:
    print(f"Redis connection failed: {e}")
    return False
