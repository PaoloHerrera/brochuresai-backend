from pydantic_settings import BaseSettings

"""
This settings module uses Pydantic to manage configuration settings.
It loads environment variables from a .env file and provides a structured way to access them.
"""

class Settings(BaseSettings):
  open_ai_api_key: str

  class Config:
    env_file = ".env"

settings = Settings()
