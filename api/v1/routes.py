from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from api.v1.schemas import ScrapeRequest
from services.scraper import Scraper  # Assuming you have a scraper service

router = APIRouter()

@router.post("/scrape")
async def scrape(request: ScrapeRequest):
    try:
        url = str(request.url)
        scraper = Scraper(url)
        content = await scraper.get_content()
        return content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))