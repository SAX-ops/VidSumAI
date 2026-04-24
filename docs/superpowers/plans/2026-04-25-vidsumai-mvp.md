# VidSumAI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal MVP video downloader with Vue/Nuxt.js frontend and Python FastAPI backend, supporting YouTube/TikTok/Instagram/Bilibili downloads with real-time progress.

**Architecture:** Single monolith with Nuxt.js frontend communicating to FastAPI backend via REST/WebSocket. Backend calls yt-dlp via subprocess for video parsing and downloading, streams files directly to browser.

**Tech Stack:** Vue 3, Nuxt.js 3, TailwindCSS, FastAPI, Python, yt-dlp, WebSockets

---

## File Structure

```
vidsumai/
├── frontend/                          # Nuxt.js frontend
│   ├── nuxt.config.ts                # Nuxt configuration
│   ├── tailwind.config.ts            # TailwindCSS config
│   ├── app.vue                       # Root component
│   ├── pages/
│   │   └── index.vue                 # Home page
│   ├── components/
│   │   ├── DownloadInput.vue         # URL input + parse button
│   │   ├── QualitySelector.vue       # Quality chips
│   │   ├── ProgressTracker.vue       # Download progress bar
│   │   ├── PlatformList.vue          # Supported platforms
│   │   └── DownloadResult.vue        # Download complete state
│   ├── composables/
│   │   └── useWebSocket.ts           # WebSocket hook
│   ├── types/
│   │   └── index.ts                  # TypeScript types
│   └── package.json
├── backend/                           # FastAPI backend
│   ├── main.py                       # FastAPI app entry
│   ├── routers/
│   │   └── download.py               # Download endpoints
│   ├── services/
│   │   └── ytdlp.py                  # yt-dlp wrapper
│   ├── models.py                     # Pydantic models
│   ├── requirements.txt              # Python dependencies
│   └── tests/
│       ├── __init__.py
│       ├── test_download.py          # Download endpoint tests
│       └── test_ytdlp.py            # yt-dlp service tests
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-04-25-vidsumai-design.md
        └── plans/
            └── 2026-04-25-vidsumai-mvp.md
```

---

## Task 1: Backend Project Setup

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/main.py`
- Create: `backend/models.py`

- [ ] **Step 1: Create requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
websockets==12.0
pydantic==2.5.3
python-multipart==0.0.6
```

- [ ] **Step 2: Create Pydantic models**

```python
# backend/models.py
from pydantic import BaseModel
from typing import List, Optional


class FormatInfo(BaseModel):
    quality: str
    ext: str
    size: Optional[int] = None
    url: str


class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    duration: Optional[int] = None
    formats: List[FormatInfo]


class ParseRequest(BaseModel):
    url: str


class DownloadTask(BaseModel):
    id: str
    url: str
    status: str = "pending"
    progress: float = 0.0
    filename: Optional[str] = None


class ProgressUpdate(BaseModel):
    percent: float
    speed: str
    eta: str
    downloaded: str
```

- [ ] **Step 3: Create FastAPI main app**

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import download

app = FastAPI(title="VidSumAI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(download.router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

- [ ] **Step 4: Create empty routers init**

```python
# backend/routers/__init__.py
```

- [ ] **Step 5: Test backend starts**

Run: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`
Expected: Server starts on http://localhost:8000

- [ ] **Step 6: Test health endpoint**

Run: `curl http://localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: setup FastAPI backend with models and health endpoint"
```

---

## Task 2: yt-dlp Service

**Files:**
- Create: `backend/services/__init__.py`
- Create: `backend/services/ytdlp.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_ytdlp.py`

- [ ] **Step 1: Write failing test for parse_url**

```python
# backend/tests/test_ytdlp.py
import pytest
from services.ytdlp import YtdlpService


@pytest.mark.asyncio
async def test_parse_url_returns_video_info():
    service = YtdlpService()
    # Use a known stable YouTube video
    result = await service.parse_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert result.title is not None
    assert result.thumbnail is not None
    assert len(result.formats) > 0


@pytest.mark.asyncio
async def test_parse_url_invalid_raises():
    service = YtdlpService()
    with pytest.raises(Exception):
        await service.parse_url("https://invalid-url-that-does-not-exist.com")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_ytdlp.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'services'"

- [ ] **Step 3: Implement YtdlpService**

```python
# backend/services/__init__.py
from .ytdlp import YtdlpService

__all__ = ["YtdlpService"]
```

```python
# backend/services/ytdlp.py
import subprocess
import json
import uuid
import os
import asyncio
from typing import Callable, Optional
from models import VideoInfo, FormatInfo


class YtdlpService:
    def __init__(self):
        self.tasks = {}

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
            formats=unique_formats[:10]  # Limit to 10 formats
        )

    async def download_video(
        self,
        url: str,
        quality: str,
        output_dir: str,
        progress_callback: Optional[Callable] = None
    ) -> str:
        task_id = str(uuid.uuid4())
        output_path = os.path.join(output_dir, f"{task_id}.%(ext)s")

        format_spec = "bestvideo[height<=?720]+bestaudio/best[height<=?720]"
        if quality == "1080p":
            format_spec = "bestvideo[height<=?1080]+bestaudio/best[height<=?1080]"
        elif quality == "4k":
            format_spec = "bestvideo[height<=?2160]+bestaudio/best[height<=?2160]"
        elif quality == "audio":
            format_spec = "bestaudio/best"

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

        self.tasks[task_id] = {
            "process": proc,
            "status": "downloading",
            "progress": 0
        }

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            self.tasks[task_id]["status"] = "failed"
            raise Exception(f"Download failed: {stderr.decode()}")

        self.tasks[task_id]["status"] = "completed"
        self.tasks[task_id]["progress"] = 100

        # Find the actual downloaded file
        for f in os.listdir(output_dir):
            if f.startswith(task_id):
                return os.path.join(output_dir, f)

        raise Exception("Downloaded file not found")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_ytdlp.py -v`
Expected: PASS (requires yt-dlp installed)

- [ ] **Step 5: Commit**

```bash
git add backend/services/ backend/tests/
git commit -m "feat: add yt-dlp service for URL parsing and video download"
```

---

## Task 3: Download Router

**Files:**
- Create: `backend/routers/download.py`
- Create: `backend/tests/test_download.py`

- [ ] **Step 1: Write failing test for parse endpoint**

```python
# backend/tests/test_download.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_parse_endpoint():
    response = client.post(
        "/api/parse",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "formats" in data
    assert len(data["formats"]) > 0


def test_parse_endpoint_invalid_url():
    response = client.post(
        "/api/parse",
        json={"url": "invalid-url"}
    )
    assert response.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_download.py -v`
Expected: FAIL with 404 or 422

- [ ] **Step 3: Implement download router**

```python
# backend/routers/download.py
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
```

- [ ] **Step 4: Add start_download method to YtdlpService**

```python
# Add to backend/services/ytdlp.py YtdlpService class

async def start_download(
    self,
    url: str,
    quality: str,
    output_dir: str
) -> str:
    task_id = str(uuid.uuid4())
    output_path = os.path.join(output_dir, f"{task_id}.%(ext)s")

    format_spec = "bestvideo[height<=?720]+bestaudio/best[height<=?720]"
    if quality == "1080p":
        format_spec = "bestvideo[height<=?1080]+bestaudio/best[height<=?1080]"
    elif quality == "4k":
        format_spec = "bestvideo[height<=?2160]+bestaudio/best[height<=?2160]"
    elif quality == "audio":
        format_spec = "bestaudio/best"
        output_path = os.path.join(output_dir, f"{task_id}.%(ext)s")

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

    self.tasks[task_id] = {
        "process": proc,
        "status": "downloading",
        "progress": 0,
        "output_path": output_path
    }

    # Run download in background
    asyncio.create_task(self._wait_for_download(task_id, output_dir))

    return task_id


async def _wait_for_download(self, task_id: str, output_dir: str):
    task = self.tasks[task_id]
    proc = task["process"]
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        task["status"] = "failed"
        return

    # Find the actual file
    for f in os.listdir(output_dir):
        if f.startswith(task_id):
            task["file_path"] = os.path.join(output_dir, f)
            task["status"] = "completed"
            task["progress"] = 100
            return

    task["status"] = "failed"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_download.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/routers/download.py backend/tests/test_download.py backend/services/ytdlp.py
git commit -m "feat: add download router with parse and download endpoints"
```

---

## Task 4: WebSocket Progress

**Files:**
- Modify: `backend/routers/download.py`
- Modify: `backend/services/ytdlp.py`

- [ ] **Step 1: Add WebSocket endpoint to router**

```python
# Add to backend/routers/download.py

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
```

- [ ] **Step 2: Update yt-dlp to track progress**

```python
# Add progress hook to YtdlpService in backend/services/ytdlp.py

def _progress_hook(self, task_id: str):
    def hook(d):
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]

        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)

            if total > 0:
                task["progress"] = round((downloaded / total) * 100, 1)

            task["speed"] = d.get("speed", "")
            task["eta"] = d.get("eta", "")
            task["downloaded"] = self._format_bytes(downloaded)

        elif d["status"] == "finished":
            task["progress"] = 100
            task["status"] = "processing"

    return hook


def _format_bytes(self, bytes_val: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024.0:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.1f} TB"
```

- [ ] **Step 3: Update start_download to use progress hook**

```python
# Modify the cmd list in start_download method

cmd = [
    "yt-dlp",
    "-f", format_spec,
    "--merge-output-format", "mp4",
    "-o", output_path,
    "--no-warnings",
    "--progress",
    url
]

proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)

# Store progress hook
self.tasks[task_id]["hook"] = self._progress_hook(task_id)
```

- [ ] **Step 4: Test WebSocket connection**

Run: `cd backend && python -c "import websockets; print('websockets installed')"`
Expected: No error

- [ ] **Step 5: Commit**

```bash
git add backend/routers/download.py backend/services/ytdlp.py
git commit -m "feat: add WebSocket progress tracking for downloads"
```

---

## Task 5: Frontend Project Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/nuxt.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/app.vue`
- Create: `frontend/pages/index.vue`
- Create: `frontend/types/index.ts`

- [ ] **Step 1: Initialize Nuxt project**

Run: `cd vidsumai && npx nuxi@latest init frontend`
Expected: Nuxt project created

- [ ] **Step 2: Install dependencies**

Run: `cd frontend && npm install && npm install -D @nuxtjs/tailwindcss`
Expected: Dependencies installed

- [ ] **Step 3: Configure Nuxt**

```typescript
// frontend/nuxt.config.ts
export default defineNuxtConfig({
  devtools: { enabled: true },
  modules: ['@nuxtjs/tailwindcss'],
  css: ['~/assets/css/main.css'],
  app: {
    head: {
      title: 'VidSumAI - 8K 无水印视频下载',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: '支持 YouTube、TikTok、Instagram 等 50+ 平台，高清无水印视频一键下载' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
      ]
    }
  },
  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000'
    }
  }
})
```

- [ ] **Step 4: Configure TailwindCSS**

```typescript
// frontend/tailwind.config.ts
import type { Config } from 'tailwindcss'

export default {
  content: [
    './components/**/*.{js,vue,ts}',
    './layouts/**/*.vue',
    './pages/**/*.vue',
    './plugins/**/*.{js,ts}',
    './app.vue',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          from: '#ff6b6b',
          to: '#feca57',
        },
        dark: {
          bg: '#0a0a0f',
          card: 'rgba(255,255,255,0.05)',
          border: 'rgba(255,255,255,0.1)',
        }
      },
      backgroundImage: {
        'gradient-primary': 'linear-gradient(135deg, #ff6b6b 0%, #feca57 100%)',
      }
    },
  },
  plugins: [],
} satisfies Config
```

- [ ] **Step 5: Create global CSS**

```css
/* frontend/assets/css/main.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #0a0a0f;
  color: #fff;
}

.gradient-text {
  background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.gradient-bg {
  background: linear-gradient(135deg, #ff6b6b 0%, #feca57 100%);
}
```

- [ ] **Step 6: Create TypeScript types**

```typescript
// frontend/types/index.ts
export interface FormatInfo {
  quality: string
  ext: string
  size: number | null
  url: string
}

export interface VideoInfo {
  title: string
  thumbnail: string
  duration: number | null
  formats: FormatInfo[]
}

export interface ProgressUpdate {
  status: string
  progress: number
  speed: string
  eta: string
  downloaded: string
}

export interface DownloadState {
  url: string
  parsing: boolean
  downloading: boolean
  videoInfo: VideoInfo | null
  selectedQuality: string
  progress: ProgressUpdate | null
  error: string | null
}
```

- [ ] **Step 7: Create root app.vue**

```vue
<!-- frontend/app.vue -->
<template>
  <NuxtPage />
</template>
```

- [ ] **Step 8: Create basic index page**

```vue
<!-- frontend/pages/index.vue -->
<template>
  <div class="min-h-screen bg-dark-bg">
    <header class="border-b border-dark-border py-4 px-8">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 gradient-bg rounded-xl flex items-center justify-center text-xl transform -rotate-12">
          ▶
        </div>
        <span class="text-2xl font-bold gradient-text">VidSumAI</span>
      </div>
    </header>

    <main class="container mx-auto px-4 py-16">
      <h1 class="text-5xl font-extrabold text-center mb-4">
        <span class="gradient-text">8K 无水印</span><br>
        视频一键下载
      </h1>
      <p class="text-gray-400 text-xl text-center mb-8">
        支持 YouTube、TikTok、Instagram 等 50+ 平台
      </p>
    </main>
  </div>
</template>
```

- [ ] **Step 9: Test frontend starts**

Run: `cd frontend && npm run dev`
Expected: Server starts on http://localhost:3000

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat: setup Nuxt.js frontend with TailwindCSS and types"
```

---

## Task 6: DownloadInput Component

**Files:**
- Create: `frontend/components/DownloadInput.vue`

- [ ] **Step 1: Create DownloadInput component**

```vue
<!-- frontend/components/DownloadInput.vue -->
<template>
  <div class="max-w-2xl mx-auto">
    <div class="bg-dark-card border border-dark-border rounded-2xl p-6 shadow-2xl">
      <div class="flex gap-3 mb-5">
        <input
          v-model="url"
          type="text"
          placeholder="粘贴视频链接，例如 https://youtube.com/watch?v=..."
          class="flex-1 bg-white/5 border-2 border-white/15 rounded-xl px-5 py-4 text-white text-base outline-none transition-all focus:border-primary-from focus:shadow-[0_0_20px_rgba(255,107,107,0.2)] placeholder:text-gray-600"
          @keyup.enter="handleParse"
        />
        <button
          class="gradient-bg border-none rounded-xl px-8 py-4 text-white text-lg font-bold cursor-pointer transition-all hover:-translate-y-1 hover:shadow-[0_12px_32px_rgba(255,107,107,0.5)]"
          :disabled="loading"
          @click="handleParse"
        >
          {{ loading ? '解析中...' : '免费下载' }}
        </button>
      </div>

      <div v-if="error" class="text-red-400 text-sm mt-2">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{
  parsed: [videoInfo: VideoInfo]
}>()

const url = ref('')
const loading = ref(false)
const error = ref('')

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const handleParse = async () => {
  if (!url.value.trim()) {
    error.value = '请输入视频链接'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await $fetch<VideoInfo>(`${apiBase}/api/parse`, {
      method: 'POST',
      body: { url: url.value }
    })
    emit('parsed', response)
  } catch (e: any) {
    error.value = e.data?.detail || '解析失败，请检查链接是否正确'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 2: Test component renders**

Run: `cd frontend && npm run dev`
Expected: Input box and button visible on page

- [ ] **Step 3: Commit**

```bash
git add frontend/components/DownloadInput.vue
git commit -m "feat: add DownloadInput component with URL parsing"
```

---

## Task 7: QualitySelector Component

**Files:**
- Create: `frontend/components/QualitySelector.vue`

- [ ] **Step 1: Create QualitySelector component**

```vue
<!-- frontend/components/QualitySelector.vue -->
<template>
  <div v-if="formats.length > 0" class="flex gap-3 justify-center mt-5">
    <button
      v-for="format in formats"
      :key="format.quality"
      class="px-4 py-2 rounded-lg text-sm cursor-pointer transition-all"
      :class="[
        selected === format.quality
          ? 'bg-primary-from/20 border border-primary-from text-white'
          : 'bg-white/5 border border-white/15 text-gray-400 hover:bg-primary-from/20 hover:border-primary-from hover:text-white'
      ]"
      @click="select(format.quality)"
    >
      {{ format.quality }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { FormatInfo } from '~/types'

const props = defineProps<{
  formats: FormatInfo[]
  selected: string
}>()

const emit = defineEmits<{
  update: [quality: string]
}>()

const select = (quality: string) => {
  emit('update', quality)
}
</script>
```

- [ ] **Step 2: Integrate with DownloadInput**

```vue
<!-- Update frontend/components/DownloadInput.vue script section -->
<script setup lang="ts">
import type { VideoInfo } from '~/types'

const emit = defineEmits<{
  parsed: [videoInfo: VideoInfo]
}>()

const url = ref('')
const loading = ref(false)
const error = ref('')

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const handleParse = async () => {
  if (!url.value.trim()) {
    error.value = '请输入视频链接'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const response = await $fetch<VideoInfo>(`${apiBase}/api/parse`, {
      method: 'POST',
      body: { url: url.value }
    })
    emit('parsed', response)
  } catch (e: any) {
    error.value = e.data?.detail || '解析失败，请检查链接是否正确'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/QualitySelector.vue frontend/components/DownloadInput.vue
git commit -m "feat: add QualitySelector component for quality picking"
```

---

## Task 8: ProgressTracker Component

**Files:**
- Create: `frontend/components/ProgressTracker.vue`
- Create: `frontend/composables/useWebSocket.ts`

- [ ] **Step 1: Create WebSocket composable**

```typescript
// frontend/composables/useWebSocket.ts
import type { ProgressUpdate } from '~/types'

export const useWebSocket = (taskId: string, apiBase: string) => {
  const progress = ref<ProgressUpdate | null>(null)
  const connected = ref(false)
  const error = ref<string | null>(null)

  let ws: WebSocket | null = null

  const connect = () => {
    const wsUrl = apiBase.replace('http', 'ws') + `/api/ws/progress/${taskId}`

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      connected.value = true
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      progress.value = data
    }

    ws.onerror = (e) => {
      error.value = 'WebSocket connection error'
      connected.value = false
    }

    ws.onclose = () => {
      connected.value = false
    }
  }

  const disconnect = () => {
    if (ws) {
      ws.close()
      ws = null
    }
  }

  return {
    progress,
    connected,
    error,
    connect,
    disconnect
  }
}
```

- [ ] **Step 2: Create ProgressTracker component**

```vue
<!-- frontend/components/ProgressTracker.vue -->
<template>
  <div v-if="progress" class="max-w-2xl mx-auto mt-8 bg-dark-card border border-dark-border rounded-2xl p-6">
    <div class="flex justify-between mb-3 text-sm">
      <span class="text-white">{{ filename }}</span>
      <span class="text-primary-from font-semibold">{{ progress.progress }}%</span>
    </div>

    <div class="h-2.5 bg-white/10 rounded-full overflow-hidden">
      <div
        class="h-full gradient-bg rounded-full transition-all duration-300"
        :style="{ width: `${progress.progress}%` }"
      />
    </div>

    <div class="flex justify-between mt-3 text-xs text-gray-500">
      <span>已下载: {{ progress.downloaded }}</span>
      <span>速度: {{ progress.speed }}</span>
      <span>剩余: {{ progress.eta }}</span>
    </div>

    <div v-if="progress.status === 'completed'" class="mt-4 text-center">
      <button
        class="gradient-bg border-none rounded-xl px-6 py-3 text-white font-bold cursor-pointer"
        @click="$emit('download')"
      >
        下载文件
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ProgressUpdate } from '~/types'

defineProps<{
  progress: ProgressUpdate
  filename: string
}>()

defineEmits<{
  download: []
}>()
</script>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ProgressTracker.vue frontend/composables/useWebSocket.ts
git commit -m "feat: add ProgressTracker component with WebSocket support"
```

---

## Task 9: PlatformList Component

**Files:**
- Create: `frontend/components/PlatformList.vue`

- [ ] **Step 1: Create PlatformList component**

```vue
<!-- frontend/components/PlatformList.vue -->
<template>
  <div class="py-16 text-center">
    <h2 class="text-sm text-gray-500 uppercase tracking-widest mb-8">
      支持 50+ 主流平台
    </h2>

    <div class="flex justify-center gap-8 flex-wrap">
      <div
        v-for="platform in platforms"
        :key="platform.name"
        class="flex flex-col items-center gap-3 text-gray-500 text-xs transition-all hover:text-white hover:-translate-y-1"
      >
        <div class="w-14 h-14 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-2xl transition-all hover:bg-primary-from/15 hover:border-primary-from/30">
          {{ platform.icon }}
        </div>
        <span>{{ platform.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const platforms = [
  { name: 'YouTube', icon: '▶' },
  { name: 'TikTok', icon: '♪' },
  { name: 'Instagram', icon: '📷' },
  { name: 'X', icon: '𝕏' },
  { name: 'Facebook', icon: 'f' },
  { name: 'Bilibili', icon: '◎' },
  { name: '更多平台', icon: '📺' },
]
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/PlatformList.vue
git commit -m "feat: add PlatformList component showing supported platforms"
```

---

## Task 10: Complete Home Page

**Files:**
- Modify: `frontend/pages/index.vue`

- [ ] **Step 1: Update index.vue with all components**

```vue
<!-- frontend/pages/index.vue -->
<template>
  <div class="min-h-screen bg-dark-bg">
    <!-- Header -->
    <header class="border-b border-dark-border py-5 px-10">
      <div class="flex justify-between items-center max-w-7xl mx-auto">
        <div class="flex items-center gap-3">
          <div class="w-10 h-10 gradient-bg rounded-xl flex items-center justify-center text-xl transform -rotate-12">
            ▶
          </div>
          <span class="text-2xl font-bold gradient-text">VidSumAI</span>
        </div>
        <nav class="flex gap-8 items-center">
          <a href="#" class="text-gray-500 text-sm hover:text-white transition-colors">功能</a>
          <a href="#" class="text-gray-500 text-sm hover:text-white transition-colors">价格</a>
          <a href="#" class="text-gray-500 text-sm hover:text-white transition-colors">关于</a>
          <div class="bg-primary-from/15 border border-primary-from/30 rounded-full px-4 py-1.5 text-xs text-primary-from">
            已服务 500 万+ 用户
          </div>
        </nav>
      </div>
    </header>

    <!-- Hero Section -->
    <main class="container mx-auto px-4 py-20">
      <h1 class="text-6xl font-extrabold text-center mb-5 leading-tight">
        <span class="gradient-text">8K 无水印</span><br>
        视频一键下载
      </h1>
      <p class="text-gray-400 text-xl text-center mb-6">
        支持 YouTube、TikTok、Instagram 等 50+ 平台
      </p>

      <!-- Selling Points -->
      <div class="flex justify-center gap-6 mb-10">
        <div class="flex items-center gap-2 bg-primary-from/10 border border-primary-from/20 rounded-full px-5 py-2.5 text-sm text-primary-from">
          <span>⚡</span>
          <span>极速解析</span>
        </div>
        <div class="flex items-center gap-2 bg-primary-from/10 border border-primary-from/20 rounded-full px-5 py-2.5 text-sm text-primary-from">
          <span>🎬</span>
          <span>8K 超高清</span>
        </div>
        <div class="flex items-center gap-2 bg-primary-from/10 border border-primary-from/20 rounded-full px-5 py-2.5 text-sm text-primary-from">
          <span>🚫</span>
          <span>无水印</span>
        </div>
        <div class="flex items-center gap-2 bg-primary-from/10 border border-primary-from/20 rounded-full px-5 py-2.5 text-sm text-primary-from">
          <span>📦</span>
          <span>批量下载</span>
        </div>
      </div>

      <!-- Download Input -->
      <DownloadInput @parsed="handleParsed" />

      <!-- Quality Selector -->
      <QualitySelector
        v-if="videoInfo"
        :formats="videoInfo.formats"
        :selected="selectedQuality"
        @update="selectedQuality = $event"
      />

      <!-- Progress Tracker -->
      <ProgressTracker
        v-if="progress"
        :progress="progress"
        :filename="videoInfo?.title || 'video'"
        @download="handleDownloadFile"
      />

      <!-- Platform List -->
      <PlatformList />
    </main>

    <!-- Footer -->
    <footer class="text-center py-10 text-gray-600 text-sm border-t border-dark-border">
      <div class="flex justify-center gap-6 mb-4">
        <a href="#" class="hover:text-white transition-colors">关于我们</a>
        <a href="#" class="hover:text-white transition-colors">使用条款</a>
        <a href="#" class="hover:text-white transition-colors">隐私政策</a>
        <a href="#" class="hover:text-white transition-colors">联系我们</a>
      </div>
      <p>© 2024 VidSumAI. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import type { VideoInfo, ProgressUpdate } from '~/types'

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const videoInfo = ref<VideoInfo | null>(null)
const selectedQuality = ref('1080p')
const progress = ref<ProgressUpdate | null>(null)
const taskId = ref<string | null>(null)

let ws: WebSocket | null = null

const handleParsed = (info: VideoInfo) => {
  videoInfo.value = info
  progress.value = null
  if (info.formats.length > 0) {
    selectedQuality.value = info.formats[0].quality
  }
}

const handleDownload = async () => {
  if (!videoInfo.value) return

  try {
    const response = await $fetch<{ task_id: string }>(`${apiBase}/api/start-download`, {
      method: 'POST',
      body: { url: videoInfo.value.formats[0].url },
      params: { quality: selectedQuality.value }
    })

    taskId.value = response.task_id
    connectWebSocket(response.task_id)
  } catch (e: any) {
    alert('下载失败: ' + (e.data?.detail || '未知错误'))
  }
}

const connectWebSocket = (id: string) => {
  const wsUrl = apiBase.replace('http', 'ws') + `/api/ws/progress/${id}`

  ws = new WebSocket(wsUrl)

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    progress.value = data

    if (data.status === 'completed') {
      ws?.close()
    }
  }

  ws.onerror = () => {
    alert('连接错误，请重试')
  }
}

const handleDownloadFile = () => {
  if (taskId.value) {
    window.open(`${apiBase}/api/download/${taskId.value}`, '_blank')
  }
}
</script>
```

- [ ] **Step 2: Test complete flow**

Run: `cd frontend && npm run dev`
Expected: Full page with all components visible

- [ ] **Step 3: Commit**

```bash
git add frontend/pages/index.vue
git commit -m "feat: complete home page with all components integrated"
```

---

## Task 11: Final Testing

**Files:**
- None (testing only)

- [ ] **Step 1: Start backend server**

Run: `cd backend && uvicorn main:app --reload`
Expected: Backend running on http://localhost:8000

- [ ] **Step 2: Start frontend server**

Run: `cd frontend && npm run dev`
Expected: Frontend running on http://localhost:3000

- [ ] **Step 3: Test parse functionality**

1. Open http://localhost:3000
2. Paste a YouTube URL
3. Click "免费下载"
4. Verify video info appears with quality options

- [ ] **Step 4: Test download functionality**

1. Select a quality option
2. Click download
3. Verify progress bar appears and updates
4. Verify file downloads on completion

- [ ] **Step 5: Test error handling**

1. Enter an invalid URL
2. Verify error message appears
3. Enter a private/unavailable video URL
4. Verify appropriate error handling

- [ ] **Step 6: Commit final state**

```bash
git add -A
git commit -m "feat: VidSumAI MVP complete - video download with progress tracking"
```

---

## Summary

This plan implements a complete MVP video downloader with:

1. **Backend**: FastAPI with yt-dlp integration, REST API, WebSocket progress
2. **Frontend**: Vue/Nuxt.js with TailwindCSS, responsive dark theme
3. **Features**: URL parsing, quality selection, real-time progress, file download
4. **Design**: Inspired by snapvee.com with brand identity (red-yellow gradient)

Total tasks: 11
Estimated time: 2-3 hours for experienced developer
