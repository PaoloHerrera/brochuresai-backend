from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from api.v1.schemas import ScrapeRequest
from services.openai.openai_client import OpenAIClient


router = APIRouter()

@router.post("/scrape")
async def scrape(request: ScrapeRequest):
    try:
        url = str(request.url)
        company_name = str(request.company_name)

        brochure_type = str(request.brochure_type) or "professional"
        language = str(request.language) or "English"

        brochure = await OpenAIClient().create_brochure(company_name, url, language, brochure_type)
        return brochure

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
