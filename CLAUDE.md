# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

VidSumAI is a multi-platform video downloader with a dark, minimal UI and red-yellow gradient branding. Supports YouTube, TikTok, Instagram, and other yt-dlp-compatible platforms.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue 3 + Nuxt.js 3 + TailwindCSS |
| Backend | Python FastAPI |
| Download Engine | yt-dlp (Python API, not CLI) |
| Communication | REST API + WebSocket |

## Development Commands

### Backend (Python, uses `uv`)

```bash
cd backend
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000    # Start dev server
uv run pytest                                                     # Run all tests
uv run pytest tests/test_ytdlp.py                                 # Run single test file
uv run pytest -k test_parse_url                                   # Run single test by name
```

### Frontend (Nuxt 3)

```bash
cd frontend
npx nuxi dev                                                      # Start dev server (port 3000)
npx nuxi build                                                    # Production build
```

## Architecture

### Backend (`backend/`)

- **`main.py`** — FastAPI app entry point, CORS config (allows localhost:3000/3002)
- **`models.py`** — Pydantic models: `VideoInfo`, `FormatInfo`, `ParseRequest`, `DownloadTask`, `ProgressUpdate`
- **`routers/download.py`** — All API endpoints: `/api/parse`, `/api/start-download`, `/api/download/{task_id}`, `/ws/progress/{task_id}`, `/api/download-direct`
- **`services/ytdlp.py`** — `YtdlpService` class wrapping yt-dlp Python API. Key methods: `parse_url()` (extract video info), `start_download()` (begin async download with progress hooks)

**Critical pattern**: yt-dlp runs in a background thread via `asyncio.to_thread()` to avoid blocking the event loop. Progress updates flow through `progress_hooks` callback → in-memory task dict → WebSocket push to frontend.

**Known issue**: yt-dlp's `finished` hook returns `filename` of intermediate files (e.g., `.f398.mp4`) rather than the final merged `.mp4`. The download endpoint falls back to checking `backend/downloads/{task_id}.mp4` on disk.

### Frontend (`frontend/`)

- **`pages/index.vue`** — Main page: orchestrates URL parsing, video preview, download flow, WebSocket connection
- **`components/`** — `DownloadInput.vue` (URL input), `VideoPreview.vue` (thumbnail + quality selector + download button), `ProgressTracker.vue` (progress bar + status), `PlatformList.vue` (supported platforms display)
- **`composables/useWebSocket.ts`** — WebSocket composable for real-time progress (currently inline in index.vue; composable exists but not fully integrated)
- **`types/index.ts`** — TypeScript interfaces mirroring backend Pydantic models

**Data flow**: URL input → `POST /api/parse` → display preview → user selects quality → `POST /api/start-download` → WebSocket receives progress → on completion → `GET /api/download/{task_id}` → browser save dialog via blob URL.

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| POST | `/api/parse` | Extract video info (title, thumbnail, formats) |
| POST | `/api/start-download` | Start download task, returns `task_id` |
| GET | `/api/download/{task_id}` | Stream file as `video/mp4` with attachment header |
| WS | `/api/ws/progress/{task_id}` | Real-time progress: `{status, progress, speed, eta, downloaded}` |
| POST | `/api/open-folder` | Open folder in OS file explorer (Windows) |
| GET | `/api/proxy/image?url=<encoded_url>` | Proxy image requests (bypasses Bilibili Referer hotlink protection) |

## Important Notes

- **Python 必须通过 UV 运行**：本项目使用 UV 管理 Python 环境和依赖，不要直接调用 `python`、`pip` 等命令，一律使用 `uv run python ...`、`uv add ...`、`uv pip install ...`
- **Windows 环境**：本项目在 Windows 上开发，避免使用 Linux 专属命令（如 `chmod`、`ln -s`、`/dev/null`）。路径使用 `os.path.join()` 或 Windows 风格
- yt-dlp is used via Python API (`from yt_dlp import YoutubeDL`), NOT subprocess CLI calls
- Quality mapping uses format specs like `bestvideo[height<=1080]+bestaudio/best[height<=1080]`
- The `YtdlpService.tasks` dict holds all task state in memory — lost on backend restart
- Bilibili (B站) uses `visitor=true` extractor arg + custom headers (User-Agent, Referer, Origin) to bypass HTTP 412. Format selector must be `bestvideo+bestaudio/best` — `best` fails for Bilibili's format IDs (30080, 30280, etc.). Premium content (1080P+) still requires cookies.
- Frontend API base URL configured in `nuxt.config.ts` runtimeConfig: `http://localhost:8000`
- UI uses custom Tailwind colors: `primary-from` (#ff6b6b), `primary-to` (#feca57), `dark-bg` (#0a0a0f)
