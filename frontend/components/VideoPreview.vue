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

      <!-- Quality Selector -->
      <div class="mt-3">
        <select
          v-model="selectedQuality"
          class="bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white text-sm w-full"
        >
          <option value="360p">360p（低画质，省流量）</option>
          <option value="720p">720p（推荐，平衡质量与大小）</option>
          <option value="1080p">1080p（高清）</option>
          <option value="原画质">原画质（视频最佳）</option>
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
  modelValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [quality: string]
  download: []
}>()

const isPlaying = ref(false)
const selectedQuality = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const selectedFormatIndex = computed(() => {
  return props.videoInfo.formats.findIndex(f => f.quality === props.modelValue)
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