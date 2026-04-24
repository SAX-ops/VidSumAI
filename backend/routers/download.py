from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from models import ParseRequest, VideoInfo
from services.ytdlp import YtdlpService
import os
import asyncio

router = APIRouter()
ytdlp_service = YtdlpService()

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


@router.post("/parse", response_model=VideoInfo)
async def parse_video(request: ParseRequest):
    try:
        result = await ytdlp_service.parse_url(request.url)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download/{task_id}")
async def download_file(task_id: str):
    if task_id not in ytdlp_service.tasks:
        raise HTTPException(status_code=404, detail="Task not found")

    task = ytdlp_service.tasks[task_id]
    if task["status"] != "completed":
        raise HTTPException(status_code=400, detail="Download not ready")

    file_path = task.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    filename = os.path.basename(file_path)

    async def file_iterator():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        file_iterator(),
        media_type="video/mp4",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/start-download")
async def start_download(request: ParseRequest, quality: str = "720p"):
    try:
        task_id = await ytdlp_service.start_download(
            url=request.url,
            quality=quality,
            output_dir=DOWNLOAD_DIR
        )
        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.websocket("/ws/progress/{task_id}")
async def progress_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()

    if task_id not in ytdlp_service.tasks:
        await websocket.close(code=4004, reason="Task not found")
        return

    try:
        while True:
            task = ytdlp_service.tasks.get(task_id)
            if not task:
                break

            await websocket.send_json({
                "status": task["status"],
                "progress": task.get("progress", 0),
                "speed": task.get("speed", ""),
                "eta": task.get("eta", ""),
                "downloaded": task.get("downloaded", "")
            })

            if task["status"] in ("completed", "failed"):
                break

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
