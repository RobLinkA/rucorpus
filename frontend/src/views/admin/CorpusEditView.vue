<script setup lang="ts">
import { ArrowDown, ArrowUp, Combine, Pencil, Plus, Trash2 } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'
import Modal from '@/components/ui/Modal.vue'
import { useMeta } from '@/stores/meta'
import { useToast } from '@/stores/toast'

interface Corpus { id: number; name: string; description: string; source_lang: string; target_lang: string; status: string; sort_order: number }
interface Version { id: number; kind: string; lang: string; label: string; person: string; bibliography: string; sort_order: number; segments: number }
interface Work { id: number; title_source: string; title_target: string; author: string; sort_order: number; paragraphs: number; groups: number; segments: number }
interface Value { id: number; label: string; sort_order: number; usage: number; defined_in_legacy: boolean }
interface Group { id: number; name: string; key: string; description: string; widget: string; sort_order: number; values: Value[] }

const route = useRoute()
const toast = useToast()
const meta = useMeta()
const id = computed(() => Number(route.params.id))
const tab = ref<'info' | 'versions' | 'works' | 'scheme'>((route.query.tab as 'info') || 'scheme')
const corpus = ref<Corpus | null>(null)
const versions = ref<Version[]>([])
const works = ref<Work[]>([])
const groups = ref<Group[]>([])

async function load() {
  const all = await api.get<Corpus[]>('/manage/corpora')
  corpus.value = all.find((c) => c.id === id.value) ?? null
  versions.value = await api.get<Version[]>(`/manage/corpora/${id.value}/versions`)
  works.value = await api.get<Work[]>(`/manage/corpora/${id.value}/works`)
  groups.value = await api.get<Group[]>(`/manage/corpora/${id.value}/annotation-groups`)
}
onMounted(load)
async function run(fn: () => Promise<unknown>, msg = '已保存') {
  try { await fn(); toast.ok(msg); await load(); meta.load(true) } catch (e) { toast.error(e) }
}

// ---- info
const saveInfo = () => corpus.value && run(() => api.put(`/manage/corpora/${id.value}`, corpus.value))

// ---- versions
const vForm = ref<Partial<Version> | null>(null)
const saveVersion = () => run(async () => {
  const v = vForm.value!
  const body = { kind: v.kind, lang: v.lang, label: v.label, person: v.person ?? '', bibliography: v.bibliography ?? '', sort_order: v.sort_order ?? 0 }
  if (v.id) await api.put(`/manage/versions/${v.id}`, body)
  else await api.post(`/manage/corpora/${id.value}/versions`, body)
  vForm.value = null
})
function delVersion(v: Version) {
  if (confirm(`删除版本“${v.label}”及其 ${v.segments} 个句对？不可恢复。`)) run(() => api.del(`/manage/versions/${v.id}`), '已删除')
}

// ---- works
const wForm = ref<Partial<Work> | null>(null)
const saveWork = () => run(async () => {
  const w = wForm.value!
  const body = { title_source: w.title_source, title_target: w.title_target ?? '', author: w.author ?? '', sort_order: w.sort_order ?? works.value.length }
  if (w.id) await api.put(`/manage/works/${w.id}`, body)
  else await api.post(`/manage/corpora/${id.value}/works`, body)
  wForm.value = null
})
function delWork(w: Work) {
  if (confirm(`删除作品“${w.title_source}”及其 ${w.segments} 个句对？不可恢复。`)) run(() => api.del(`/manage/works/${w.id}`), '已删除')
}
function moveWork(i: number, d: number) {
  const ids = works.value.map((w) => w.id)
  ;[ids[i], ids[i + d]] = [ids[i + d], ids[i]]
  run(() => api.post('/manage/works/reorder', { ids }), '已调整顺序')
}

// ---- annotation scheme
const gForm = ref<Partial<Group> | null>(null)
const valForm = ref<{ group: Group; value?: Value; label: string } | null>(null)
const merging = ref<{ value: Value; into: number | null } | null>(null)
const allValues = computed(() => groups.value.flatMap((g) => g.values.map((v) => ({ ...v, group: g.name }))))
const saveGroup = () => run(async () => {
  const g = gForm.value!
  const body = { name: g.name, key: g.key ?? '', description: g.description ?? '', widget: g.widget ?? 'checkbox' }
  if (g.id) await api.put(`/manage/annotation-groups/${g.id}`, body)
  else await api.post(`/manage/corpora/${id.value}/annotation-groups`, body)
  gForm.value = null
})
function delGroup(g: Group) {
  const n = g.values.reduce((a, v) => a + v.usage, 0)
  if (confirm(`删除标注组“${g.name}”？其下 ${g.values.length} 个标注项及 ${n} 条标注将一并删除。`))
    run(() => api.del(`/manage/annotation-groups/${g.id}`), '已删除')
}
const saveValue = () => run(async () => {
  const f = valForm.value!
  if (f.value) await api.put(`/manage/annotation-values/${f.value.id}`, { label: f.label })
  else await api.post(`/manage/annotation-groups/${f.group.id}/values`, { label: f.label })
  valForm.value = null
})
function delValue(v: Value) {
  if (confirm(`删除标注项“${v.label}”？${v.usage ? `已有 ${v.usage} 条标注将被删除。` : ''}`))
    run(() => api.del(`/manage/annotation-values/${v.id}`), '已删除')
}
const doMerge = () => merging.value?.into && run(async () => {
  const r = await api.post<{ moved: number }>(`/manage/annotation-values/${merging.value!.value.id}/merge`, { into: merging.value!.into })
  merging.value = null
  toast.info(`已迁移 ${r.moved} 条标注`)
}, '已合并')
function moveGroup(i: number, d: number) {
  const ids = groups.value.map((g) => g.id)
  ;[ids[i], ids[i + d]] = [ids[i + d], ids[i]]
  run(() => api.post('/manage/annotation-groups/reorder', { ids }), '已调整顺序')
}
function moveValue(g: Group, i: number, d: number) {
  const ids = g.values.map((v) => v.id)
  ;[ids[i], ids[i + d]] = [ids[i + d], ids[i]]
  run(() => api.post('/manage/annotation-values/reorder', { ids }), '已调整顺序')
}
const WIDGET: Record<string, string> = { checkbox: '复选（多选）', multiselect: '下拉多选', radio: '单选', select: '下拉单选' }
</script>

<template>
  <div v-if="corpus">
    <RouterLink to="/admin/corpora" class="text-[13px] muted-link">← 语料库</RouterLink>
    <h1 class="mt-1 text-2xl font-semibold">{{ corpus.name }}</h1>

    <div class="mt-4 flex gap-1 border-b border-line" role="tablist">
      <button v-for="t in [{ k: 'scheme', l: '标注体系' }, { k: 'works', l: '作品' }, { k: 'versions', l: '版本' }, { k: 'info', l: '基本信息' }] as const"
              :key="t.k" role="tab" :aria-selected="tab === t.k" class="-mb-px border-b-2 px-3 py-2 text-sm transition"
              :class="tab === t.k ? 'border-accent font-medium text-accent' : 'border-transparent text-ink-2 hover:text-ink'"
              @click="tab = t.k">{{ t.l }}</button>
    </div>

    <!-- 基本信息 -->
    <form v-if="tab === 'info'" class="card mt-5 max-w-2xl space-y-3 p-5" @submit.prevent="saveInfo">
      <div><label class="label" for="n">名称</label><input id="n" v-model="corpus.name" class="input" required /></div>
      <div><label class="label" for="d">说明</label><textarea id="d" v-model="corpus.description" rows="3" class="input h-auto py-2" /></div>
      <div class="grid grid-cols-3 gap-3">
        <div><label class="label" for="s">原文语言（ru/en/fr/es/zh 等）</label><input id="s" v-model="corpus.source_lang" class="input" /></div>
        <div><label class="label" for="t">译文语言（ru/en/fr/es/zh 等）</label><input id="t" v-model="corpus.target_lang" class="input" /></div>
        <div><label class="label" for="o">排序</label><input id="o" v-model.number="corpus.sort_order" type="number" class="input" /></div>
      </div>
      <div><label class="label" for="st">状态</label>
        <select id="st" v-model="corpus.status" class="input w-40"><option value="published">已发布</option><option value="hidden">已下架</option></select></div>
      <button class="btn-primary">保存</button>
    </form>

    <!-- 版本 -->
    <section v-if="tab === 'versions'" class="mt-5">
      <button class="btn-primary" @click="vForm = { kind: 'translation', lang: corpus.target_lang, label: '', sort_order: versions.length }"><Plus class="size-4" />添加版本</button>
      <div class="card mt-4 divide-y divide-line">
        <div v-for="v in versions" :key="v.id" class="flex items-start gap-3 px-4 py-3 text-sm">
          <span class="tag mt-0.5" :class="v.kind === 'source' && 'tag-seal'">{{ v.kind === 'source' ? '原文' : '译文' }}</span>
          <div class="min-w-0 flex-1">
            <div class="font-medium">{{ v.label }} <span class="font-normal text-muted">{{ v.person }} · {{ v.lang }}</span></div>
            <div class="truncate text-xs text-muted">{{ v.bibliography || '—' }}</div>
          </div>
          <span class="text-xs text-muted tabular-nums">{{ v.segments.toLocaleString() }} 句对</span>
          <button class="btn-icon size-8" title="编辑" @click="vForm = { ...v }"><Pencil class="size-4" /></button>
          <button class="btn-icon size-8 hover:text-seal" title="删除" @click="delVersion(v)"><Trash2 class="size-4" /></button>
        </div>
      </div>
    </section>

    <!-- 作品 -->
    <section v-if="tab === 'works'" class="mt-5">
      <button class="btn-primary" @click="wForm = { title_source: '', title_target: '', author: '' }"><Plus class="size-4" />添加作品</button>
      <p class="mt-2 text-xs text-muted">作品正文请通过“导入导出”上传；这里维护标题、作者与顺序。</p>
      <div class="card mt-4 divide-y divide-line">
        <div v-for="(w, i) in works" :key="w.id" class="flex items-center gap-3 px-4 py-2.5 text-sm">
          <div class="flex flex-col">
            <button class="text-muted hover:text-ink disabled:opacity-30" :disabled="i === 0" aria-label="上移" @click="moveWork(i, -1)"><ArrowUp class="size-3.5" /></button>
            <button class="text-muted hover:text-ink disabled:opacity-30" :disabled="i === works.length - 1" aria-label="下移" @click="moveWork(i, 1)"><ArrowDown class="size-3.5" /></button>
          </div>
          <div class="min-w-0 flex-1">
            <div class="font-medium">{{ w.title_target || w.title_source }} <span class="font-display font-normal text-muted">{{ w.title_source }}</span></div>
            <div class="text-xs text-muted">{{ w.author }}</div>
          </div>
          <span class="text-xs text-muted tabular-nums">{{ w.paragraphs }} 段 · {{ w.groups.toLocaleString() }} 句组 · {{ w.segments.toLocaleString() }} 句对</span>
          <RouterLink :to="{ name: 'read', params: { workId: w.id } }" class="btn-ghost btn-sm">阅读</RouterLink>
          <button class="btn-icon size-8" title="编辑" @click="wForm = { ...w }"><Pencil class="size-4" /></button>
          <button class="btn-icon size-8 hover:text-seal" title="删除" @click="delWork(w)"><Trash2 class="size-4" /></button>
        </div>
        <p v-if="!works.length" class="px-4 py-8 text-center text-sm text-muted">暂无作品</p>
      </div>
    </section>

    <!-- 标注体系 -->
    <section v-if="tab === 'scheme'" class="mt-5">
      <div class="flex flex-wrap items-center gap-3">
        <button class="btn-primary" @click="gForm = { name: '', widget: 'checkbox' }"><Plus class="size-4" />新建标注组</button>
        <p class="text-xs text-muted">两层结构：标注组 → 标注项。标注组属于本语料库，与其他语料库互不共用。</p>
      </div>
      <div class="mt-4 space-y-4">
        <article v-for="(g, gi) in groups" :key="g.id" class="card">
          <header class="flex items-center gap-2 border-b border-line px-4 py-2.5">
            <div class="flex flex-col">
              <button class="text-muted hover:text-ink disabled:opacity-30" :disabled="gi === 0" aria-label="上移" @click="moveGroup(gi, -1)"><ArrowUp class="size-3.5" /></button>
              <button class="text-muted hover:text-ink disabled:opacity-30" :disabled="gi === groups.length - 1" aria-label="下移" @click="moveGroup(gi, 1)"><ArrowDown class="size-3.5" /></button>
            </div>
            <h2 class="font-semibold">{{ g.name }}</h2>
            <span class="text-xs text-muted">{{ WIDGET[g.widget] }}<template v-if="g.key"> · {{ g.key }}</template></span>
            <div class="ml-auto flex">
              <button class="btn-ghost btn-sm" @click="valForm = { group: g, label: '' }"><Plus class="size-4" />标注项</button>
              <button class="btn-icon size-8" title="编辑标注组" @click="gForm = { ...g }"><Pencil class="size-4" /></button>
              <button class="btn-icon size-8 hover:text-seal" title="删除标注组" @click="delGroup(g)"><Trash2 class="size-4" /></button>
            </div>
          </header>
          <ul class="divide-y divide-line">
            <li v-for="(v, vi) in g.values" :key="v.id" class="group flex items-center gap-3 px-4 py-2 text-sm">
              <div class="flex flex-col opacity-40 group-hover:opacity-100">
                <button class="text-muted hover:text-ink disabled:opacity-30" :disabled="vi === 0" aria-label="上移" @click="moveValue(g, vi, -1)"><ArrowUp class="size-3" /></button>
                <button class="text-muted hover:text-ink disabled:opacity-30" :disabled="vi === g.values.length - 1" aria-label="下移" @click="moveValue(g, vi, 1)"><ArrowDown class="size-3" /></button>
              </div>
              <span class="flex-1">{{ v.label }}
                <span v-if="!v.defined_in_legacy" class="tag tag-seal ml-1" title="该项未在旧系统字段定义中出现，仅出现在原始标注数据里">原始数据外项</span>
              </span>
              <RouterLink :to="{ name: 'search', query: { values: String(v.id), corpora: String(id) } }" class="text-xs text-muted tabular-nums hover:text-accent">
                {{ v.usage.toLocaleString() }} 条
              </RouterLink>
              <div class="flex opacity-60 group-hover:opacity-100">
                <button class="btn-icon size-7" title="重命名" @click="valForm = { group: g, value: v, label: v.label }"><Pencil class="size-3.5" /></button>
                <button class="btn-icon size-7" title="合并到其他标注项" @click="merging = { value: v, into: null }"><Combine class="size-3.5" /></button>
                <button class="btn-icon size-7 hover:text-seal" title="删除" @click="delValue(v)"><Trash2 class="size-3.5" /></button>
              </div>
            </li>
            <li v-if="!g.values.length" class="px-4 py-3 text-sm text-muted">暂无标注项</li>
          </ul>
        </article>
        <p v-if="!groups.length" class="card px-4 py-8 text-center text-sm text-muted">尚未定义标注体系</p>
      </div>
    </section>

    <Modal :model-value="!!vForm" :title="vForm?.id ? '编辑版本' : '添加版本'" @update:model-value="(o) => !o && (vForm = null)">
      <form v-if="vForm" id="vf" class="space-y-3" @submit.prevent="saveVersion">
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label" for="vk">类型</label><select id="vk" v-model="vForm.kind" class="input"><option value="source">原文</option><option value="translation">译文</option></select></div>
          <div><label class="label" for="vl">语言代码</label><input id="vl" v-model="vForm.lang" class="input" required /></div>
        </div>
        <div><label class="label" for="vn">名称</label><input id="vn" v-model="vForm.label" class="input" placeholder="如：甲译本" required /></div>
        <div><label class="label" for="vp">作者 / 译者</label><input id="vp" v-model="vForm.person" class="input" /></div>
        <div><label class="label" for="vb">出处</label><textarea id="vb" v-model="vForm.bibliography" rows="2" class="input h-auto py-2" /></div>
        <div><label class="label" for="vs">排序</label><input id="vs" v-model.number="vForm.sort_order" type="number" class="input w-28" /></div>
      </form>
      <template #footer><button class="btn-ghost" @click="vForm = null">取消</button><button form="vf" class="btn-primary">保存</button></template>
    </Modal>

    <Modal :model-value="!!wForm" :title="wForm?.id ? '编辑作品' : '添加作品'" @update:model-value="(o) => !o && (wForm = null)">
      <form v-if="wForm" id="wf" class="space-y-3" @submit.prevent="saveWork">
        <div><label class="label" for="ws">原文标题</label><input id="ws" v-model="wForm.title_source" class="input font-display" required /></div>
        <div><label class="label" for="wt">译文标题</label><input id="wt" v-model="wForm.title_target" class="input" /></div>
        <div><label class="label" for="wa">作者</label><input id="wa" v-model="wForm.author" class="input" /></div>
      </form>
      <template #footer><button class="btn-ghost" @click="wForm = null">取消</button><button form="wf" class="btn-primary">保存</button></template>
    </Modal>

    <Modal :model-value="!!gForm" :title="gForm?.id ? '编辑标注组' : '新建标注组'" @update:model-value="(o) => !o && (gForm = null)">
      <form v-if="gForm" id="gf" class="space-y-3" @submit.prevent="saveGroup">
        <div><label class="label" for="gn">名称</label><input id="gn" v-model="gForm.name" class="input" required /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label" for="gk">英文标识（可选）</label><input id="gk" v-model="gForm.key" class="input" /></div>
          <div><label class="label" for="gw">选择方式</label>
            <select id="gw" v-model="gForm.widget" class="input"><option v-for="(l, k) in WIDGET" :key="k" :value="k">{{ l }}</option></select></div>
        </div>
        <div><label class="label" for="gd">说明</label><input id="gd" v-model="gForm.description" class="input" /></div>
      </form>
      <template #footer><button class="btn-ghost" @click="gForm = null">取消</button><button form="gf" class="btn-primary">保存</button></template>
    </Modal>

    <Modal :model-value="!!valForm" :title="valForm?.value ? '重命名标注项' : `添加标注项 · ${valForm?.group.name}`" @update:model-value="(o) => !o && (valForm = null)">
      <form v-if="valForm" id="valf" @submit.prevent="saveValue">
        <label class="label" for="vlab">名称</label><input id="vlab" v-model="valForm.label" class="input" required autofocus />
        <p v-if="valForm.value?.usage" class="mt-2 text-xs text-muted">重命名会同步影响已有的 {{ valForm.value.usage }} 条标注。</p>
      </form>
      <template #footer><button class="btn-ghost" @click="valForm = null">取消</button><button form="valf" class="btn-primary">保存</button></template>
    </Modal>

    <Modal :model-value="!!merging" title="合并标注项" @update:model-value="(o) => !o && (merging = null)">
      <template v-if="merging">
        <p class="text-sm">将“<b>{{ merging.value.label }}</b>”的 {{ merging.value.usage }} 条标注迁移到：</p>
        <select v-model="merging.into" class="input mt-3">
          <option :value="null" disabled>选择目标标注项</option>
          <option v-for="v in allValues.filter((x) => x.id !== merging!.value.id)" :key="v.id" :value="v.id">{{ v.group }}：{{ v.label }}</option>
        </select>
        <p class="mt-2 text-xs text-muted">合并后原标注项会被删除。</p>
      </template>
      <template #footer><button class="btn-ghost" @click="merging = null">取消</button><button class="btn-primary" :disabled="!merging?.into" @click="doMerge">合并</button></template>
    </Modal>
  </div>
</template>
