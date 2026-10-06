<script setup lang="ts">
import { onClickOutside, onKeyStroke } from '@vueuse/core'
import { ref, useTemplateRef, watch } from 'vue'
import { useRoute } from 'vue-router'

withDefaults(defineProps<{ align?: 'left' | 'right'; width?: string }>(), { align: 'left', width: 'w-52' })
const open = ref(false)
const root = useTemplateRef<HTMLElement>('root')
const route = useRoute()
onClickOutside(root, () => { open.value = false })
onKeyStroke('Escape', () => { open.value = false })
watch(() => route.fullPath, () => { open.value = false })
defineExpose({ close: () => { open.value = false } })
</script>

<template>
  <div ref="root" class="relative">
    <div @click="open = !open"><slot name="trigger" :open="open" /></div>
    <Transition name="pop">
      <div v-if="open" role="menu"
           class="absolute z-50 mt-1.5 rounded-xl border border-line bg-surface p-1 shadow-card"
           :class="[align === 'right' ? 'right-0' : 'left-0', width]" @click="open = false">
        <slot />
      </div>
    </Transition>
  </div>
</template>

<style>
.menu-item {
  display: flex; align-items: center; gap: .6rem; padding: .45rem .65rem; border-radius: .5rem;
  font-size: .875rem; color: var(--ink-2); text-align: left; cursor: pointer;
}
.menu-item:hover { background: var(--surface-2); color: var(--ink); }
</style>
