<script setup lang="ts">
import { computed } from 'vue'
import type { AiInfo } from '@/api/types'
import { useMeta } from '@/stores/meta'

const props = defineProps<{ values: number[]; active?: number[]; ai?: Record<number, AiInfo>; showEvidence?: boolean }>()
const meta = useMeta()

const METHOD: Record<string, string> = {
  'morph.nonfinite': '俄语词形分析', 'morph.forms': '俄语词形分析', 'morph.fix': '依词形更正人工标注',
  'syntax.definite': '依存句法分析', 'zh.redup': '叠词结构规则', 'zh.idiom': '成语词表与四字格式', 'zh.sound': '象声词词表',
}

const items = computed(() => props.values.map((id) => meta.valueById.get(id)).filter((v) => !!v).map((v) => {
  const ai = props.ai?.[v.id]
  const replaced = ai?.replaced ? meta.valueById.get(ai.replaced)?.label : undefined
  const title = ai
    ? [`✦ AI 标注 · ${v.group.name}：${v.label}`, `方法：${METHOD[ai.method] ?? ai.method}${ai.confidence === 'medium' ? '（中等置信）' : ''}`,
       ai.evidence && `依据：${ai.evidence}`, replaced && `原人工标注：${replaced}`].filter(Boolean).join('\n')
    : `${v.group.name}：${v.label}`
  return { ...v, color: meta.groupColor.get(v.group.id) ?? '#94a3b8', ai, replaced, title }
}))
</script>

<template>
  <span v-if="items.length" class="flex flex-wrap gap-1">
    <span v-for="v in items" :key="v.id" :title="v.title"
          class="inline-flex items-center gap-1.5 rounded-md px-1.5 py-[3px] text-[12px] leading-none text-ink-2"
          :class="v.ai && 'border border-dashed'"
          :style="{
            background: `color-mix(in srgb, ${v.color} ${active?.includes(v.id) ? 22 : v.ai ? 4 : 9}%, transparent)`,
            borderColor: v.ai ? `color-mix(in srgb, ${v.color} 55%, transparent)` : undefined,
            boxShadow: active?.includes(v.id) ? `inset 0 0 0 1px color-mix(in srgb, ${v.color} 55%, transparent)` : undefined,
          }">
      <span v-if="v.ai" class="text-[11px] leading-none" :style="{ color: v.color }" aria-label="AI 标注">✦</span>
      <span v-else class="size-1.5 shrink-0 rounded-full" :style="{ background: v.color }" />
      <span class="text-muted">{{ v.group.name }}</span>
      <span class="font-medium" :class="active?.includes(v.id) && 'text-ink'">{{ v.label }}</span>
      <span v-if="v.replaced" class="text-[11px] text-muted line-through decoration-muted/60">{{ v.replaced }}</span>
      <span v-if="showEvidence && v.ai?.evidence" class="font-serif text-[11.5px] text-muted italic">{{ v.ai.evidence }}</span>
    </span>
  </span>
</template>
