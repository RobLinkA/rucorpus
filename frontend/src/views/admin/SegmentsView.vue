<script setup lang="ts">
import { PencilLine, Scissors, Search, Tags } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { AiInfo, Paged } from '@/api/types'
import AnnotationEditor from '@/components/AnnotationEditor.vue'
import AnnotationPills from '@/components/AnnotationPills.vue'
import Modal from '@/components/ui/Modal.vue'
import Pager from '@/components/ui/Pager.vue'
import { useMeta } from '@/stores/meta'
import { useToast } from '@/stores/toast'

interface Row { id: number; group_id: number; work_id: number; version_id: number; paragraph_seq: number; group_seq: number; seq: number
  source: string; target: string; unsplit: boolean; annotations: number[]; ai: Record<number, AiInfo> }

const route = useRoute()
const router = useRouter()
const meta = useMeta()
const toast = useToast()
const data = ref<Paged<Row> | null>(null)
const loading = ref(false)
const selected = ref<Set<number>>(new Set())
const text = ref(String(route.query.q ?? ''))

const f = computed(() => ({
  corpus: Number(route.query.corpus) || meta.corpora.find((c) => c.works.length)?.id || 0,
  work: Number(route.query.work) || undefined,
  version: Number(route.query.version) || undefined,
  q: String(route.query.q ?? ''),
  value: Number(route.query.value) || undefined,
  unannotated: route.query.unannotated === '1',
  unsplit: route.query.unsplit === '1',
  origin: typeof route.query.origin === 'string' ? route.query.origin : '',
  page: Number(route.query.page) || 1,
  size: 50,
}))
const corpus = computed(() => meta.corpusById.get(f.value.corpus))

async function load() {
  if (!f.value.corpus) return
  loading.value = true
  try {
    data.value = await api.get<Paged<Row>>('/manage/segments', f.value)
    selected.value = new Set()
  } catch (e) { toast.error(e) } finally { loading.value = false }
}
watch([() => route.query, () => meta.loaded], load, { immediate: true })

function set(patch: Record<string, string | undefined>) {
  router.push({ query: { ...route.query, page: undefined, ...patch } })
}

// ---- selection & batch
const allOnPage = computed(() => !!data.value?.results.length && data.value.results.every((r) => selected.value.has(r.id)))
function toggleAll() {
  selected.value = allOnPage.value ? new Set() : new Set(data.value?.results.map((r) => r.id))
}
function toggle(id: number) {
  const s = new Set(selected.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  selected.value = s
}
const batchValue = ref<number | ''>('')
async function batch(op: 'add' | 'remove') {
  if (!batchValue.value) return
  try {
    const r = await api.post<{ added: number; removed: number }>('/manage/segments/batch-annotate', {
      segment_ids: [...selected.value], [op]: [batchValue.value] })
    toast.ok(op === 'add' ? `新增 ${r.added} 条标注` : `移除 ${r.removed} 条标注`)
    load(); meta.load(true)
  } catch (e) { toast.error(e) }
}

// ---- annotation editor
const editing = ref<Row | null>(null)
const annOpen = ref(false)
function annotate(r: Row) { editing.value = r; annOpen.value = true }

// ---- text edit
const textEdit = ref<{ row: Row; source: string; target: string } | null>(null)
async function saveText() {
  const t = textEdit.value!
  try {
    await api.put(`/manage/segments/${t.row.id}`, { source: t.source, target: t.target })
    t.row.source = t.source; t.row.target = t.target
    textEdit.value = null
    toast.ok('已保存')
  } catch (e) { toast.error(e) }
}

// ---- split
const splitting = ref<{ row: Row; src: string; tgt: string } | null>(null)
const splitSrc = (s: string) => s.split(/(?<=[.!?…»])\s+(?=[«"А-ЯЁA-Z—–-])/u).join('\n')
const splitTgt = (s: string) => s.replace(/([。！？…]+[”」』]?)(?=\S)/gu, '$1\n')
function openSplit(r: Row) { splitting.value = { row: r, src: splitSrc(r.source), tgt: splitTgt(r.target) } }
const splitParts = computed(() => {
  if (!splitting.value) return null
  const a = splitting.value.src.split('\n').map((x) => x.trim()).filter(Boolean)
  const b = splitting.value.tgt.split('\n').map((x) => x.trim()).filter(Boolean)
  return { a, b, ok: a.length === b.length && a.length > 1 }
})
async function doSplit() {
  const p = splitParts.value!
  try {
    await api.post(`/manage/segments/${splitting.value!.row.id}/split`, { parts: p.a.map((s, i) => ({ source: s, target: p.b[i] })) })
    splitting.value = null
    toast.ok(`已拆分为 ${p.a.length} 句`)
    load()
  } catch (e) { toast.error(e) }
}
</script>

<template>
  <div>
    <h1 class="text-2xl font-semibold">句对与标注</h1>

    <div class="card mt-4 flex flex-wrap items-center gap-2 p-3">
      <select class="input w-40" :value="f.corpus" aria-label="语料库" @change="set({ corpus: ($event.target as HTMLSelectElement).value, work: undefined, version: undefined, value: undefined })">
        <option v-for="c in meta.corpora" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
      <select class="input w-40" :value="f.work ?? ''" aria-label="作品" @change="set({ work: ($event.target as HTMLSelectElement).value || undefined })">
        <option value="">全部作品</option>
        <option v-for="w in corpus?.works" :key="w.id" :value="w.id">{{ w.title_target || w.title_source }}</option>
      </select>
      <select class="input w-36" :value="f.version ?? ''" aria-label="译本" @change="set({ version: ($event.target as HTMLSelectElement).value || undefined })">
        <option value="">全部译本</option>
        <option v-for="v in corpus?.versions.filter((x) => x.kind === 'translation')" :key="v.id" :value="v.id">{{ v.label }}</option>
      </select>
      <select class="input w-44" :value="f.value ?? ''" aria-label="标注项" @change="set({ value: ($event.target as HTMLSelectElement).value || undefined })">
        <option value="">任意标注</option>
        <optgroup v-for="g in corpus?.annotation_groups" :key="g.id" :label="g.name">
          <option v-for="v in g.values" :key="v.id" :value="v.id">{{ v.label }}</option>
        </optgroup>
      </select>
      <form class="relative min-w-48 flex-1" @submit.prevent="set({ q: text || undefined })">
        <Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
        <input v-model="text" type="search" class="input pl-9" placeholder="文本或句对ID" />
      </form>
      <label class="flex items-center gap-1.5 text-[13px]"><input type="checkbox" class="accent-[var(--accent)]" :checked="f.unannotated" @change="set({ unannotated: f.unannotated ? undefined : '1' })" />无标注</label>
      <label class="flex items-center gap-1.5 text-[13px]"><input type="checkbox" class="accent-[var(--accent)]" :checked="f.unsplit" @change="set({ unsplit: f.unsplit ? undefined : '1' })" />未切分</label>
      <select class="input w-36" :value="f.origin" aria-label="标注来源" @change="set({ origin: ($event.target as HTMLSelectElement).value || undefined })">
        <option value="">全部来源</option><option value="ai">含 ✦ AI 标注</option><option value="fix">含 AI 更正</option>
      </select>
    </div>

    <div class="mt-3 flex min-h-10 flex-wrap items-center gap-2 text-sm">
      <span class="text-muted">共 {{ data?.total.toLocaleString() ?? '—' }} 条</span>
      <template v-if="selected.size">
        <span class="ml-3 font-medium">已选 {{ selected.size }} 条</span>
        <select v-model="batchValue" class="input h-8 w-52 text-[13px]" aria-label="批量标注项">
          <option value="">选择标注项…</option>
          <optgroup v-for="g in corpus?.annotation_groups" :key="g.id" :label="g.name">
            <option v-for="v in g.values" :key="v.id" :value="v.id">{{ v.label }}</option>
          </optgroup>
        </select>
        <button class="btn-primary btn-sm" :disabled="!batchValue" @click="batch('add')">批量添加</button>
        <button class="btn-outline btn-sm" :disabled="!batchValue" @click="batch('remove')">批量移除</button>
      </template>
    </div>

    <div class="card mt-2 overflow-x-auto" :class="loading && 'opacity-60'">
      <table class="w-full min-w-[900px] text-sm">
        <thead class="border-b border-line text-left text-[13px] text-muted">
          <tr>
            <th class="w-10 px-3 py-2.5"><input type="checkbox" class="accent-[var(--accent)]" :checked="allOnPage" aria-label="全选" @change="toggleAll" /></th>
            <th class="w-28 px-2 py-2.5 font-medium">位置</th>
            <th class="px-2 py-2.5 font-medium">原文</th>
            <th class="px-2 py-2.5 font-medium">译文</th>
            <th class="w-56 px-2 py-2.5 font-medium">标注</th>
            <th class="w-24" />
          </tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="r in data?.results ?? []" :key="r.id" class="group align-top hover:bg-surface-2/40" :class="selected.has(r.id) && 'bg-accent-soft/40'">
            <td class="px-3 py-2.5"><input type="checkbox" class="accent-[var(--accent)]" :checked="selected.has(r.id)" :aria-label="`选择 ${r.id}`" @change="toggle(r.id)" /></td>
            <td class="px-2 py-2.5 text-xs leading-5 text-muted">
              <div class="font-medium text-ink-2">{{ meta.workTitle(r.work_id) }}</div>
              <div class="tabular-nums">¶{{ r.paragraph_seq + 1 }} · 组{{ r.group_seq + 1 }}</div>
              <div>{{ meta.versionById.get(r.version_id)?.label }}</div>
              <RouterLink :to="{ name: 'group', params: { id: r.group_id } }" class="tabular-nums hover:text-accent">#{{ r.id }}</RouterLink>
            </td>
            <td class="px-2 py-2.5 font-display text-[14.5px] leading-relaxed"><span class="line-clamp-4">{{ r.source }}</span></td>
            <td class="px-2 py-2.5 font-display text-[14.5px] leading-relaxed"><span class="line-clamp-4">{{ r.target }}</span>
              <span v-if="r.unsplit" class="tag tag-seal mt-1">未切分整段</span></td>
            <td class="px-2 py-2.5"><AnnotationPills :values="r.annotations" :ai="r.ai" class="text-xs" /></td>
            <td class="px-2 py-2">
              <div class="flex justify-end opacity-60 group-hover:opacity-100">
                <button class="btn-icon size-8" title="编辑标注" @click="annotate(r)"><Tags class="size-4" /></button>
                <button class="btn-icon size-8" title="编辑文本" @click="textEdit = { row: r, source: r.source, target: r.target }"><PencilLine class="size-4" /></button>
                <button class="btn-icon size-8" title="拆分句对" @click="openSplit(r)"><Scissors class="size-4" /></button>
              </div>
            </td>
          </tr>
          <tr v-if="data && !data.results.length"><td colspan="6" class="px-4 py-10 text-center text-muted">没有符合条件的句对</td></tr>
        </tbody>
      </table>
    </div>
    <Pager v-if="data" class="mt-5" :page="f.page" :total="data.total" :size="f.size" @go="(p) => router.push({ query: { ...route.query, page: String(p) } })" />

    <AnnotationEditor v-if="editing" v-model="annOpen" :segment-id="editing.id" :corpus-id="f.corpus" :values="editing.annotations"
                      :context="editing.target" :ai="editing.ai" @saved="(v, ai) => { if (editing) { editing.annotations = v; editing.ai = ai } }" />

    <Modal :model-value="!!textEdit" title="编辑句对文本" width="max-w-3xl" @update:model-value="(o) => !o && (textEdit = null)">
      <form v-if="textEdit" id="tf" class="space-y-3" @submit.prevent="saveText">
        <div><label class="label" for="ts">原文</label><textarea id="ts" v-model="textEdit.source" rows="5" class="input h-auto py-2 font-display" required /></div>
        <div><label class="label" for="tt">译文</label><textarea id="tt" v-model="textEdit.target" rows="5" class="input h-auto py-2 font-display" /></div>
        <p class="text-xs text-muted">修改会记入操作日志，并即时更新检索索引。</p>
      </form>
      <template #footer><button class="btn-ghost" @click="textEdit = null">取消</button><button form="tf" class="btn-primary">保存</button></template>
    </Modal>

    <Modal :model-value="!!splitting" title="拆分句对" width="max-w-5xl" @update:model-value="(o) => !o && (splitting = null)">
      <template v-if="splitting && splitParts">
        <p class="mb-3 text-sm text-ink-2">每行为一句，原文与译文按行一一对应。已按标点自动预切分，请检查调整。</p>
        <div class="grid gap-3 md:grid-cols-2">
          <div><label class="label" for="sa">原文（{{ splitParts.a.length }} 行）</label>
            <textarea id="sa" v-model="splitting.src" rows="14" class="input h-auto py-2 font-display text-[14px] leading-relaxed" /></div>
          <div><label class="label" for="sb">译文（{{ splitParts.b.length }} 行）</label>
            <textarea id="sb" v-model="splitting.tgt" rows="14" class="input h-auto py-2 font-display text-[14px] leading-relaxed" /></div>
        </div>
        <p v-if="!splitParts.ok" class="mt-2 text-sm text-seal">原文与译文行数需相同且至少两行。</p>
      </template>
      <template #footer><button class="btn-ghost" @click="splitting = null">取消</button><button class="btn-primary" :disabled="!splitParts?.ok" @click="doSplit">拆分</button></template>
    </Modal>
  </div>
</template>
