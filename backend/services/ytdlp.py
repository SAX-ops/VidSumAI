import json
import uuid
import os
import asyncio
from typing import Optional
from models import VideoInfo, FormatInfo


class YtdlpService:
    def __init__(self):
        self.tasks = {}

    def _extract_platform(self, url: str) -> str:
        """Extract platform name from URL"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return "YouTube"
        elif 'tiktok.com' in url:
            return "TikTok"
        elif 'instagram.com' in url:
            return "Instagram"
        elif 'bilibili.com' in url:
            return "Bilibili"
        elif 'twitter.com' in url or 'x.com' in url:
            return "X"
        return "Unknown"

    async def parse_url(self, url: str) -> VideoInfo:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            url
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise Exception(f"Failed to parse URL: {stderr.decode()}")

        data = json.loads(stdout.decode())

        formats = []
        for f in data.get("formats", []):
            if f.get("vcodec") != "none" and f.get("height"):
                quality = f"{f['height']}p"
                formats.append(FormatInfo(
                    quality=quality,
                    ext=f.get("ext", "mp4"),
                    size=f.get("filesize") or f.get("filesize_approx"),
                    url=f.get("url", "")
                ))

        # Deduplicate by quality, keep best
        seen = set()
        unique_formats = []
        for f in sorted(formats, key=lambda x: int(x.quality.replace("p", "")), reverse=True):
            if f.quality not in seen:
                seen.add(f.quality)
                unique_formats.append(f)

        return VideoInfo(
            title=data.get("title", "Unknown"),
            thumbnail=data.get("thumbnail", ""),
            duration=data.get("duration"),
            platform=self._extract_platform(url),
            url=url,
            formats=unique_formats[:10]
        )

    async def start_download(
        self,
        url: str,
        quality: str,
        output_dir: str
    ) -> str:
        task_id = str(uuid.uuid4())
        output_path = os.path.join(output_dir, f"{task_id}.%(ext)s")

        # Debug: log received quality
        print(f"[DEBUG] start_download called with quality='{quality}'")

        # Map quality to yt-dlp format spec with fallback
        # "360p" = best available up to 360p, "720p" = up to 720p, "1080p" = up to 1080p, "original" = best available
        format_map = {
            "360p": "best[height<=360]",
            "720p": "best[height<=720]",
            "1080p": "best[height<=1080]",
            "原画质": "best",
            "audio": "bestaudio/best",
        }
        format_spec = format_map.get(quality, "best[height<=720]")
        print(f"[DEBUG] format_spec='{format_spec}'")

        cmd = [
            "yt-dlp",
            "-f", format_spec,
            "--merge-output-format", "mp4",
            "-o", output_path,
            "--no-warnings",
            url
        ]
        print(f"[DEBUG] yt-dlp command: {' '.join(cmd)}")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        self.tasks[task_id] = {
            "process": proc,
            "status": "downloading",
            "progress": 0,
            "output_path": output_path,
            "speed": "",
            "eta": "",
            "downloaded": ""
        }

        asyncio.create_task(self._wait_for_download(task_id, output_dir))

        return task_id

    async def _wait_for_download(self, task_id: str, output_dir: str):
        task = self.tasks[task_id]
        proc = task["process"]
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            task["status"] = "failed"
            return

        for f in os.listdir(output_dir):
            if f.startswith(task_id):
                task["file_path"] = os.path.join(output_dir, f)
                task["status"] = "completed"
                task["progress"] = 100
                return

        task["status"] = "failed"

    def _format_bytes(self, bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"
