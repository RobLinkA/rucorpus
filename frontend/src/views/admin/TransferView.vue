<script setup lang="ts">
import { CheckCircle2, Download, FileSpreadsheet, LoaderCircle, Upload } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useMeta } from '@/stores/meta'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

interface Job {
  id: number; kind: string; filename: string; status: string; created_at: string; user: string | null
  preview: { corpus_id: number | null; summary?: Record<string, unknown>; error_count?: number; errors?: [number, string][] }
  result: Record<string, number>
}

const meta = useMeta()
const session = useSession()
const toast = useToast()

// ---- export
const exCorpus = ref<number>(meta.corpora[0]?.id ?? 1)
const exWorks = ref<number[]>([])
const exCorpusObj = computed(() => meta.corpusById.get(exCorpus.value))
const exportHref = (format: string) => api.href(`/manage/transfer/export/${exCorpus.value}`, { format, works: exWorks.value.join(',') || undefined })

// ---- import
const kind = ref<'annotations' | 'corpus'>('annotations')
const imCorpus = ref<number | 0>(meta.corpora[0]?.id ?? 0)
const updateText = ref(false)
const file = ref<File | null>(null)
const dragging = ref(false)
const busy = ref(false)
const job = ref<Job | null>(null)
const jobs = ref<Job[]>([])

async function loadJobs() { jobs.value = await api.get<Job[]>('/manage/transfer/jobs') }
onMounted(() => {
  loadJobs()
  meta.load().then(() => { exCorpus.value ||= meta.corpora[0]?.id; imCorpus.value ||= meta.corpora[0]?.id ?? 0 })
})

function pick(e: Event | DragEvent) {
  const f = (e as DragEvent).dataTransfer?.files?.[0] ?? (e.target as HTMLInputElement).files?.[0]
  dragging.value = false
  if (f) { file.value = f; job.value = null }
}

async function upload() {
  if (!file.value) return
  const fd = new FormData()
  fd.append('kind', kind.value)
  fd.append('corpus_id', String(imCorpus.value || 0))
  fd.append('update_text', String(updateText.value))
  fd.append('file', file.value)
  busy.value = true
  try { job.value = await api.post<Job>('/manage/transfer/upload', fd) } catch (e) { toast.error(e) } finally { busy.value = false }
}
async function commit() {
  busy.value = true
  try {
    job.value = await api.post<Job>(`/manage/transfer/jobs/${job.value!.id}/commit`)
    toast.ok('导入完成')
    file.value = null
    loadJobs(); meta.load(true)
  } catch (e) { toast.error(e) } finally { busy.value = false }
}
async function cancel() {
  await api.post(`/manage/transfer/jobs/${job.value!.id}/cancel`)
  job.value = null; file.value = null
  loadJobs()
}

const S = computed(() => (job.value?.preview.summary ?? {}) as Record<string, any>) // eslint-disable-line @typescript-eslint/no-explicit-any
const STATUS: Record<string, string> = { preview: '待确认', done: '已导入', failed: '失败', cancelled: '已取消' }
const KIND: Record<string, string> = { annotations: '标注更新', corpus: '语料导入' }
const time = (s: string) => new Date(s).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
</script>

<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-semibold">导入导出</h1>

    <section class="card p-5">
      <h2 class="flex items-center gap-2 font-semibold"><Download class="size-4" />导出</h2>
      <p class="mt-1 text-sm text-muted">导出的 Excel 含语料库信息、版本、作品、标注体系和全部句对（每个标注组一列），修改标注列后可直接导回。</p>
      <div class="mt-4 flex flex-wrap items-end gap-3">
        <div><label class="label" for="ec">语料库</label>
          <select id="ec" v-model.number="exCorpus" class="input w-48" @change="exWorks = []">
            <option v-for="c in meta.corpora" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select></div>
        <div v-if="exCorpusObj?.works.length" class="min-w-0 flex-1">
          <div class="label">作品（不选即全部）</div>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="w in exCorpusObj.works" :key="w.id" type="button" class="chip h-7" :class="exWorks.includes(w.id) && 'chip-on'"
                    @click="exWorks = exWorks.includes(w.id) ? exWorks.filter((x) => x !== w.id) : [...exWorks, w.id]">{{ w.title_target || w.title_source }}</button>
          </div>
        </div>
      </div>
      <div class="mt-4 flex flex-wrap gap-2">
        <a :href="exportHref('xlsx')" class="btn-primary"><FileSpreadsheet class="size-4" />导出 Excel</a>
        <a :href="exportHref('csv')" class="btn-outline">导出句对 CSV</a>
        <a :href="api.href(`/manage/transfer/template/${exCorpus}`)" class="btn-ghost">下载空白模板</a>
      </div>
    </section>

    <section class="card p-5">
      <h2 class="flex items-center gap-2 font-semibold"><Upload class="size-4" />导入</h2>
      <div class="mt-4 grid gap-4 md:grid-cols-2">
        <label class="card flex cursor-pointer gap-3 p-4 transition" :class="kind === 'annotations' && 'ring-2 ring-accent/40'">
          <input v-model="kind" type="radio" value="annotations" class="mt-1 accent-[var(--accent)]" @change="job = null" />
          <span><b>标注更新</b><br /><span class="text-sm text-muted">按“句对ID”更新已有句对的标注（可选同时更新文本）。用于线下 Excel 标注后回传。</span></span>
        </label>
        <label class="card flex gap-3 p-4 transition" :class="[kind === 'corpus' && 'ring-2 ring-accent/40', session.isAdmin ? 'cursor-pointer' : 'opacity-50']">
          <input v-model="kind" type="radio" value="corpus" class="mt-1 accent-[var(--accent)]" :disabled="!session.isAdmin" @change="job = null" />
          <span><b>语料导入</b><br /><span class="text-sm text-muted">新建语料库，或向已有语料库追加新作品（需管理员）。按“作品 / 段落 / 句组 / 版本”自动建立对齐。</span></span>
        </label>
      </div>

      <div class="mt-4 flex flex-wrap items-end gap-4">
        <div><label class="label" for="ic">{{ kind === 'annotations' ? '语料库' : '目标' }}</label>
          <select id="ic" v-model.number="imCorpus" class="input w-56" @change="job = null">
            <option v-if="kind === 'corpus'" :value="0">新建语料库（按文件中的“语料库”表）</option>
            <option v-for="c in meta.corpora" :key="c.id" :value="c.id">{{ kind === 'corpus' ? `追加到：${c.name}` : c.name }}</option>
          </select></div>
        <label v-if="kind === 'annotations'" class="flex items-center gap-2 pb-2 text-sm">
          <input v-model="updateText" type="checkbox" class="accent-[var(--accent)]" @change="job = null" />同时更新原文 / 译文文本
        </label>
      </div>

      <label class="mt-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-8 text-center transition"
             :class="dragging ? 'border-accent bg-accent-soft/40' : 'border-line-strong hover:border-accent/60'"
             @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="pick">
        <FileSpreadsheet class="size-8 text-muted" />
        <span v-if="file" class="font-medium">{{ file.name }} <span class="text-muted">（{{ (file.size / 1024).toFixed(0) }} KB）</span></span>
        <span v-else class="text-sm text-ink-2">拖入 .xlsx / .csv 文件，或点击选择</span>
        <input type="file" accept=".xlsx,.csv" class="sr-only" @change="pick" />
      </label>
      <div class="mt-4 flex gap-2">
        <button class="btn-primary" :disabled="!file || busy || (kind === 'annotations' && !imCorpus)" @click="upload">
          <LoaderCircle v-if="busy && !job" class="size-4 animate-spin" />上传并预览
        </button>
        <span class="self-center text-xs text-muted">预览阶段不会写入任何数据</span>
      </div>

      <div v-if="job" class="mt-5 rounded-xl border border-line bg-surface-2/50 p-4">
        <div class="flex items-center gap-2">
          <CheckCircle2 v-if="job.status === 'done'" class="size-5 text-ok" />
          <h3 class="font-semibold">{{ job.status === 'done' ? '导入完成' : '预览结果' }}</h3>
          <span class="text-sm text-muted">{{ job.filename }}</span>
        </div>

        <dl v-if="job.status === 'done'" class="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
          <div v-for="(v, k) in job.result" :key="k"><dt class="inline text-muted">{{ ({ applied_segments: '变更句对', skipped_rows: '跳过行', annotations_added: '新增标注', annotations_removed: '移除标注', text_updates: '文本更新', segments: '句对', works: '作品', corpus_id: '语料库ID' } as Record<string, string>)[k] ?? k }}：</dt><dd class="inline font-semibold tabular-nums">{{ v }}</dd></div>
        </dl>

        <template v-else>
          <dl v-if="job.kind === 'annotations'" class="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div><dt class="text-muted">文件行数</dt><dd class="text-lg font-semibold tabular-nums">{{ S.rows }}</dd></div>
            <div><dt class="text-muted">将变更句对</dt><dd class="text-lg font-semibold tabular-nums">{{ S.changed_segments }}</dd></div>
            <div><dt class="text-muted">新增 / 移除标注</dt><dd class="text-lg font-semibold tabular-nums">+{{ S.annotations_added }} / −{{ S.annotations_removed }}</dd></div>
            <div><dt class="text-muted">文本更新</dt><dd class="text-lg font-semibold tabular-nums">{{ S.text_updates }}</dd></div>
            <div class="col-span-full text-xs text-muted">识别的标注列：{{ (S.columns || []).join('、') || '无' }}
              <template v-if="S.ignored_columns?.length"> · 忽略的列：{{ S.ignored_columns.join('、') }}</template></div>
          </dl>
          <dl v-else class="mt-3 space-y-1 text-sm">
            <div><dt class="inline text-muted">目标：</dt><dd class="inline font-medium">{{ S.target }}{{ S.new_corpus ? '（新建，默认下架）' : '' }}</dd></div>
            <div><dt class="inline text-muted">规模：</dt><dd class="inline tabular-nums">{{ S.works }} 部作品 · {{ S.groups }} 个句组 · {{ S.segments }} 个句对</dd></div>
            <div><dt class="inline text-muted">版本：</dt><dd class="inline">{{ (S.versions || []).map((v: { label: string; new: boolean }) => v.label + (v.new ? '（新）' : '')).join('、') }}</dd></div>
            <div v-if="Object.keys(S.new_annotation_values || {}).length"><dt class="inline text-muted">将新建标注项：</dt>
              <dd class="inline">{{ Object.entries(S.new_annotation_values).map(([g, vs]) => `${g}：${(vs as string[]).join('、')}`).join('；') }}</dd></div>
          </dl>

          <div v-if="job.preview.error_count" class="mt-4">
            <div class="flex items-center gap-2 text-sm font-medium text-seal">
              {{ job.preview.error_count }} 处问题{{ job.kind === 'annotations' ? '（这些行将被跳过）' : '（需修正后重新上传）' }}
              <a :href="api.href(`/manage/transfer/jobs/${job.id}/errors`)" class="ml-auto text-xs text-accent hover:underline">下载错误明细</a>
            </div>
            <ul class="mt-2 max-h-48 overflow-y-auto rounded-lg border border-line bg-surface text-[13px]">
              <li v-for="(e, i) in job.preview.errors" :key="i" class="flex gap-3 border-b border-line px-3 py-1.5 last:border-0">
                <span class="w-14 shrink-0 text-muted tabular-nums">第 {{ e[0] }} 行</span><span>{{ e[1] }}</span>
              </li>
            </ul>
          </div>
          <div class="mt-4 flex gap-2">
            <button class="btn-primary" :disabled="busy || (job.kind === 'corpus' && !!job.preview.error_count) || (job.kind === 'annotations' && !S.changed_segments)" @click="commit">
              <LoaderCircle v-if="busy" class="size-4 animate-spin" />确认导入
            </button>
            <button class="btn-ghost" @click="cancel">取消</button>
          </div>
        </template>
      </div>
    </section>

    <section class="card">
      <h2 class="border-b border-line px-5 py-3 font-semibold">导入记录</h2>
      <table class="w-full text-sm">
        <tbody class="divide-y divide-line">
          <tr v-for="j in jobs" :key="j.id">
            <td class="px-5 py-2.5 text-xs text-muted tabular-nums">{{ time(j.created_at) }}</td>
            <td class="px-2 py-2.5">{{ KIND[j.kind] ?? j.kind }}</td>
            <td class="max-w-xs truncate px-2 py-2.5">{{ j.filename }}</td>
            <td class="px-2 py-2.5 text-ink-2">{{ j.user }}</td>
            <td class="px-2 py-2.5"><span class="tag" :class="j.status === 'done' && 'text-ok'">{{ STATUS[j.status] }}</span></td>
            <td class="px-5 py-2.5 text-right text-xs text-muted">{{ j.preview.error_count ? `${j.preview.error_count} 处问题` : '' }}</td>
          </tr>
          <tr v-if="!jobs.length"><td class="px-5 py-6 text-center text-muted">暂无记录</td></tr>
        </tbody>
      </table>
    </section>
  </div>
</template>
