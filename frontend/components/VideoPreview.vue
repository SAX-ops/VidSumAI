<template>
  <div v-if="videoInfo" class="max-w-2xl mx-auto mt-8 bg-dark-card border border-dark-border rounded-2xl overflow-hidden">
    <!-- Video/Thumbnail Area -->
    <div class="relative aspect-video bg-black">
      <!-- Thumbnail (shown when not playing) -->
      <img
        v-if="!isPlaying"
        :src="thumbnailUrl"
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
        已选画质：{{ qualityLabel }}
      </p>

      <!-- Quality Selector -->
      <div class="mt-3">
        <select
          v-model="selectedQuality"
          class="bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm w-full"
        >
          <option value="360p">360p（低清）.{{ qualityExt('360p') }}</option>
          <option value="720p">720p（标清）.{{ qualityExt('720p') }}</option>
          <option value="1080p">1080p（高清）.{{ qualityExt('1080p') }}</option>
          <option value="原画质">{{ videoInfo.max_quality }}（原画）.{{ qualityExt(videoInfo.max_quality) }}</option>
        </select>
      </div>
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
        class="flex-1 gradient-bg border-none rounded-xl py-3 text-white font-bold transition-all"
        :class="{
          'opacity-50 cursor-not-allowed hover:-translate-y-0 hover:shadow-none': isDownloading,
        }"
        :disabled="isDownloading"
        @click="handleDownload"
      >
        <span v-if="isDownloading">下载中 {{ safeProgress }}%</span>
        <span v-else>下载到本地</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { VideoInfo } from '~/types'

const props = defineProps<{
  videoInfo: VideoInfo
  modelValue: string
  isDownloading: boolean
  downloadProgress: number
}>()

const emit = defineEmits<{
  'update:modelValue': [quality: string]
  download: []
}>()

const config = useRuntimeConfig()
const apiBase = config.public.apiBase

const isPlaying = ref(false)
const selectedQuality = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

// Bilibili thumbnails need proxy to bypass Referer hotlink protection
const thumbnailUrl = computed(() => {
  if (props.videoInfo.platform === 'Bilibili' && props.videoInfo.thumbnail) {
    return `${apiBase}/api/proxy/image?url=${encodeURIComponent(props.videoInfo.thumbnail)}`
  }
  return props.videoInfo.thumbnail
})

// 安全进度值，防止 NaN 或 undefined
const safeProgress = computed(() => {
  const p = props.downloadProgress
  if (typeof p !== 'number' || isNaN(p) || p < 0) return 0
  return Math.round(p)
})

const handleDownload = () => {
  console.log('[VideoPreview] handleDownload called, isDownloading:', props.isDownloading)
  if (props.isDownloading) {
    console.log('[VideoPreview] Skipping because isDownloading is true')
    return
  }
  console.log('[VideoPreview] Emitting download event')
  emit('download')
}

const selectedFormatIndex = computed(() => {
  if (props.modelValue === '原画质') return 0
  return props.videoInfo.formats.findIndex(f => f.quality === props.modelValue)
})

const qualityLabel = computed(() => {
  const q = props.modelValue
  if (q === '原画质') return `${props.videoInfo.max_quality}（原画）`
  if (q === '360p') return '360p（低清）'
  if (q === '720p') return '720p（标清）'
  if (q === '1080p') return '1080p（高清）'
  return q
})

const qualityExt = (quality: string) => {
  const qualityMap: Record<string, string> = {
    '360p': '360p',
    '720p': '720p',
    '1080p': '1080p',
    '4K': '2160p',
    '2K': '1440p',
  }
  const formatQuality = qualityMap[quality] || quality
  const format = props.videoInfo.formats.find(f => f.quality === formatQuality)
  return format?.ext || 'mp4'
}

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
