import asyncio
import os
import uuid
import threading
from typing import Dict

from yt_dlp import YoutubeDL

from models import VideoInfo, FormatInfo


class YtdlpService:
    def __init__(self):
        self.tasks: Dict[str, dict] = {}
        self._lock = threading.Lock()

    def _extract_platform(self, url: str) -> str:
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

    def _is_bilibili(self, url: str) -> bool:
        return 'bilibili.com' in url

    def _get_base_ydl_opts(self, url: str) -> dict:
        """Get base yt-dlp options, with Bilibili-specific settings when needed."""
        opts = {
            'no_warnings': True,
            'quiet': True,
        }
        if self._is_bilibili(url):
            opts['extractor_args'] = {'bilibili': ['visitor=true']}
            opts['http_headers'] = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com/',
                'Origin': 'https://www.bilibili.com',
            }
        return opts

    async def parse_url(self, url: str) -> VideoInfo:
        def _extract_info():
            ydl_opts = self._get_base_ydl_opts(url)
            is_bili = self._is_bilibili(url)
            # Bilibili's format IDs (30080, 30280) don't match 'best' selector
            ydl_opts['format'] = 'bv*+ba/b' if is_bili else 'best[height>=144]'
            ydl_opts['download'] = False
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            return info

        data = await asyncio.to_thread(_extract_info)

        formats = []
        for f in data.get('formats', []):
            if f.get('vcodec') != 'none' and f.get('height'):
                quality = f"{f['height']}p"
                formats.append(FormatInfo(
                    quality=quality,
                    ext=f.get('ext', 'mp4'),
                    size=f.get('filesize') or f.get('filesize_approx'),
                    url=f.get('url', '')
                ))

        seen = set()
        unique_formats = []
        for f in sorted(formats, key=lambda x: int(x.quality.replace('p', '')), reverse=True):
            if f.quality not in seen:
                seen.add(f.quality)
                unique_formats.append(f)

        unique_formats = [f for f in unique_formats if f.quality != '144p']

        max_q = unique_formats[0].quality if unique_formats else 'Unknown'
        max_q_display = max_q
        if max_q.endswith('p'):
            h = int(max_q.replace('p', ''))
            if h >= 2160:
                max_q_display = '4K'
            elif h >= 1440:
                max_q_display = '2K'
            elif h >= 1080:
                max_q_display = '1080p'

        return VideoInfo(
            title=data.get('title', 'Unknown'),
            thumbnail=data.get('thumbnail', ''),
            duration=int(data['duration']) if data.get('duration') else None,
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
        # Use absolute path to avoid working directory issues in download endpoint
        output_path = os.path.join(os.path.abspath(output_dir), f'{task_id}.%(ext)s')

        quality_lower = quality.lower()
        if 'k' in quality_lower:
            quality_num = int(quality_lower.replace('k', '')) * 1000
        elif 'p' in quality_lower:
            quality_num = int(quality_lower.replace('p', ''))
        else:
            quality_num = 0

        if quality == '原画质' or quality_num == 0:
            format_spec = 'bestvideo+bestaudio/best'
        elif quality == '4k':
            format_spec = 'bestvideo[height<=2160]+bestaudio/best'
        elif quality == 'audio':
            format_spec = 'bestaudio/best'
        else:
            format_spec = f'bestvideo[height<={quality_num}]+bestaudio/best[height<={quality_num}]'

        # Bilibili uses different format IDs (30080, 30280, etc.) - height-based selectors fail
        if self._is_bilibili(url):
            if quality == 'audio':
                format_spec = 'bestaudio/best'
            else:
                # bv* matches best video-only stream, ba matches best audio-only stream
                # /b ensures fallback to a combined stream if available
                format_spec = 'bv*+ba/b'

        with self._lock:
            self.tasks[task_id] = {
                'status': 'downloading',
                'progress': 0,
                'speed': '',
                'eta': '',
                'downloaded': '',
                'file_path': None,
                'output_path': output_path,
            }

        asyncio.create_task(self._run_download(task_id, url, format_spec, output_path))

        return task_id

    async def _run_download(self, task_id: str, url: str, format_spec: str, output_path: str):
        """Run yt-dlp download. Progress is calculated based on downloaded bytes
        across multiple files (video + audio), normalized to 0-100%."""

        # Track cumulative progress across multiple files
        prev_downloaded = 0
        file_index = 0  # 0 = first file (video), 1 = second file (audio)

        # The expected final file path: replace %(ext)s template with mp4
        final_file_path = output_path.replace('%(ext)s', 'mp4')

        def progress_hook(d):
            nonlocal prev_downloaded, file_index

            with self._lock:
                if task_id not in self.tasks:
                    return

                task = self.tasks[task_id]

                if d['status'] == 'downloading':
                    downloaded = d.get('downloaded_bytes', 0) or 0
                    total = d.get('total_bytes', 0) or 1  # avoid div by 0

                    # Detect file switch: if downloaded bytes reset to ~0, new file started
                    if downloaded < prev_downloaded and file_index == 0:
                        file_index = 1  # switch to second file (audio)
                        prev_downloaded = 0

                    prev_downloaded = downloaded

                    # Calculate overall progress
                    # File 1 contributes 0-50%, File 2 contributes 50-100%
                    file_progress = min(50, (downloaded * 50) / total)
                    overall_progress = (file_index * 50) + file_progress

                    task['progress'] = min(99, overall_progress)
                    task['speed'] = d.get('_speed_str', '') or ''
                    task['eta'] = d.get('_eta_str', '') or ''
                    task['downloaded'] = d.get('_downloaded_bytes_str', '') or ''
                    task['status'] = 'downloading'

                elif d['status'] == 'finished':
                    # yt-dlp calls 'finished' for each intermediate file (video, then audio).
                    # d['filename'] may point to .f30280.m4a instead of the final merged .mp4.
                    # Always use the expected final path based on output template.
                    task['progress'] = 100
                    task['status'] = 'completed'
                    task['file_path'] = final_file_path

        def _download():
            ydl_opts = self._get_base_ydl_opts(url)
            ydl_opts.update({
                'format': format_spec,
                'merge_output_format': 'mp4',
                'outtmpl': output_path,
                'progress_hooks': [progress_hook],
            })
            print(f'[yt-dlp] Downloading with format: {format_spec}')
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

        try:
            await asyncio.to_thread(_download)
        except Exception as e:
            print(f'[yt-dlp] Download error: {e}')
            with self._lock:
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = 'failed'
                    self.tasks[task_id]['error'] = str(e)
