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

## Task 1: Update Backend Models

**Files:**
- Modify: `backend/models.py`

- [ ] **Step 1: Read current models.py**

Run: Read `backend/models.py`

- [ ] **Step 2: Add platform and url fields**

```python
class FormatInfo(BaseModel):
    quality: str
    ext: str
    size: Optional[int] = None
    url: str  # Direct playback URL for preview


class VideoInfo(BaseModel):
    title: str
    thumbnail: str
    duration: Optional[int] = None
    platform: str  # "YouTube", "TikTok", etc.
    formats: List[FormatInfo]
```

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: add platform and url fields to VideoInfo/Format models"
```

---

## Task 2: Update Backend yt-dlp Service to Extract Platform and URL

**Files:**
- Modify: `backend/services/ytdlp.py`

- [ ] **Step 1: Read current ytdlp.py**

Run: Read `backend/services/ytdlp.py`

- [ ] **Step 2: Add platform extraction function**

```python
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
```

- [ ] **Step 3: Update parse_url to include platform and url**

Find the `parse_url` method and update the FormatInfo creation to include url:

```python
formats.append(FormatInfo(
    quality=quality,
    ext=f.get("ext", "mp4"),
    size=f.get("filesize") or f.get("filesize_approx"),
    url=f.get("url", "")  # Direct playback URL
))
```

And update VideoInfo return:

```python
return VideoInfo(
    title=data.get("title", "Unknown"),
    thumbnail=data.get("thumbnail", ""),
    duration=data.get("duration"),
    platform=self._extract_platform(url),
    formats=unique_formats[:10]
)
```

- [ ] **Step 4: Commit**

```bash
git add backend/services/ytdlp.py
git commit -m "feat: extract platform name and include format url"
```

---

## Task 3: Add Backend /api/open-folder Endpoint

**Files:**
- Modify: `backend/routers/download.py`

- [ ] **Step 1: Read current download.py**

Run: Read `backend/routers/download.py`

- [ ] **Step 2: Add open-folder endpoint**

Add after existing endpoints:

```python
@router.post("/open-folder")
async def open_folder(folder_path: str = None):
    """Open the specified folder in file explorer (Windows)"""
    import os
    import subprocess

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
```

- [ ] **Step 3: Commit**

```bash
git add backend/routers/download.py
git commit -m "feat: add open-folder endpoint to open downloads directory"
```

---

## Task 4: Create VideoPreview Component

**Files:**
- Create: `frontend/components/VideoPreview.vue`

- [ ] **Step 1: Create VideoPreview.vue**

```vue
<template>
  <div v-if="videoInfo" class="max-w-2xl mx-auto mt-8 bg-dark-card border border-dark-border rounded-2xl overflow-hidden">
    <!-- Video/Thumbnail Area -->
    <div class="relative aspect-video bg-black">
      <!-- Thumbnail (shown when not playing) -->
      <img
        v-if="!isPlaying"
        :src="videoInfo.thumbnail"
        class="w-full h-full object-contain"
        alt="Video thumbnail"
      />

      <!-- Video Player (shown when playing) -->
      <video
        v-if="isPlaying && videoInfo.formats[selectedFormatIndex]?.url"
        ref="videoPlayer"
        :src="videoInfo.formats[selectedFormatIndex].url"
        class="w-full h-full object-contain"
        controls
        autoplay
        @error="onVideoError"
      />

      <!-- Play Button Overlay -->
      <div
        v-if="!isPlaying"
        class="absolute inset-0 flex items-center justify-center bg-black/30 cursor-pointer"
        @click="startPreview"
      >
        <div class="w-20 h-20 rounded-full gradient-bg flex items-center justify-center text-3xl">
          ▶
        </div>
      </div>
    </div>

    <!-- Video Info -->
    <div class="p-6">
      <div class="flex items-center gap-2 text-sm text-gray-400 mb-2">
        <span class="bg-primary-from/20 text-primary-from px-2 py-0.5 rounded">
          {{ videoInfo.platform }}
        </span>
        <span v-if="videoInfo.duration">
          {{ formatDuration(videoInfo.duration) }}
        </span>
      </div>
      <h3 class="text-white text-lg font-semibold mb-4">
        {{ videoInfo.title }}
      </h3>
      <p class="text-gray-500 text-sm">
        已选画质：{{ selectedQuality }}
      </p>
    </div>

    <!-- Action Buttons -->
    <div class="px-6 pb-6 flex gap-4">
      <button
        class="flex-1 bg-white/10 border border-white/20 rounded-xl py-3 text-white font-semibold hover:bg-white/20 transition-all"
        @click="startPreview"
      >
        {{ isPlaying ? '重新预览' : '预览视频' }}
      </button>
      <button
        class="flex-1 gradient-bg border-none rounded-xl py-3 text-white font-bold hover:-translate-y-1 hover:shadow-[0_12px_32px_rgba(255,107,107,0.5)] transition-all"
        @click="$emit('download')"
      >
        下载到本地
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { VideoInfo } from '~/types'

const props = defineProps<{
  videoInfo: VideoInfo
  selectedQuality: string
}>()

const emit = defineEmits<{
  download: []
}>()

const isPlaying = ref(false)
const selectedFormatIndex = computed(() => {
  return props.videoInfo.formats.findIndex(f => f.quality === props.selectedQuality)
})

const startPreview = () => {
  isPlaying.value = true
}

const onVideoError = () => {
  alert('视频预览加载失败，请尝试其他清晰度或重新解析')
  isPlaying.value = false
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
</script>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/components/VideoPreview.vue
git commit -m "feat: add VideoPreview component with thumbnail and playback"
```

---

## Task 5: Update Frontend index.vue - Header and Flow

**Files:**
- Modify: `frontend/pages/index.vue`

- [ ] **Step 1: Read current index.vue**

Run: Read `frontend/pages/index.vue`

- [ ] **Step 2: Update header title and selling points**

Find and update:
```javascript
// Change from:
<h1 class="text-6xl font-extrabold text-center mb-5 leading-tight">
  <span class="gradient-text">8K 无水印</span><br>
  视频一键下载
</h1>

// To:
<h1 class="text-6xl font-extrabold text-center mb-5 leading-tight">
  <span class="gradient-text">无水印高清</span><br>
  视频一键下载
</h1>
```

Update selling points:
```html
<!-- Change from 8K Ultra HD and batch download tags -->
<div class="flex items-center gap-2 bg-primary-from/10 border border-primary-from/20 rounded-full px-5 py-2.5 text-sm text-primary-from">
  <span>🎬</span>
  <span>4K 超高清</span>
</div>
<!-- Remove 批量下载 tag -->
```

- [ ] **Step 3: Add VideoPreview to template**

Replace QualitySelector section with VideoPreview:

```html
<!-- Video Preview -->
<VideoPreview
  v-if="videoInfo"
  :video-info="videoInfo"
  :selected-quality="selectedQuality"
  @download="handleDownload"
/>

<!-- Remove old QualitySelector and DownloadButton from here since they're now in VideoPreview -->
```

- [ ] **Step 4: Update script to remove duplicate QualitySelector and DownloadButton**

Remove the old QualitySelector and the download button that were in index.vue since they're now in VideoPreview.

- [ ] **Step 5: Commit**

```bash
git add frontend/pages/index.vue
git commit -m "feat: update header text and integrate VideoPreview component"
```

---

## Task 6: Update ProgressTracker - Add Open Folder Button

**Files:**
- Modify: `frontend/components/ProgressTracker.vue`

- [ ] **Step 1: Read current ProgressTracker.vue**

Run: Read `frontend/components/ProgressTracker.vue`

- [ ] **Step 2: Add open folder functionality**

Add new function:

```javascript
const openFolder = async () => {
  try {
    await $fetch(`${config.public.apiBase}/api/open-folder`, {
      method: 'POST'
    })
  } catch (e) {
    console.error('Failed to open folder:', e)
  }
}
```

Add button in template after download completes:

```html
<div v-if="progress.status === 'completed'" class="mt-4 flex gap-3 justify-center">
  <button
    class="bg-white/10 border border-white/20 rounded-xl px-6 py-3 text-white font-semibold hover:bg-white/20"
    @click="openFolder"
  >
    📁 打开文件夹
  </button>
  <button
    class="gradient-bg border-none rounded-xl px-6 py-3 text-white font-bold"
    @click="$emit('download')"
  >
    重新下载
  </button>
</div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ProgressTracker.vue
git commit -m "feat: add open folder button to ProgressTracker"
```

---

## Task 7: Integration Test

**Files:**
- Test: Full flow

- [ ] **Step 1: Start backend**

Run:
```bash
cd backend && uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: Start frontend**

Run:
```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Test full flow in browser**

1. Open http://localhost:3000
2. Enter YouTube URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
3. Click "解析"
4. Verify video info shows (title, platform, thumbnail)
5. Select quality (e.g., 1080p)
6. Click "预览视频" - verify video plays
7. Click "下载到本地" - verify download starts
8. Wait for download to complete
9. Verify "打开文件夹" button appears
10. Click "打开文件夹" - verify explorer opens

- [ ] **Step 4: Fix any issues found**

---

## Verification Checklist

- [ ] Backend parse returns `platform` field
- [ ] Backend parse returns format `url` for preview
- [ ] Backend /api/open-folder works
- [ ] Frontend shows VideoPreview after parse
- [ ] Preview video plays correctly
- [ ] Download works with progress
- [ ] Open folder button appears after download completes
- [ ] Open folder opens Windows Explorer
