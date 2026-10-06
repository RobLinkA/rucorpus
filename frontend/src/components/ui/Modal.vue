<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { X } from 'lucide-vue-next'

const props = withDefaults(defineProps<{ title?: string; width?: string; dismissable?: boolean }>(),
  { width: 'max-w-lg', dismissable: true })
const open = defineModel<boolean>({ default: false })
onKeyStroke('Escape', () => { if (open.value && props.dismissable) open.value = false })
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto bg-black/35 p-4 pt-[8vh] backdrop-blur-[2px]"
           @mousedown.self="dismissable && (open = false)">
        <div role="dialog" aria-modal="true" :aria-label="title" class="card w-full" :class="width">
          <div v-if="title" class="flex items-center justify-between border-b border-line px-5 py-3.5">
            <h2 class="text-[15px] font-semibold">{{ title }}</h2>
            <button class="btn-icon -mr-2 size-8" aria-label="关闭" @click="open = false"><X class="size-4" /></button>
          </div>
          <div class="px-5 py-4"><slot /></div>
          <div v-if="$slots.footer" class="flex justify-end gap-2 border-t border-line px-5 py-3"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
