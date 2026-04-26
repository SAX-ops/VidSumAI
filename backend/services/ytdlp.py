import json
import uuid
import os
import asyncio
import threading
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

        # Get max quality for display
        max_q = unique_formats[0].quality if unique_formats else "Unknown"
        # Convert to user-friendly format: 2160p -> 4K, 1440p -> 2K, etc.
        max_q_display = max_q
        if max_q.endswith("p"):
            h = int(max_q.replace("p", ""))
            if h >= 2160:
                max_q_display = "4K"
            elif h >= 1440:
                max_q_display = "2K"
            elif h >= 1080:
                max_q_display = "1080p"

        return VideoInfo(
            title=data.get("title", "Unknown"),
            thumbnail=data.get("thumbnail", ""),
            duration=data.get("duration"),
            platform=self._extract_platform(url),
            url=url,
            max_quality=max_q_display,
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

        # Map quality to yt-dlp format spec
        format_map = {
            "360p": "best[height<=360]",
            "720p": "best[height<=720]",
            "1080p": "best[height<=1080]",
            "原画质": "best",
            "audio": "bestaudio/best",
        }
        format_spec = format_map.get(quality, "best[height<=720]")
        print(f"[DEBUG] format_spec='{format_spec}'")

        self.tasks[task_id] = {
            "status": "downloading",
            "progress": 0,
            "output_path": output_path,
            "speed": "",
            "eta": "",
            "downloaded": "",
            "file_path": None
        }

        # Use yt-dlp as library with progress hooks
        loop = asyncio.get_event_loop()

        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed', '')
                eta = d.get('eta', '')
                downloaded_str = self._format_bytes(downloaded)

                if total > 0:
                    percent = (downloaded / total) * 100
                else:
                    percent = 0

                # Update task progress
                if task_id in self.tasks:
                    self.tasks[task_id]['progress'] = percent
                    self.tasks[task_id]['speed'] = speed
                    self.tasks[task_id]['eta'] = eta
                    self.tasks[task_id]['downloaded'] = downloaded_str

            elif d['status'] == 'finished':
                if task_id in self.tasks:
                    self.tasks[task_id]['progress'] = 100
                    self.tasks[task_id]['status'] = 'completed'

        def download_thread():
            import yt_dlp

            ydl_opts = {
                'format': format_spec,
                'outtmpl': output_path,
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook],
                'quiet': True,
                'no_warnings': True,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                # Find downloaded file
                for f in os.listdir(output_dir):
                    if f.startswith(task_id):
                        file_path = os.path.join(output_dir, f)
                        if task_id in self.tasks:
                            self.tasks[task_id]['file_path'] = file_path
                        break
            except Exception as e:
                print(f"[ERROR] Download failed: {e}")
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = 'failed'

        # Run download in thread pool
        thread = threading.Thread(target=download_thread)
        thread.start()

        return task_id

    def _format_bytes(self, bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"
