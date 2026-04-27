import asyncio
import os
import uuid
from typing import Optional

from yt_dlp import YoutubeDL

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
        def _extract_info():
            ydl_opts = {
                'dump_json': True,
                'no_download': True,
                'no_warnings': True,
                'quiet': True,
            }
            with YoutubeDL(ydl_opts) as ydl:
                data = ydl.extract_info(url, download=False)
            return data

        data = await asyncio.to_thread(_extract_info)

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

        # Filter out 144p (no audio)
        unique_formats = [f for f in unique_formats if f.quality != "144p"]

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

        # Check if YouTube URL
        is_youtube_url = "youtube.com/watch" in url or "youtu.be/" in url

        # Parse quality number
        quality_num = int(quality.lower().replace('p', '').replace('k', '000')) if quality else 0

        # Determine format spec based on quality
        if is_youtube_url and quality_num <= 480:
            actual_quality = max(quality_num, 360)
            format_spec = f"bestvideo[height={actual_quality}]+bestaudio/best[height={actual_quality}]"
        elif quality == "1080p":
            format_spec = "bestvideo[height<=?1080]+bestaudio/best[height<=?1080]"
        elif quality == "4k":
            format_spec = "bestvideo[height<=?2160][vcodec^=avc]+bestaudio/bestvideo[height<=?2160]+bestaudio"
        elif quality == "audio":
            format_spec = "bestaudio/best"
        else:
            format_spec = f"bestvideo[height<=?{quality_num}]+bestaudio/best[height<=?{quality_num}]"

        # Get video info for total size estimation
        total_size = 0
        try:
            video_info = await self.parse_url(url)
            for f in video_info.formats:
                if f.size:
                    total_size = max(total_size, f.size)
        except Exception:
            pass

        self.tasks[task_id] = {
            "status": "downloading",
            "progress": 0,
            "total_size": total_size,
            "output_path": output_path,
            "speed": "",
            "eta": "",
            "downloaded": "",
            "file_path": None
        }

        # Start download in background thread
        asyncio.create_task(self._run_download(task_id, url, format_spec, output_path))

        return task_id

    async def _run_download(self, task_id: str, url: str, format_spec: str, output_path: str):
        """Run yt-dlp download in a background thread with progress hooks."""
        task = self.tasks[task_id]

        def progress_hook(d):
            if d['status'] == 'downloading':
                percent_str = d.get('_percent_str', '0%')
                try:
                    progress = float(percent_str.rstrip('%'))
                except ValueError:
                    progress = 0

                speed = d.get('_speed_str', '')
                eta = d.get('_eta_str', '')
                downloaded = d.get('_downloaded_str', '')

                task['progress'] = min(99, progress)
                task['speed'] = speed
                task['eta'] = eta
                task['downloaded'] = downloaded
                task['status'] = 'downloading'
            elif d['status'] == 'finished':
                task['progress'] = 100
                task['status'] = 'completed'
                task['file_path'] = d.get('filename', '')

        def _download():
            ydl_opts = {
                'format': format_spec,
                'merge_output_format': 'mp4',
                'outtmpl': output_path,
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [progress_hook],
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.to_thread(_download)
        except Exception as e:
            task['status'] = 'failed'
            task['error'] = str(e)

    def _format_bytes(self, bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} TB"
