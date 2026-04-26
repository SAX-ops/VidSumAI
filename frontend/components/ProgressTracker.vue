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

    <div v-if="progress.status === 'completed'" class="mt-4 flex gap-3 justify-center">
      <button
        class="gradient-bg border-none rounded-xl px-6 py-3 text-white font-bold"
        @click="$emit('download')"
      >
        重新下载
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
