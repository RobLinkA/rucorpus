<script setup lang="ts">
import { Check, Copy, PencilLine, SquareArrowOutUpRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import type { Group, Segment } from '@/api/types'
import AnnotationEditor from '@/components/AnnotationEditor.vue'
import AnnotationPills from '@/components/AnnotationPills.vue'
import FavoriteButton from '@/components/FavoriteButton.vue'
import HlText from '@/components/HlText.vue'
import { useMeta } from '@/stores/meta'
import { useSession } from '@/stores/session'

const props = withDefaults(defineProps<{
  group: Group
  activeValues?: number[]
  hiddenVersions?: number[]
  onlyHits?: boolean
  editable?: boolean
  showHeader?: boolean
}>(), { showHeader: true })

const meta = useMeta()
const session = useSession()
const copied = ref(false)
const editing = ref<Segment | null>(null)
const editOpen = ref(false)

const corpus = computed(() => meta.corpusById.get(props.group.corpus_id))
const versionCode = (vid: number) => {
  const vs = corpus.value?.versions.filter((v) => v.kind === 'translation') ?? []
  return `V${vs.findIndex((v) => v.id === vid) + 1}`
}
const rows = computed(() => props.group.rows.filter((r) => {
  if (props.hiddenVersions?.includes(r.version_id)) return false
  if (props.onlyHits && !r.segments.some((s) => s.hit)) return false
  return true
}))
const hitRows = computed(() => new Set(props.group.rows.filter((r) => r.segments.some((s) => s.hit)).map((r) => r.version_id)))
const partialHit = computed(() => hitRows.value.size > 0 && hitRows.value.size < props.group.rows.length)

async function copy() {
  const lines = [props.group.source, ...props.group.rows.map((r) =>
    `【${meta.versionById.get(r.version_id)?.label}】${r.segments.map((s) => s.target).join(' ')}`)]
  await navigator.clipboard.writeText(lines.join('\n'))
  copied.value = true
  setTimeout(() => { copied.value = false }, 1500)
}
function edit(s: Segment) {
  editing.value = s
  editOpen.value = true
}
</script>

<template>
  <article class="card card-hover overflow-hidden">
    <header v-if="showHeader" class="flex items-center gap-1.5 border-b border-line px-4 py-2 text-[12.5px] text-muted sm:px-5">
      <span class="truncate">{{ corpus?.name }}</span>
      <span class="text-line-strong">/</span>
      <RouterLink :to="{ name: 'read', params: { workId: group.work_id }, query: { around: group.id } }"
                  class="truncate font-sans text-[12.5px] font-medium text-ink-2 hover:text-accent">{{ meta.workTitle(group.work_id) }}</RouterLink>
      <span class="text-line-strong">/</span>
      <span class="shrink-0 tabular-nums">¶{{ group.paragraph_seq + 1 }}·{{ group.seq + 1 }}</span>
      <div class="ml-auto flex shrink-0 items-center">
        <button class="btn-icon size-7" :title="copied ? '已复制' : '复制'" aria-label="复制" @click="copy">
          <Check v-if="copied" class="size-3.5 text-ok" /><Copy v-else class="size-3.5" />
        </button>
        <RouterLink :to="{ name: 'group', params: { id: group.id } }" class="btn-icon size-7" title="句组详情" aria-label="句组详情">
          <SquareArrowOutUpRight class="size-3.5" />
        </RouterLink>
        <FavoriteButton v-model="group.favorite" :group-id="group.id" small />
      </div>
    </header>

    <div class="px-4 pt-3.5 pb-3.5 sm:px-5">
      <div class="mb-1 text-[11.5px] font-semibold tracking-wide text-accent">原文</div>
      <p class="corpus-text text-[16.5px]"><HlText :text="group.source" :spans="group.source_hl" /></p>
    </div>

    <div class="border-t border-line bg-surface-2/30">
      <div v-for="r in rows" :key="r.version_id"
           class="relative grid gap-x-4 gap-y-1.5 border-b border-line px-4 py-3 last:border-0 sm:grid-cols-[8.5rem_1fr] sm:px-5">
        <span v-if="partialHit && hitRows.has(r.version_id)" class="absolute inset-y-2 left-0 w-0.5 rounded-full bg-accent" />
        <div class="flex items-start gap-2 text-[12.5px] leading-6">
          <span class="mt-[3px] rounded bg-surface-2 px-1 text-[10.5px] leading-4 font-semibold text-muted">{{ versionCode(r.version_id) }}</span>
          <span class="text-ink-2">{{ meta.versionById.get(r.version_id)?.label }}</span>
        </div>
        <div class="space-y-2.5">
          <div v-for="s in r.segments" :key="s.id" class="group/seg">
            <p class="corpus-text text-[15.5px]"><HlText :text="s.target" :spans="s.target_hl" /></p>
            <div v-if="s.annotations.length || s.unsplit || (editable && session.canEdit)" class="mt-1.5 flex flex-wrap items-center gap-1.5">
              <span v-if="s.unsplit" class="tag" title="原始数据中该段未切分为句对">未切分整段</span>
              <AnnotationPills :values="s.annotations" :ai="s.ai" :active="activeValues" />
              <button v-if="editable && session.canEdit" class="btn-ghost btn-sm h-6 px-1.5 text-xs opacity-60 group-hover/seg:opacity-100"
                      @click="edit(s)"><PencilLine class="size-3.5" />标注</button>
            </div>
          </div>
        </div>
      </div>
    </div>
    <AnnotationEditor v-if="editing" v-model="editOpen" :segment-id="editing.id" :corpus-id="group.corpus_id"
                      :values="editing.annotations" :context="editing.target"
                      :ai="editing.ai" @saved="(v, ai) => { if (editing) { editing.annotations = v; editing.ai = ai } }" />
  </article>
</template>
