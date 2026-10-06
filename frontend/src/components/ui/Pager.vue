<script setup lang="ts">
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'

const props = defineProps<{ page: number; total: number; size: number }>()
const emit = defineEmits<{ go: [page: number] }>()
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.size)))
const jump = ref(String(props.page))
watch(() => props.page, (p) => { jump.value = String(p) })

const items = computed(() => {
  const n = pages.value, p = props.page
  const set = new Set([1, n, p - 1, p, p + 1, p - 2, p + 2].filter((x) => x >= 1 && x <= n))
  const sorted = [...set].sort((a, b) => a - b)
  const out: (number | '…')[] = []
  sorted.forEach((x, i) => {
    if (i && x - sorted[i - 1] > 1) out.push('…')
    out.push(x)
  })
  return out
})

function go(p: number) {
  const target = Math.min(Math.max(1, p), pages.value)
  if (target !== props.page) emit('go', target)
}
</script>

<template>
  <nav v-if="pages > 1" class="flex flex-wrap items-center justify-center gap-1 text-sm" aria-label="分页">
    <button class="btn-icon" :disabled="page <= 1" aria-label="上一页" @click="go(page - 1)"><ChevronLeft class="size-4" /></button>
    <template v-for="(it, i) in items" :key="i">
      <span v-if="it === '…'" class="px-1 text-muted">…</span>
      <button v-else class="h-9 min-w-9 rounded-lg px-2 text-[13.5px] tabular-nums transition"
              :class="it === page ? 'bg-accent text-accent-ink font-semibold' : 'text-ink-2 hover:bg-surface-3/60'"
              :aria-current="it === page ? 'page' : undefined" @click="go(it)">{{ it }}</button>
    </template>
    <button class="btn-icon" :disabled="page >= pages" aria-label="下一页" @click="go(page + 1)"><ChevronRight class="size-4" /></button>
    <form v-if="pages > 7" class="ml-2 flex items-center gap-1.5 text-muted" @submit.prevent="go(Number(jump))">
      跳至 <input v-model="jump" class="input h-8 w-14 px-2 text-center tabular-nums" inputmode="numeric" aria-label="页码" /> 页
    </form>
  </nav>
</template>
