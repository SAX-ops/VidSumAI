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
