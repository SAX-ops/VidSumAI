from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse, Response
from models import ParseRequest, VideoInfo
from services.ytdlp import YtdlpService
import asyncio
import os
import subprocess
import httpx
from typing import Optional
from urllib.parse import urlparse, quote

router = APIRouter()
ytdlp_service = YtdlpService()

# Use absolute path for downloads directory
DOWNLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "downloads"))
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
    file_path = None

    # First try: check if task is in memory (same session)
    print(f"[download] Looking for task_id={task_id}")
    print(f"[download] Available tasks: {list(ytdlp_service.tasks.keys())}")
    if task_id in ytdlp_service.tasks:
        task = ytdlp_service.tasks[task_id]
        if task["status"] == "completed":
            file_path = task.get("file_path")
            # Resolve relative paths to absolute
            if file_path and not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            if file_path and os.path.exists(file_path):
                filename = os.path.basename(file_path)
                async def file_iterator():
                    try:
                        with open(file_path, "rb") as f:
                            while chunk := f.read(8192):
                                yield chunk
                    finally:
                        # Clean up temporary file after streaming
                        try:
                            os.remove(file_path)
                            print(f"[download] Cleaned up: {file_path}")
                        except OSError:
                            pass
                return StreamingResponse(
                    file_iterator(),
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"'
                    }
                )

    # Second try: look for file in downloads folder (file persists across restarts)
    candidate = os.path.join(DOWNLOAD_DIR, f"{task_id}.mp4")
    if os.path.exists(candidate):
        file_path = candidate
        filename = f"{task_id}.mp4"
        async def file_iterator():
            try:
                with open(file_path, "rb") as f:
                    while chunk := f.read(8192):
                        yield chunk
            finally:
                # Clean up temporary file after streaming
                try:
                    os.remove(file_path)
                    print(f"[download] Cleaned up: {file_path}")
                except OSError:
                    pass
        return StreamingResponse(
            file_iterator(),
            media_type="video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    raise HTTPException(status_code=404, detail="File not found")


@router.post("/start-download")
async def start_download(request: ParseRequest):
    try:
        task_id = await ytdlp_service.start_download(
            url=request.url,
            quality=request.quality,
            output_dir=DOWNLOAD_DIR
        )
        return {"task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download-direct")
async def download_direct(url: str, quality: str = "720p"):
    """Download video directly with browser save dialog (no progress tracking)"""
    import subprocess
    import tempfile

    print(f"[DEBUG] download_direct called with quality='{quality}'")

    try:
        # Map quality to yt-dlp format spec with fallback
        format_map = {
            "360p": "best[height<=360]",
            "720p": "best[height<=720]",
            "1080p": "best[height<=1080]",
            "原画质": "best",
            "audio": "bestaudio/best",
        }
        format_spec = format_map.get(quality, "best[height<=720]")
        print(f"[DEBUG] format_spec='{format_spec}'")

        # Get video title for filename
        probe_cmd = ["yt-dlp", "--get-title", "--no-download", url]
        proc = await asyncio.create_subprocess_exec(
            *probe_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        title = stdout.decode().strip().replace('/', '-').replace('\\', '-') or "video"

        # Create temp file
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"vidsumai_{quality}.%(ext)s")

        # Download command
        cmd = [
            "yt-dlp",
            "-f", format_spec,
            "--merge-output-format", "mp4",
            "-o", output_path,
            "--no-warnings",
            url
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()

        # Find the downloaded file
        for f in os.listdir(temp_dir):
            if f.startswith("vidsumai_") and f.endswith(".mp4"):
                file_path = os.path.join(temp_dir, f)
                filename = f"{title}.mp4"

                async def file_iterator():
                    with open(file_path, "rb") as f:
                        while chunk := f.read(8192):
                            yield chunk

                # Clean up temp file after reading
                def cleanup():
                    try:
                        os.remove(file_path)
                    except:
                        pass

                # Return streaming response with attachment header
                return StreamingResponse(
                    file_iterator(),
                    media_type="video/mp4",
                    headers={
                        "Content-Disposition": f'attachment; filename="{filename}"'
                    }
                )

        raise HTTPException(status_code=500, detail="Download failed")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


@router.post("/open-folder")
async def open_folder(folder_path: Optional[str] = None):
    """Open the specified folder in file explorer (Windows)"""

    try:
        if folder_path and os.path.exists(folder_path):
            target = folder_path
        else:
            # Open default downloads folder for current user
            target = os.path.join(os.path.expanduser("~"), "Downloads")

        # Windows: use explorer to open folder
        subprocess.Popen(f'explorer "{target}"')
        return {"success": True, "path": target}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proxy/image")
async def proxy_image(url: str = Query(...)):
    """Proxy image requests to bypass Referer hotlink protection (e.g. Bilibili thumbnails)"""
    parsed = urlparse(url)
    allowed_domains = ['bilibili.com', 'hdslb.com', 'bfmtv.com']
    is_allowed = any(d in parsed.netloc for d in allowed_domains)

    if not is_allowed:
        raise HTTPException(status_code=403, detail="Domain not allowed for proxy")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Referer': 'https://www.bilibili.com/',
        'Origin': 'https://www.bilibili.com',
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch image")

            content_type = resp.headers.get('content-type', 'image/jpeg')
            return Response(content=resp.content, media_type=content_type)
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Image proxy error: {str(e)}")
