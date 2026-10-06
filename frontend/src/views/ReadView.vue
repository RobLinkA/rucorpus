<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { Columns3, LoaderCircle, Tags } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Group } from '@/api/types'
import AnnotationPills from '@/components/AnnotationPills.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import Pager from '@/components/ui/Pager.vue'
import { useMeta } from '@/stores/meta'

interface ReadResponse { work_id: number; corpus_id: number; total: number; page: number; size: number; paragraphs: number; groups: Group[] }

const route = useRoute()
const router = useRouter()
const meta = useMeta()
const data = ref<ReadResponse | null>(null)
const loading = ref(false)
const error = ref('')
const hidden = ref<Set<number>>(new Set())
const showAnn = ref(true)

const workId = computed(() => Number(route.params.workId) || 0)
const mode = computed(() => (route.query.mode === 'para' ? 'para' : 'sent'))
const size = computed(() => [20, 40, 80, 160].includes(Number(route.query.size)) ? Number(route.query.size) : 40)
const around = computed(() => Number(route.query.around) || 0)
const work = computed(() => meta.workById.get(workId.value))
const corpus = computed(() => (work.value ? meta.corpusById.get(work.value.corpus_id) : undefined))
const translations = computed(() => corpus.value?.versions.filter((v) => v.kind === 'translation') ?? [])
const visible = computed(() => translations.value.filter((v) => !hidden.value.has(v.id)))

watch([() => meta.loaded, workId], () => {
  if (meta.loaded && !workId.value) {
    const first = meta.corpora.find((c) => c.works.length)?.works[0]
    if (first) router.replace({ name: 'read', params: { workId: first.id } })
  }
}, { immediate: true })

watch(() => [workId.value, route.query.page, size.value, around.value], async () => {
  if (!workId.value) return
  loading.value = true
  error.value = ''
  try {
    data.value = await api.get<ReadResponse>(`/read/${workId.value}`, {
      page: Number(route.query.page) || 1, size: size.value, around: around.value || undefined })
    if (around.value) {
      await nextTick()
      document.getElementById(`g${around.value}`)?.scrollIntoView({ block: 'center' })
    }
  } catch (e) { error.value = e instanceof Error ? e.message : String(e) } finally { loading.value = false }
}, { immediate: true })

const textOf = (g: Group, vid: number) => g.rows.find((r) => r.version_id === vid)?.segments ?? []

// paragraph mode: merge consecutive groups of the same paragraph
const paragraphs = computed(() => {
  const out: { id: number; seq: number; first: number; source: string; targets: Record<number, string> }[] = []
  for (const g of data.value?.groups ?? []) {
    let p = out[out.length - 1]
    if (!p || p.id !== g.paragraph_id) {
      p = { id: g.paragraph_id, seq: g.paragraph_seq, first: g.id, source: '', targets: {} }
      out.push(p)
    }
    p.source += (p.source ? ' ' : '') + g.source
    for (const r of g.rows) {
      const lang = meta.versionById.get(r.version_id)?.lang ?? corpus.value?.target_lang
      const separator = lang === 'zh' || lang === 'ja' ? '' : ' '
      p.targets[r.version_id] = [p.targets[r.version_id] ?? '', ...r.segments.map((s) => s.target)]
        .map((text) => text.trim()).filter(Boolean).join(separator)
    }
  }
  return out
})

function setQuery(patch: Record<string, string | undefined>) {
  router.push({ query: { ...route.query, around: undefined, ...patch } })
}
function go(page: number) {
  setQuery({ page: String(page) })
  window.scrollTo({ top: 0 })
}
const pages = computed(() => data.value ? Math.max(1, Math.ceil(data.value.total / data.value.size)) : 1)

onKeyStroke(['ArrowLeft', 'ArrowRight'], (e) => {
  if (e.defaultPrevented || e.isComposing || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return
  const target = e.target
  if (target instanceof HTMLElement && (target.isContentEditable || target.closest(
    'input, textarea, select, [role="textbox"], [role="combobox"], [role="slider"], [role="radiogroup"]',
  ))) return
  // Menus can be open while focus is still on their trigger button.
  if (document.querySelector('[role="menu"], [role="dialog"]')) return
  const current = data.value
  if (!current || loading.value || error.value || current.work_id !== workId.value) return
  const page = current.page + (e.key === 'ArrowRight' ? 1 : -1)
  if (page < 1 || page > pages.value) return
  e.preventDefault()
  go(page)
}, { dedupe: true })

function toggleVersion(id: number) {
  const s = new Set(hidden.value)
  if (s.has(id)) s.delete(id)
  else if (visible.value.length > 1) s.add(id)
  hidden.value = s
}
const progress = computed(() => data.value ? Math.min(100, Math.round(((data.value.page - 1) * data.value.size + data.value.groups.length) / data.value.total * 100)) : 0)
</script>

<template>
  <div class="mx-auto max-w-[1500px] px-4 py-6 sm:px-6">
    <p v-if="meta.loaded && !meta.corpora.some((c) => c.works.length)" class="card mb-6 p-6 text-sm text-muted">暂无可阅读作品，请先导入语料。</p>
    <div class="flex flex-wrap items-end gap-x-6 gap-y-3">
      <div class="min-w-0">
        <div class="text-[13px] text-muted">{{ corpus?.name }}</div>
        <h1 class="font-display text-2xl font-semibold sm:text-3xl">
          {{ work?.title_target || work?.title_source }}
          <span v-if="work?.title_target && work.title_target !== work.title_source" class="ml-2 text-lg font-normal text-muted">{{ work.title_source }}</span>
        </h1>
      </div>
      <label class="ml-auto flex items-center gap-2 text-sm">
        <span class="text-muted">作品</span>
        <select class="input h-9 w-56" :value="workId" aria-label="选择作品"
                @change="router.push({ name: 'read', params: { workId: ($event.target as HTMLSelectElement).value } })">
          <optgroup v-for="c in meta.corpora.filter((x) => x.works.length)" :key="c.id" :label="c.name">
            <option v-for="w in c.works" :key="w.id" :value="w.id">{{ w.title_target || w.title_source }}</option>
          </optgroup>
        </select>
      </label>
    </div>

    <div class="sticky top-14 z-30 -mx-4 mt-4 flex flex-wrap items-center gap-2 border-y border-line bg-bg/90 px-4 py-2 backdrop-blur sm:-mx-6 sm:px-6">
      <div class="inline-flex rounded-lg bg-surface-2 p-0.5 text-[13px]" role="radiogroup" aria-label="粒度">
        <button v-for="m in [{ v: 'sent', l: '句' }, { v: 'para', l: '段' }]" :key="m.v" role="radio" :aria-checked="mode === m.v"
                class="rounded-md px-3 py-1" :class="mode === m.v ? 'bg-surface text-ink shadow-card font-medium' : 'text-muted'"
                @click="setQuery({ mode: m.v === 'para' ? 'para' : undefined })">按{{ m.l }}对照</button>
      </div>
      <Dropdown width="w-60">
        <template #trigger><button class="btn-ghost btn-sm"><Columns3 class="size-4" />译本列 {{ visible.length }}/{{ translations.length }}</button></template>
        <div @click.stop>
          <label v-for="v in translations" :key="v.id" class="menu-item cursor-pointer">
            <input type="checkbox" class="accent-[var(--accent)]" :checked="!hidden.has(v.id)" @change="toggleVersion(v.id)" />{{ v.label }}
          </label>
        </div>
      </Dropdown>
      <label v-if="mode === 'sent'" class="btn-ghost btn-sm cursor-pointer">
        <input v-model="showAnn" type="checkbox" class="accent-[var(--accent)]" /><Tags class="size-4" />显示标注
      </label>
      <LoaderCircle v-if="loading" class="size-4 animate-spin text-muted" />
      <div class="ml-auto flex items-center gap-3 text-[13px] text-muted">
        <span v-if="data" class="hidden tabular-nums sm:inline">{{ data.total.toLocaleString() }} 句组 · {{ data.paragraphs }} 段</span>
        <div v-if="data" class="hidden h-1.5 w-28 overflow-hidden rounded-full bg-surface-2 sm:block" :title="`${progress}%`">
          <div class="h-full rounded-full bg-accent" :style="{ width: progress + '%' }" />
        </div>
        <select class="input h-8 w-auto pr-7 text-[13px]" :value="size" aria-label="每页"
                @change="setQuery({ size: ($event.target as HTMLSelectElement).value, page: '1' })">
          <option v-for="n in [20, 40, 80, 160]" :key="n" :value="n">每页 {{ n }} 句组</option>
        </select>
      </div>
    </div>

    <div v-if="error" class="card mt-6 px-5 py-4 text-sm text-seal">{{ error }}</div>

    <div v-if="data && pages > 1" class="mt-3 flex items-center justify-between gap-3 text-xs text-muted">
      <span class="tabular-nums" aria-live="polite">第 {{ data.page }} / {{ pages }} 页</span>
      <span class="hidden items-center gap-1.5 sm:inline-flex"><kbd>←</kbd> 上一页 <span class="mx-1">·</span><kbd>→</kbd> 下一页</span>
    </div>

    <div v-if="data" class="mt-4 overflow-x-auto rounded-xl border border-line bg-surface">
      <table class="w-full min-w-[720px] border-collapse text-left">
        <thead class="text-[13px] text-muted">
          <tr class="border-b border-line">
            <th class="w-12 px-3 py-2.5 font-medium">#</th>
            <th class="px-3 py-2.5 font-semibold text-accent">原文<span class="ml-1 font-normal text-muted">{{ corpus?.versions.find((v) => v.kind === 'source')?.label }}</span></th>
            <th v-for="v in visible" :key="v.id" class="px-3 py-2.5 font-medium text-ink-2">{{ v.label }}</th>
          </tr>
        </thead>
        <tbody v-if="mode === 'sent'">
          <tr v-for="g in data.groups" :id="`g${g.id}`" :key="g.id"
              class="group/row cursor-pointer border-b border-line align-top last:border-0 hover:bg-surface-2/60"
              :class="[g.id === around && 'bg-accent-soft shadow-[inset_2px_0_0_var(--accent)]', g.seq === 0 && 'border-t-2 border-t-line-strong']"
              @click="router.push({ name: 'group', params: { id: g.id } })">
            <td class="px-3 py-3 text-xs text-muted tabular-nums">
              <span v-if="g.seq === 0" class="font-semibold text-ink-2" :title="`第 ${g.paragraph_seq + 1} 段`">¶{{ g.paragraph_seq + 1 }}</span>
              <span v-else>{{ g.seq + 1 }}</span>
            </td>
            <td class="corpus-text px-3 py-3 text-[15.5px]">{{ g.source }}</td>
            <td v-for="v in visible" :key="v.id" class="px-3 py-3">
              <div v-for="s in textOf(g, v.id)" :key="s.id" class="corpus-text text-[15.5px]">
                {{ s.target }}
                <AnnotationPills v-if="showAnn" :values="s.annotations" :ai="s.ai" class="mt-1 mb-1 text-xs" />
              </div>
            </td>
          </tr>
        </tbody>
        <tbody v-else>
          <tr v-for="p in paragraphs" :key="p.id" class="cursor-pointer border-b border-line align-top last:border-0 hover:bg-surface-2/60"
              @click="router.push({ name: 'group', params: { id: p.first } })">
            <td class="px-3 py-3 text-xs font-semibold text-ink-2 tabular-nums">¶{{ p.seq + 1 }}</td>
            <td class="corpus-text px-3 py-3 text-[15.5px]">{{ p.source }}</td>
            <td v-for="v in visible" :key="v.id" class="corpus-text px-3 py-3 text-[15.5px]">{{ p.targets[v.id] }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Pager v-if="data" class="mt-6" :page="data.page" :total="data.total" :size="data.size" @go="go" />
  </div>
</template>
