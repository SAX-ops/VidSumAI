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

        # Get max quality for display
        max_q = unique_formats[0].quality if unique_formats else "Unknown"
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

        # Map quality to yt-dlp format spec
        format_map = {
            "360p": "best[height<=360]",
            "720p": "best[height<=720]",
            "1080p": "best[height<=1080]",
            "原画质": "best",
            "audio": "bestaudio/best",
        }
        format_spec = format_map.get(quality, "best[height<=720]")

        self.tasks[task_id] = {
            "status": "downloading",
            "progress": 0,
            "output_path": output_path,
            "speed": "",
            "eta": "",
            "downloaded": "",
            "file_path": None
        }

        # Start async download with real-time progress reading
        asyncio.create_task(self._run_download(task_id, url, format_spec, output_path, output_dir))

        return task_id

    async def _run_download(self, task_id: str, url: str, format_spec: str, output_path: str, output_dir: str):
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
            stderr=asyncio.subprocess.PIPE
        )

        # Read stderr line by line for progress
        async for line in proc.stderr:
            line_str = line.decode('utf-8', errors='ignore')

            # Parse progress from yt-dlp output like "[download]  87.6% of ~16.78MiB at  1.23MiB/s ETA 0:12"
            if '[download]' in line_str and '%' in line_str:
                try:
                    # Extract percentage - look for pattern like "87.6%" or "87.6"
                    parts = line_str.split('%')
                    if len(parts) >= 1:
                        percent_str = parts[0].split()[-1]
                        percent = float(percent_str)

                        # Extract speed and ETA if present
                        speed = ""
                        eta = ""
                        downloaded = ""

                        if 'at' in line_str:
                            speed_parts = line_str.split('at')
                            if len(speed_parts) >= 2:
                                speed = speed_parts[-1].split('ETA')[0].strip() if 'ETA' in speed_parts[-1] else speed_parts[-1].strip()

                        if 'ETA' in line_str:
                            eta_parts = line_str.split('ETA')
                            if len(eta_parts) >= 2:
                                eta = eta_parts[-1].strip()

                        # Update task progress
                        if task_id in self.tasks:
                            self.tasks[task_id]['progress'] = percent
                            self.tasks[task_id]['speed'] = speed
                            self.tasks[task_id]['eta'] = eta
                            self.tasks[task_id]['downloaded'] = downloaded

                except (ValueError, IndexError):
                    pass

        await proc.wait()

        # Find downloaded file
        file_path = None
        for f in os.listdir(output_dir):
            if f.startswith(task_id):
                file_path = os.path.join(output_dir, f)
                break

        if proc.returncode == 0 and file_path:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'completed'
                self.tasks[task_id]['progress'] = 100
                self.tasks[task_id]['file_path'] = file_path
        else:
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'failed'

    def _format_bytes(self, bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"
