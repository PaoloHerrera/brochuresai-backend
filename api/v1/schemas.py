from pydantic import BaseModel, HttpUrl
from typing import Optional

class CreateBrochureRequest(BaseModel):
    url: HttpUrl
    language: str = "en"
    brochure_type: str = "professional"
    company_name: Optional[str] = None
    anon_id: str

class DownloadBrochureRequest(BaseModel):
    cache_key: str

class IdentifyUserRequest(BaseModel):
    anon_id: Optional[str] = None