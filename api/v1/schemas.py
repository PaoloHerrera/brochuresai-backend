from pydantic import BaseModel, HttpUrl

class ScrapeRequest(BaseModel):
    url: HttpUrl
    language: str = "English"
    brochure_type: str = "professional"
    company_name: str = None
    