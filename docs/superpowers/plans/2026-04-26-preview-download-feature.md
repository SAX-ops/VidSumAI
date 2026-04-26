# Preview-Download Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add preview-before-download flow and download folder selection with open folder button.

**Architecture:** Backend adds `/api/open-folder` endpoint. Frontend adds `VideoPreview.vue` component and integrates preview/download/folder flow. Parse API returns `platform` field and format `url` for preview playback.

**Tech Stack:** Vue 3 + Nuxt.js + TailwindCSS (frontend), Python FastAPI + yt-dlp (backend)

---

## File Structure

### Backend Changes
- `backend/models.py` - Add `platform` field to VideoInfo, add `url` to Format
- `backend/routers/download.py` - Add `/api/open-folder` endpoint
- `backend/services/ytdlp.py` - Extract platform name from URL, include url in format

### Frontend Changes
- `frontend/pages/index.vue` - Update header text, integrate VideoPreview, update download flow
- `frontend/components/VideoPreview.vue` - New component for preview player
- `frontend/components/ProgressTracker.vue` - Add "open folder" button after download

---

## Implementation Notes

### Issues Fixed During Implementation

1. **进度条实时更新**
   - `ytdlp.py` 的 `_run_download` 使用 threading + queue 阻塞事件循环，改用纯 async subprocess
   - yt-dlp stdout 被缓冲，添加 `--newline` 参数解决
   - 正则表达式无法匹配多个空格，修复为 `%s+of%s+` 和 `ats+`

2. **清晰度选择**
   - `VideoPreview.vue` 中 `qualityMap` 有重复键 `'1080p'`，已清理
   - 后端 format_map 统一映射

3. **B站解析**
   - B站需要登录 Cookies，添加了 User-Agent 和 Referer 请求头但仍返回 412
   - 暂时搁置，需 Cookies 方案

### Key Code Patterns

**yt-dlp 进度解析正则（已修复）：**
```python
# 百分比和大小
match = re.search(r'([\d.]+)%\s+of\s+([~]?[\d.]+[KMGT]i?B)', line)
# 速度
speed_match = re.search(r'at\s+([\d.]+\s*[KMGT]i?B/s)', line)
# ETA
eta_match = re.search(r'ETA\s+([\d:]+)', line)
```

**yt-dlp 命令（带请求头）：**
```python
cmd = [
    "yt-dlp",
    "-f", format_spec,
    "--merge-output-format", "mp4",
    "--newline",
    "--add-header", "User-Agent:Mozilla/5.0 ...",
    "--add-header", "Referer:https://www.bilibili.com",
    "-o", output_path,
    url
]
```

**async subprocess 进度读取：**
```python
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

async for line in read_stream():
    # 解析进度...
    await asyncio.sleep(0.05)  # 让出控制权给事件循环
```

---

## Task 1: Update Backend Models ✅

**Status:** COMPLETED

- [x] Add `platform` field to VideoInfo
- [x] Add `url` field to FormatInfo
- [x] Commit: `backend/models.py`

---

## Task 2: Update Backend yt-dlp Service ✅

**Status:** COMPLETED

- [x] Add `_extract_platform()` function
- [x] Include format `url` in parse response
- [x] Add User-Agent and Referer headers for B站
- [x] Fix progress regex for multiple spaces
- [x] Fix async subprocess for real-time progress
- [x] Commit: `backend/services/ytdlp.py`

---

## Task 3: Add Backend /api/open-folder Endpoint ✅

**Status:** COMPLETED

- [x] Add `/api/open-folder` endpoint
- [x] Open Windows Explorer with downloads folder
- [x] Commit: `backend/routers/download.py`

---

## Task 4: Create VideoPreview Component ✅

**Status:** COMPLETED

- [x] Create `VideoPreview.vue` with thumbnail display
- [x] Add video player for preview
- [x] Add quality selector
- [x] Fix qualityMap duplicate key issue
- [x] Commit: `frontend/components/VideoPreview.vue`

---

## Task 5: Update Frontend index.vue - Header and Flow ✅

**Status:** COMPLETED

- [x] Update header title and selling points
- [x] Integrate VideoPreview component
- [x] Add ProgressTracker component
- [x] WebSocket for real-time progress
- [x] Auto-trigger download after completion
- [x] Commit: `frontend/pages/index.vue`

---

## Task 6: Update ProgressTracker - Add Open Folder Button ✅

**Status:** COMPLETED

- [x] Add "打开文件夹" button
- [x] Display progress percentage
- [x] Display speed and ETA
- [x] Display downloaded size
- [x] Commit: `frontend/components/ProgressTracker.vue`

---

## Task 7: Integration Test ✅

**Status:** COMPLETED

**Verified working:**
- [x] Backend parse returns `platform` field
- [x] Backend parse returns format `url` for preview
- [x] Backend `/api/open-folder` works
- [x] Frontend shows VideoPreview after parse
- [x] Preview video plays correctly
- [x] Download works with real-time progress (0% → 100%)
- [x] Progress shows: percentage, speed, ETA, downloaded size
- [x] Open folder button appears after download completes

**Known limitations:**
- B站视频解析需要登录 Cookies（暂时 not supported）
- YouTube preview URLs may expire (expected behavior)

---

## Pending / Future Tasks

### B站支持（需 Cookies）
- [ ] 从浏览器导出 B站 cookies
- [ ] 添加 `--cookies` 参数到 yt-dlp 命令
- [ ] 测试 B站视频解析和下载

### 优化项
- [ ] 任务暂停/恢复功能
- [ ] 多任务并行下载
- [ ] 下载历史记录
- [ ] 自定义下载路径选择器

---

## Verification Checklist

- [x] Backend parse returns `platform` field
- [x] Backend parse returns format `url` for preview
- [x] Backend /api/open-folder works
- [x] Frontend shows VideoPreview after parse
- [x] Preview video plays correctly
- [x] Download works with real-time progress
- [x] Progress updates: percentage, speed, ETA, downloaded size
- [x] Open folder button appears after download completes
- [x] Open folder opens Windows Explorer
