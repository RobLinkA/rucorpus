<script setup lang="ts">
/* A filter popover: stays open while you work inside it; closes on outside click / Esc.
   On narrow screens it becomes a bottom sheet. */
import { onClickOutside, onKeyStroke } from '@vueuse/core'
import { ChevronDown } from 'lucide-vue-next'
import { ref, useTemplateRef } from 'vue'

withDefaults(defineProps<{ label: string; value?: string; active?: boolean; width?: string; align?: 'left' | 'right' }>(),
  { width: 'w-80', align: 'left' })
const open = ref(false)
const root = useTemplateRef<HTMLElement>('root')
onClickOutside(root, () => { open.value = false })
onKeyStroke('Escape', () => { open.value = false })
defineExpose({ close: () => { open.value = false } })
</script>

<template>
  <div ref="root" class="relative">
    <button type="button" class="inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-[13px] transition"
            :class="active ? 'border-accent/60 bg-accent-soft text-accent' : 'border-line-strong bg-surface text-ink-2 hover:border-accent/50 hover:text-ink'"
            :aria-label="value ? `${label}：${value}` : label" :aria-expanded="open" @click="open = !open">
      <span>{{ label }}</span>
      <span v-if="value" class="max-w-40 truncate font-medium">{{ value }}</span>
      <ChevronDown class="size-3.5 opacity-60 transition" :class="open && 'rotate-180'" />
    </button>
    <Transition name="pop">
      <div v-if="open"
           class="z-50 rounded-xl border border-line bg-surface shadow-lift max-sm:w-auto max-sm:fixed max-sm:inset-x-2 max-sm:bottom-2 max-sm:max-h-[75vh] max-sm:overflow-y-auto sm:absolute sm:mt-2"
           :class="[width, align === 'right' ? 'sm:right-0' : 'sm:left-0']" role="dialog" :aria-label="label">
        <slot :close="() => (open = false)" />
      </div>
    </Transition>
  </div>
</template>
