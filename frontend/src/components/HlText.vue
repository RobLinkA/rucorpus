<script setup lang="ts">
import { computed } from 'vue'
import type { Span } from '@/api/types'

const props = defineProps<{ text: string; spans?: Span[] }>()
const parts = computed(() => {
  const out: { t: string; hl: boolean }[] = []
  let pos = 0
  for (const [a, b] of props.spans ?? []) {
    if (a > pos) out.push({ t: props.text.slice(pos, a), hl: false })
    out.push({ t: props.text.slice(a, b), hl: true })
    pos = b
  }
  if (pos < props.text.length) out.push({ t: props.text.slice(pos), hl: false })
  return out
})
</script>

<template>
  <span><template v-for="(p, i) in parts" :key="i"><mark v-if="p.hl" class="hl">{{ p.t }}</mark><template v-else>{{ p.t }}</template></template></span>
</template>
