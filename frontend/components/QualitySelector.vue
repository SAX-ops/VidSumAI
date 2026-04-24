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
