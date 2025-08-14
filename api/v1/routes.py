from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from api.v1.schemas import ScrapeRequest
from services.openai.openai_client import OpenAIClient
from services.scraper import Scraper


router = APIRouter()

@router.post("/scrape")
async def scrape(request: ScrapeRequest):
    try:
        url = str(request.url)
        company_name = str(request.company_name) or "Company"

        brochure_type = str(request.brochure_type) or "professional"
        language = str(request.language) or "English"

        brochure = await OpenAIClient(Scraper).create_brochure(company_name, url, language, brochure_type)
        return brochure

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
