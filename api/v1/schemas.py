from pydantic import BaseModel, HttpUrl

class CreateBrochureRequest(BaseModel):
    url: HttpUrl
    language: str = "English"
    brochure_type: str = "professional"
    company_name: str = None

class DownloadBrochureRequest(BaseModel):
    cache_key: str