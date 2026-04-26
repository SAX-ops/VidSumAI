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
            "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--add-header", "Referer:https://www.bilibili.com",
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
        import re

        cmd = [
            "yt-dlp",
            "-f", format_spec,
            "--merge-output-format", "mp4",
            "--newline",
            "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "--add-header", "Referer:https://www.bilibili.com",
            "-o", output_path,
            url
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        async def read_stream():
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                yield line.decode().strip()

        try:
            async for line in read_stream():
                print(f"[DEBUG] yt-dlp output: {line}")

                if '[download]' in line and '%' in line:
                    try:
                        percent = 0.0
                        downloaded_str = ""
                        speed = ""
                        eta = ""

                        match = re.search(r'([\d.]+)%\s+of\s+([~]?[\d.]+[KMGT]i?B)', line)
                        if match:
                            percent = float(match.group(1))
                            total_num = float(re.sub(r'[~KMGT]i?B', '', match.group(2)))
                            downloaded_str = f"{total_num * percent / 100:.2f}MiB"

                        speed_match = re.search(r'at\s+([\d.]+\s*[KMGT]i?B/s)', line)
                        if speed_match:
                            speed = speed_match.group(1)

                        eta_match = re.search(r'ETA ([\d:]+)', line)
                        if eta_match:
                            eta = eta_match.group(1)

                        if task_id in self.tasks:
                            self.tasks[task_id]['progress'] = percent
                            self.tasks[task_id]['speed'] = speed
                            self.tasks[task_id]['eta'] = eta
                            self.tasks[task_id]['downloaded'] = downloaded_str

                    except (ValueError, IndexError):
                        pass

                await asyncio.sleep(0.05)
        finally:
            await proc.wait()

        # Find downloaded file
        file_path = None
        for f in os.listdir(output_dir):
            if f.startswith(task_id):
                file_path = os.path.join(output_dir, f)
                break

        if file_path and os.path.exists(file_path):
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
