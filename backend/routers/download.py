# backend/routers/download.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/download")
async def download_video():
    return {"message": "Download endpoint - to be implemented"}
