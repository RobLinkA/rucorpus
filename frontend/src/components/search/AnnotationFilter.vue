<script setup lang="ts">
/* Annotation filter: tick to include, "排除" to exclude. Logic and source are plain-language options. */
import { Ban, Check, Search, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import type { Corpus, SearchParams } from '@/api/types'
import { useMeta } from '@/stores/meta'

const props = defineProps<{ params: Required<SearchParams>; corpora: Corpus[]; counts?: Map<number, number> }>()
const emit = defineEmits<{ change: [patch: Partial<SearchParams>] }>()
const meta = useMeta()
const text = ref('')

const groups = computed(() => props.corpora.flatMap((c) => c.annotation_groups.map((g) => ({
  ...g, corpusName: c.name,
  values: g.values.filter((v) => !text.value.trim() || v.label.includes(text.value.trim()) || g.name.includes(text.value.trim())),
}))).filter((g) => g.values.length))

const count = (id: number, usage: number) => (props.counts ? props.counts.get(id) ?? 0 : usage)

function include(id: number) {
  const on = props.params.values.includes(id)
  emit('change', {
    values: on ? props.params.values.filter((x) => x !== id) : [...props.params.values, id],
    exclude: props.params.exclude.filter((x) => x !== id),
  })
}
function excludeValue(id: number) {
  const on = props.params.exclude.includes(id)
  emit('change', {
    exclude: on ? props.params.exclude.filter((x) => x !== id) : [...props.params.exclude, id],
    values: props.params.values.filter((x) => x !== id),
  })
}
const LOGIC = [
  { v: 'group', t: '每组至少一项', d: '同一标注组内满足其一；选了几个组，就要同时满足几个组' },
  { v: 'or', t: '满足任一项', d: '只要满足任意一个所选标注项' },
  { v: 'and', t: '全部满足', d: '所选标注项全部满足' },
] as const
</script>

<template>
  <div class="flex max-h-[70vh] flex-col">
    <div class="border-b border-line p-3">
      <div class="relative">
        <Search class="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted" />
        <input v-model="text" class="input h-8 pl-8 text-[13px]" placeholder="查找标注项，如：副动词、四字格" aria-label="查找标注项" />
      </div>
    </div>

    <div class="min-h-0 flex-1 overflow-y-auto px-1.5 py-2">
      <p v-if="!groups.length" class="px-3 py-6 text-center text-[13px] text-muted">没有匹配的标注项</p>
      <section v-for="g in groups" :key="g.id" class="mb-1">
        <h4 class="flex items-center gap-2 px-2.5 pt-2 pb-1 text-[12px] font-semibold text-ink-2">
          <span class="size-2 rounded-full" :style="{ background: meta.groupColor.get(g.id) }" />{{ g.name }}
          <span v-if="corpora.length > 1" class="font-normal text-muted">{{ g.corpusName }}</span>
        </h4>
        <div v-for="v in g.values" :key="v.id"
             class="group/row flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-[13.5px] hover:bg-surface-2"
             :class="params.exclude.includes(v.id) && 'bg-seal-soft/60'">
          <button type="button" class="flex min-w-0 flex-1 items-center gap-2.5 text-left" @click="include(v.id)">
            <span class="grid size-4 shrink-0 place-items-center rounded border transition"
                  :class="params.values.includes(v.id) ? 'border-accent bg-accent text-accent-ink' : params.exclude.includes(v.id) ? 'border-seal bg-seal text-white' : 'border-line-strong bg-surface'">
              <Check v-if="params.values.includes(v.id)" class="size-3" /><X v-else-if="params.exclude.includes(v.id)" class="size-3" />
            </span>
            <span class="truncate" :class="params.exclude.includes(v.id) && 'text-seal line-through'">{{ v.label }}</span>
          </button>
          <span class="text-[12px] text-muted tabular-nums">{{ count(v.id, v.usage) }}</span>
          <button type="button" class="rounded px-1.5 py-0.5 text-[12px] transition"
                  :class="params.exclude.includes(v.id) ? 'text-seal' : 'text-muted opacity-0 group-hover/row:opacity-100 focus:opacity-100 hover:text-seal'"
                  :title="params.exclude.includes(v.id) ? '取消排除' : '排除含此标注的句子'" @click="excludeValue(v.id)">
            <Ban class="inline size-3.5" /> 排除
          </button>
        </div>
      </section>
    </div>

    <div class="space-y-2.5 border-t border-line p-3 text-[12.5px]">
      <label class="flex items-center gap-2">
        <span class="w-14 shrink-0 text-muted">多项之间</span>
        <select class="input h-8 text-[13px]" :value="params.logic" :disabled="params.values.length < 2"
                @change="emit('change', { logic: ($event.target as HTMLSelectElement).value as 'or' | 'and' | 'group' })">
          <option v-for="l in LOGIC" :key="l.v" :value="l.v">{{ l.t }}</option>
        </select>
      </label>
      <label class="flex items-center gap-2">
        <span class="w-14 shrink-0 text-muted">标注来源</span>
        <select class="input h-8 text-[13px]" :value="params.origin"
                @change="emit('change', { origin: ($event.target as HTMLSelectElement).value as 'all' | 'human' | 'ai' })">
          <option value="all">人工与 ✦ AI 标注</option>
          <option value="human">仅人工标注</option>
          <option value="ai">仅 ✦ AI 标注</option>
        </select>
      </label>
      <p v-if="params.values.length > 1" class="text-[11.5px] text-muted">{{ LOGIC.find((l) => l.v === params.logic)?.d }}</p>
    </div>
  </div>
</template>
