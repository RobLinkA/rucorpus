<script setup lang="ts">
/* 高级检索: query box + a row of filter popovers (scope · versions · annotations).
   Every change updates the URL and the results immediately. The home page is the simple search. */
import { Download, LoaderCircle, Search, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { SearchParams, SearchResponse } from '@/api/types'
import GroupCard from '@/components/GroupCard.vue'
import AnnotationFilter from '@/components/search/AnnotationFilter.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import Pager from '@/components/ui/Pager.vue'
import Popover from '@/components/ui/Popover.vue'
import { fromQuery, hasCondition, toQuery } from '@/composables/searchQuery'
import { useMeta } from '@/stores/meta'

const route = useRoute()
const router = useRouter()
const meta = useMeta()
const params = computed(() => fromQuery(route.query))
const data = ref<SearchResponse | null>(null)
const loading = ref(false)
const error = ref('')
const elapsed = ref(0)
const q = ref('')
const onlyHits = ref(false)
let seq = 0

watch(() => route.query, async () => {
  q.value = params.value.q
  if (!hasCondition(params.value)) { data.value = null; error.value = ''; return }
  const my = ++seq
  loading.value = true
  error.value = ''
  try {
    const t0 = performance.now()
    const r = await api.get<SearchResponse>('/search', { ...params.value })
    if (my === seq) { data.value = r; elapsed.value = Math.round(performance.now() - t0) }
  } catch (e) {
    if (my === seq) { error.value = e instanceof Error ? e.message : String(e); data.value = null }
  } finally {
    if (my === seq) loading.value = false
  }
}, { immediate: true })

function update(patch: Partial<SearchParams>, keepPage = false) {
  router.push({ query: toQuery({ ...params.value, ...patch, page: keepPage ? patch.page : 1 }) })
}
function go(page: number) {
  update({ page }, true)
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

// ---- facets → lookup maps
const facet = (k: 'corpora' | 'works' | 'versions' | 'values') =>
  data.value ? new Map(data.value.facets[k].map((f) => [f.id, f.count])) : undefined
const corpora = computed(() => meta.corpora.filter((c) => c.works.length))
const scoped = computed(() => corpora.value.filter((c) => !params.value.corpora.length || params.value.corpora.includes(c.id)))

// ---- scope (corpus + works) and versions
function toggleCorpus(id: number) {
  const p = params.value
  const c = meta.corpusById.get(id)!
  if (p.corpora.includes(id)) {
    const without = (ids: number[], pool: number[]) => ids.filter((x) => !pool.includes(x))
    const vals = c.annotation_groups.flatMap((g) => g.values.map((v) => v.id))
    update({
      corpora: p.corpora.filter((x) => x !== id),
      works: without(p.works, c.works.map((w) => w.id)),
      versions: without(p.versions, c.versions.map((v) => v.id)),
      values: without(p.values, vals), exclude: without(p.exclude, vals),
    })
  } else update({ corpora: [...p.corpora, id] })
}
function toggleIn(key: 'works' | 'versions', cid: number, id: number) {
  const p = params.value
  update({
    [key]: p[key].includes(id) ? p[key].filter((x) => x !== id) : [...p[key], id],
    corpora: p.corpora.includes(cid) ? p.corpora : [...p.corpora, cid],
  })
}

const scopeLabel = computed(() => {
  const p = params.value
  if (p.works.length) return p.works.length === 1 ? meta.workTitle(p.works[0]) : `${p.works.length} 部作品`
  return p.corpora.map((id) => meta.corpusById.get(id)?.name).join('、')
})
const versionLabel = computed(() => {
  const v = params.value.versions
  return v.length === 1 ? meta.versionById.get(v[0])?.label : v.length ? `${v.length} 个` : ''
})
const annLabel = computed(() => {
  const p = params.value
  return [p.values.length && `${p.values.length} 项`, p.exclude.length && `排除 ${p.exclude.length}`,
    p.origin !== 'all' && (p.origin === 'ai' ? '仅 AI' : '仅人工')].filter(Boolean).join(' · ')
})

// ---- active condition chips
const chips = computed(() => {
  const p = params.value
  const out: { label: string; patch: Partial<SearchParams>; exclude?: boolean }[] = []
  p.works.forEach((id) => out.push({ label: meta.workTitle(id), patch: { works: p.works.filter((x) => x !== id) } }))
  if (!p.works.length) p.corpora.forEach((id) => out.push({ label: meta.corpusById.get(id)?.name ?? '', patch: { corpora: p.corpora.filter((x) => x !== id) } }))
  p.versions.forEach((id) => out.push({ label: meta.versionById.get(id)?.label ?? '', patch: { versions: p.versions.filter((x) => x !== id) } }))
  p.values.forEach((id) => out.push({ label: meta.valueById.get(id)?.label ?? '', patch: { values: p.values.filter((x) => x !== id) } }))
  p.exclude.forEach((id) => out.push({ label: meta.valueById.get(id)?.label ?? '', exclude: true, patch: { exclude: p.exclude.filter((x) => x !== id) } }))
  if (p.origin !== 'all') out.push({ label: p.origin === 'ai' ? '仅 ✦ AI 标注' : '仅人工标注', patch: { origin: 'all' } })
  return out
})
const clearAll = () => update({ corpora: [], works: [], versions: [], values: [], exclude: [], origin: 'all', logic: 'group' })
const exportHref = (format: string) => api.href('/search/export', { ...params.value, page: undefined, size: undefined, format })

// Suggestions use this installation's metadata, never fixed corpus IDs.
const starters = computed(() => meta.corpora.filter((c) => c.works.length).slice(0, 4).map((c) => ({
  t: c.name, d: '浏览本语料库', query: toQuery({ corpora: [c.id] }),
})))
</script>

<template>
  <div class="mx-auto max-w-[1080px] px-4 py-7 sm:px-6">
    <h1 class="mb-4 font-display text-[1.6rem] font-semibold">高级检索</h1>
    <form class="flex gap-2" role="search" @submit.prevent="update({ q: q.trim() })">
      <div class="flex flex-1 items-center rounded-xl border border-line-strong bg-surface shadow-card transition focus-within:border-accent focus-within:shadow-glow">
        <Search class="ml-3.5 size-[18px] shrink-0 text-muted" />
        <input v-model="q" type="search" class="h-11 min-w-0 flex-1 bg-transparent px-3 font-serif focus-visible:outline-none text-[16px] outline-none placeholder:font-sans placeholder:text-[14px] placeholder:text-muted"
               placeholder="检索词（可留空，只用下方条件筛选）" aria-label="检索词" />
        <div class="mr-1.5 hidden shrink-0 rounded-lg bg-surface-2 p-0.5 text-[12.5px] sm:flex" role="radiogroup" aria-label="匹配方式">
          <button v-for="m in [{ v: 'morph', l: '模糊匹配' }, { v: 'exact', l: '精确匹配' }] as const" :key="m.v" type="button" role="radio"
                  :aria-checked="params.mode === m.v" :title="m.v === 'morph' ? '匹配俄语单词的不同变化形式；其他语言按词形匹配' : '只匹配输入的词形'"
                  class="rounded-md px-2.5 py-1" :class="params.mode === m.v ? 'bg-surface text-ink shadow-card font-medium' : 'text-muted'"
                  @click="update({ mode: m.v })">{{ m.l }}</button>
        </div>
      </div>
      <button class="btn-primary h-11 px-5">检索</button>
    </form>

    <div class="mt-3 flex flex-wrap items-center gap-2">
      <Popover label="范围" :value="scopeLabel" :active="!!scopeLabel" width="w-[22rem]">
        <div class="max-h-[60vh] space-y-3 overflow-y-auto p-3">
          <div v-for="c in corpora" :key="c.id">
            <label class="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 hover:bg-surface-2">
              <input type="checkbox" :checked="params.corpora.includes(c.id)" @change="toggleCorpus(c.id)" />
              <span class="flex-1 text-[14px] font-medium">{{ c.name }}</span>
              <span class="text-[12px] text-muted tabular-nums">{{ facet('corpora')?.get(c.id) ?? '' }}</span>
            </label>
            <div class="mt-1.5 flex flex-wrap gap-1.5 pl-8">
              <button v-for="w in c.works" :key="w.id" type="button" class="chip h-7 text-[12.5px]" :class="params.works.includes(w.id) && 'chip-on'"
                      @click="toggleIn('works', c.id, w.id)">{{ w.title_target || w.title_source }}</button>
            </div>
          </div>
          <p class="px-2 text-[11.5px] text-muted">不选即检索全部；点作品即限定到所选作品。</p>
        </div>
      </Popover>

      <Popover label="译本" :value="versionLabel" :active="!!versionLabel" width="w-72">
        <div class="max-h-[60vh] overflow-y-auto p-2">
          <template v-for="c in scoped" :key="c.id">
            <div v-if="scoped.length > 1" class="px-2.5 pt-2 pb-1 text-[12px] text-muted">{{ c.name }}</div>
            <label v-for="v in c.versions.filter((x) => x.kind === 'translation')" :key="v.id"
                   class="flex cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-1.5 text-[13.5px] hover:bg-surface-2">
              <input type="checkbox" :checked="params.versions.includes(v.id)" @change="toggleIn('versions', c.id, v.id)" />
              <span class="flex-1">{{ v.label }}</span>
              <span class="text-[12px] text-muted tabular-nums">{{ facet('versions')?.get(v.id) ?? '' }}</span>
            </label>
          </template>
          <p class="px-2.5 pt-1 text-[11.5px] text-muted">不选即全部译本</p>
        </div>
      </Popover>

      <Popover label="标注" :value="annLabel" :active="!!annLabel" width="w-[24rem]">
        <AnnotationFilter :params="params" :corpora="scoped" :counts="facet('values')" @change="update" />
      </Popover>

      <button v-if="chips.length" type="button" class="ml-1 text-[13px] text-muted hover:text-accent" @click="clearAll">清除筛选</button>
    </div>

    <div v-if="chips.length" class="mt-2.5 flex flex-wrap items-center gap-1.5">
      <button v-for="(c, i) in chips" :key="i" type="button" :title="`移除：${c.label}`" @click="update(c.patch)"
              class="inline-flex h-7 items-center gap-1 rounded-full px-2.5 text-[12.5px]"
              :class="c.exclude ? 'bg-seal-soft text-seal' : 'bg-accent-soft text-accent'">
        <span v-if="c.exclude">排除</span><span :class="c.exclude && 'line-through'">{{ c.label }}</span><X class="size-3.5 opacity-70" />
      </button>
      <span v-if="params.values.length > 1" class="text-[12px] text-muted">
        {{ { group: '· 每组至少一项', or: '· 满足任一项', and: '· 全部满足' }[params.logic] }}
      </span>
    </div>

    <div v-if="data" class="mt-6 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-line pb-3">
      <p class="text-[14px] text-ink-2" aria-live="polite">
        <b class="text-ink tabular-nums">{{ data.total.toLocaleString() }}</b> 个句组
        <span class="text-[12.5px] text-muted">· {{ data.total_segments.toLocaleString() }} 个译文句对 · {{ elapsed }} ms</span>
      </p>
      <LoaderCircle v-if="loading" class="size-4 animate-spin text-muted" />
      <div class="ml-auto flex items-center gap-1.5">
        <Popover label="显示" width="w-56" align="right">
          <div class="space-y-3 p-3 text-[13px]">
            <label class="flex cursor-pointer items-center gap-2"><input v-model="onlyHits" type="checkbox" />只显示命中的译本</label>
            <label class="flex items-center gap-2">每页
              <select class="input h-8 w-auto" :value="params.size" @change="update({ size: Number(($event.target as HTMLSelectElement).value) })">
                <option v-for="n in [10, 20, 50, 100]" :key="n" :value="n">{{ n }}</option>
              </select>条
            </label>
          </div>
        </Popover>
        <Dropdown v-if="data.total" align="right" width="w-40">
          <template #trigger><button class="btn-ghost btn-sm"><Download class="size-4" />导出</button></template>
          <a :href="exportHref('xlsx')" class="menu-item">Excel</a>
          <a :href="exportHref('csv')" class="menu-item">CSV</a>
        </Dropdown>
      </div>
    </div>

    <div v-if="error" class="card mt-6 px-5 py-4 text-sm text-seal">{{ error }}</div>

    <div v-else-if="!hasCondition(params)" class="mt-8">
      <p class="text-[13.5px] text-ink-2">输入检索词，或用上方“范围 · 译本 · 标注”组合筛选。也可以选择下方语料库：</p>
      <div class="mt-4 grid gap-3 sm:grid-cols-2">
        <RouterLink v-for="s in starters" :key="s.t" :to="{ name: 'search', query: s.query }" class="card card-hover px-5 py-4">
          <div class="font-display text-[16px] font-semibold">{{ s.t }}</div>
          <div class="mt-0.5 text-[12.5px] text-muted">{{ s.d }}</div>
        </RouterLink>
      </div>
      <p class="mt-6 text-[13px] text-muted">
        检索语法：<span class="font-serif text-ink-2">человек</span> 模糊匹配（含不同变化形式） · <span class="font-serif text-ink-2">"на шее"</span> 短语 ·
        <span class="font-serif text-ink-2">чинов*</span> 前缀 · 中文直接输入 ·
        <RouterLink to="/help" class="text-accent hover:underline">更多说明</RouterLink>
      </p>
    </div>

    <div v-else-if="data && !data.total && !loading" class="mt-12 text-center text-[14px]">
      <p class="text-[16px]">没有找到匹配的句组</p>
      <p class="mt-2 text-muted">试试模糊匹配、减少关键词，或放宽筛选条件</p>
    </div>

    <div v-if="data?.results.length" class="mt-5 space-y-4" :class="loading && 'opacity-60 transition-opacity'">
      <GroupCard v-for="g in data.results" :key="g.id" :group="g" :active-values="params.values" :only-hits="onlyHits" />
    </div>
    <div v-else-if="loading" class="mt-5 space-y-4">
      <div v-for="i in 3" :key="i" class="card h-40 animate-pulse bg-surface-2/60" />
    </div>

    <Pager v-if="data" class="mt-8" :page="params.page" :total="data.total" :size="params.size" @go="go" />
  </div>
</template>
