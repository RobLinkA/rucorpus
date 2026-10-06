<script setup lang="ts">
import { Download, NotebookPen, Search, Star } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Group, Paged } from '@/api/types'
import GroupCard from '@/components/GroupCard.vue'
import Dropdown from '@/components/ui/Dropdown.vue'
import Pager from '@/components/ui/Pager.vue'
import { useMeta } from '@/stores/meta'
import { useToast } from '@/stores/toast'

interface Fav { id: number; note: string; created_at: string; group: Group }

const route = useRoute()
const router = useRouter()
const meta = useMeta()
const toast = useToast()
const data = ref<Paged<Fav> | null>(null)
const loading = ref(false)
const text = ref(String(route.query.q ?? ''))
const editingNote = ref<number | null>(null)
const draft = ref('')

const filters = computed(() => ({
  corpus: Number(route.query.corpus) || undefined,
  work: Number(route.query.work) || undefined,
  values: ([] as string[]).concat((route.query.values as string[] | string) ?? []).map(Number).filter(Boolean),
  q: String(route.query.q ?? ''),
  page: Number(route.query.page) || 1,
  size: 20,
}))
const corpus = computed(() => (filters.value.corpus ? meta.corpusById.get(filters.value.corpus) : undefined))

async function load() {
  loading.value = true
  try { data.value = await api.get<Paged<Fav>>('/me/favorites', filters.value) } catch (e) { toast.error(e) } finally { loading.value = false }
}
watch(() => route.query, load, { immediate: true })

function set(patch: Record<string, unknown>) {
  const q: Record<string, unknown> = { ...route.query, page: undefined, ...patch }
  for (const k of Object.keys(q)) if (q[k] === '' || q[k] == null || (Array.isArray(q[k]) && !(q[k] as unknown[]).length)) delete q[k]
  router.push({ query: q as Record<string, string> })
}
function toggleValue(id: number) {
  const v = filters.value.values
  set({ values: (v.includes(id) ? v.filter((x) => x !== id) : [...v, id]).map(String) })
}

function editNote(f: Fav) { editingNote.value = f.id; draft.value = f.note }
async function saveNote(f: Fav) {
  try {
    await api.put(`/me/favorites/by-group/${f.group.id}`, { note: draft.value })
    f.note = draft.value
    editingNote.value = null
    toast.ok('笔记已保存')
  } catch (e) { toast.error(e) }
}
function removed(f: Fav) {
  if (!f.group.favorite && data.value) {
    data.value.results = data.value.results.filter((x) => x.id !== f.id)
    data.value.total -= 1
  }
}
const exportHref = (format: string) => api.href('/me/favorites/export', { ...filters.value, page: undefined, size: undefined, format })
</script>

<template>
  <div class="mx-auto max-w-5xl px-4 py-8 sm:px-6">
    <div class="flex flex-wrap items-end gap-3">
      <div>
        <h1 class="font-display text-3xl font-semibold">我的收藏</h1>
        <p class="mt-1 text-sm text-muted">共 {{ data?.total ?? '—' }} 个句组 · 可添加笔记、按标注筛选、导出为 Excel</p>
      </div>
      <Dropdown v-if="data?.total" align="right" width="w-44" class="ml-auto">
        <template #trigger><button class="btn-outline"><Download class="size-4" />导出</button></template>
        <a :href="exportHref('xlsx')" class="menu-item">Excel（.xlsx）</a>
        <a :href="exportHref('csv')" class="menu-item">CSV（UTF-8）</a>
      </Dropdown>
    </div>

    <div class="card mt-6 space-y-3 p-4">
      <div class="flex flex-wrap gap-2">
        <form class="relative min-w-52 flex-1" @submit.prevent="set({ q: text })">
          <Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
          <input v-model="text" type="search" class="input pl-9" placeholder="在收藏的原文、译文和笔记中查找" />
        </form>
        <select class="input w-44" :value="filters.corpus ?? ''" aria-label="语料库" @change="set({ corpus: ($event.target as HTMLSelectElement).value, work: undefined, values: [] })">
          <option value="">全部语料库</option>
          <option v-for="c in meta.corpora.filter((x) => x.works.length)" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select v-if="corpus" class="input w-44" :value="filters.work ?? ''" aria-label="作品" @change="set({ work: ($event.target as HTMLSelectElement).value })">
          <option value="">全部作品</option>
          <option v-for="w in corpus.works" :key="w.id" :value="w.id">{{ w.title_target || w.title_source }}</option>
        </select>
      </div>
      <div v-if="corpus" class="space-y-1.5">
        <div v-for="g in corpus.annotation_groups" :key="g.id" class="flex flex-wrap items-center gap-1.5">
          <span class="w-24 shrink-0 text-[13px] text-muted">{{ g.name }}</span>
          <button v-for="v in g.values" :key="v.id" class="chip h-6.5 text-xs" :class="filters.values.includes(v.id) && 'chip-on'" @click="toggleValue(v.id)">{{ v.label }}</button>
        </div>
      </div>
      <p v-else class="text-xs text-muted">选择语料库后可按标注筛选（同时满足所选标注）。</p>
    </div>

    <div v-if="data && !data.total && !loading" class="card mt-6 px-6 py-12 text-center">
      <Star class="mx-auto size-8 text-muted" />
      <p class="mt-3 text-ink-2">{{ filters.q || filters.corpus ? '没有符合条件的收藏' : '还没有收藏。在检索结果或句组详情中点击星标即可收藏。' }}</p>
    </div>

    <div class="mt-5 space-y-5">
      <div v-for="f in data?.results ?? []" :key="f.id">
        <GroupCard v-if="f.group" :group="f.group" :active-values="filters.values" />
        <div class="mt-1.5 flex items-start gap-2 px-1 text-sm">
          <NotebookPen class="mt-0.5 size-4 shrink-0 text-muted" />
          <template v-if="editingNote === f.id">
            <div class="flex-1">
              <textarea v-model="draft" rows="3" class="input h-auto py-2" placeholder="笔记…" />
              <div class="mt-1.5 flex gap-2">
                <button class="btn-primary btn-sm" @click="saveNote(f)">保存</button>
                <button class="btn-ghost btn-sm" @click="editingNote = null">取消</button>
              </div>
            </div>
          </template>
          <button v-else class="flex-1 text-left whitespace-pre-wrap" :class="f.note ? 'text-ink-2' : 'text-muted hover:text-accent'" @click="editNote(f)">
            {{ f.note || '添加笔记' }}
          </button>
          <span class="shrink-0 text-xs text-muted">{{ new Date(f.created_at).toLocaleDateString('zh-CN') }}</span>
          <button v-if="f.group && !f.group.favorite" class="shrink-0 text-xs text-accent hover:underline" @click="removed(f)">从列表移除</button>
        </div>
      </div>
    </div>
    <Pager v-if="data" class="mt-8" :page="filters.page" :total="data.total" :size="filters.size" @go="(p) => router.push({ query: { ...route.query, page: String(p) } })" />
  </div>
</template>
