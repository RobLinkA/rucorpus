<script setup lang="ts">
import { onKeyStroke } from '@vueuse/core'
import { BookOpen, ChevronLeft, ChevronRight, Link2, LoaderCircle, NotebookPen, PencilLine } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { GroupDetail, Segment } from '@/api/types'
import AnnotationEditor from '@/components/AnnotationEditor.vue'
import AnnotationPills from '@/components/AnnotationPills.vue'
import FavoriteButton from '@/components/FavoriteButton.vue'
import { useMeta } from '@/stores/meta'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const route = useRoute()
const router = useRouter()
const meta = useMeta()
const session = useSession()
const toast = useToast()
const g = ref<GroupDetail | null>(null)
const error = ref('')
const loading = ref(false)
const ctxVersion = ref<number | null>(null)
const editing = ref<Segment | null>(null)
const editOpen = ref(false)
const note = ref('')
const noteSaved = ref('')

watch(() => route.params.id, async (id) => {
  if (!id) return
  loading.value = true
  error.value = ''
  try {
    g.value = await api.get<GroupDetail>(`/groups/${id}`)
    if (!ctxVersion.value || !g.value.rows.some((r) => r.version_id === ctxVersion.value))
      ctxVersion.value = g.value.rows[0]?.version_id ?? null
    note.value = noteSaved.value = ''
    if (g.value.favorite) loadNote()
  } catch (e) { error.value = e instanceof Error ? e.message : String(e) } finally { loading.value = false }
}, { immediate: true })

async function loadNote() {
  if (!g.value || !session.loggedIn) return
  const f = await api.get<{ note: string }>(`/me/favorites/by-group/${g.value.id}`).catch(() => null)
  note.value = noteSaved.value = f?.note ?? ''
}
watch(() => g.value?.favorite, (fav, old) => { if (fav && old === false) note.value = noteSaved.value = '' })

async function saveNote() {
  if (!g.value) return
  try {
    await api.put(`/me/favorites/by-group/${g.value.id}`, { note: note.value })
    noteSaved.value = note.value
    toast.ok('笔记已保存')
  } catch (e) { toast.error(e) }
}

const corpus = computed(() => (g.value ? meta.corpusById.get(g.value.corpus_id) : undefined))
const source = computed(() => corpus.value?.versions.find((v) => v.kind === 'source'))
const go = (id: number | null) => id && router.push({ name: 'group', params: { id } })
onKeyStroke('ArrowLeft', (e) => { if (!(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) go(g.value?.prev ?? null) })
onKeyStroke('ArrowRight', (e) => { if (!(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)) go(g.value?.next ?? null) })

async function copyLink() {
  await navigator.clipboard.writeText(location.href)
  toast.ok('链接已复制')
}
function edit(s: Segment) { editing.value = s; editOpen.value = true }
</script>

<template>
  <div class="mx-auto max-w-6xl px-4 py-6 sm:px-6">
    <div v-if="error" class="card px-5 py-4 text-sm text-seal">{{ error }}</div>
    <template v-if="g">
      <nav class="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px] text-muted" aria-label="位置">
        <span>{{ corpus?.name }}</span><span>›</span>
        <RouterLink :to="{ name: 'read', params: { workId: g.work_id }, query: { around: g.id } }" class="hover:text-accent">{{ meta.workTitle(g.work_id) }}</RouterLink>
        <span>›</span><span class="tabular-nums">第 {{ g.paragraph_seq + 1 }} 段 · 第 {{ g.seq + 1 }} 句组</span>
        <span class="ml-auto tabular-nums">{{ g.position + 1 }} / {{ g.work_total }}</span>
        <LoaderCircle v-if="loading" class="size-4 animate-spin" />
      </nav>

      <div class="mt-4 grid gap-6 lg:grid-cols-[1fr_17rem]">
        <div class="min-w-0 space-y-4">
          <section class="card p-5 sm:p-6">
            <h2 class="mb-2 text-[13px] font-semibold text-accent">{{ source?.label || '原文' }}</h2>
            <p class="corpus-text text-[19px] leading-[1.8]">{{ g.source }}</p>
          </section>

          <section v-for="r in g.rows" :key="r.version_id" class="card p-5 sm:p-6">
            <div class="mb-2 grid gap-x-6 gap-y-1 sm:grid-cols-[auto_minmax(0,1fr)] sm:items-baseline">
              <h2 class="font-semibold">{{ meta.versionById.get(r.version_id)?.label }}</h2>
              <span class="min-w-0 text-right text-[13px] leading-relaxed break-words text-muted">
                {{ meta.versionById.get(r.version_id)?.bibliography }}</span>
            </div>
            <div class="divide-y divide-line">
              <div v-for="s in r.segments" :key="s.id" class="py-3 first:pt-1 last:pb-0">
                <p v-if="r.segments.length > 1 || s.source !== g.source" class="mb-1.5 font-display text-[14px] leading-relaxed text-muted"
                   title="该译本对应的原文切分">{{ s.source }}</p>
                <p class="corpus-text text-[18px]">{{ s.target }}</p>
                <div class="mt-2 flex flex-wrap items-center gap-1.5">
                  <span v-if="s.unsplit" class="tag">未切分整段</span>
                  <AnnotationPills :values="s.annotations" :ai="s.ai" show-evidence />
                  <span v-if="!s.annotations.length && !s.unsplit" class="text-xs text-muted">无标注</span>
                  <button v-if="session.canEdit" class="btn-ghost btn-sm ml-auto h-7 text-xs" @click="edit(s)">
                    <PencilLine class="size-3.5" />编辑标注
                  </button>
                  <span class="text-[11px] text-muted tabular-nums" :class="!session.canEdit && 'ml-auto'">#{{ s.id }}</span>
                </div>
              </div>
            </div>
          </section>
        </div>

        <aside class="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <div class="card flex items-center justify-between p-2">
            <button class="btn-ghost" :disabled="!g.prev" title="上一句组（←）" @click="go(g.prev)"><ChevronLeft class="size-4" />上一句</button>
            <button class="btn-ghost" :disabled="!g.next" title="下一句组（→）" @click="go(g.next)">下一句<ChevronRight class="size-4" /></button>
          </div>
          <div class="card space-y-1 p-2">
            <FavoriteButton v-model="g.favorite" :group-id="g.id" show-label />
            <RouterLink :to="{ name: 'read', params: { workId: g.work_id }, query: { around: g.id } }" class="menu-item">
              <BookOpen class="size-4" />在平行阅读中定位
            </RouterLink>
            <button class="menu-item w-full" @click="copyLink"><Link2 class="size-4" />复制链接</button>
          </div>
          <div v-if="g.favorite && session.loggedIn" class="card p-3">
            <label class="mb-1.5 flex items-center gap-1.5 text-[13px] font-medium text-ink-2" for="note"><NotebookPen class="size-4" />收藏笔记</label>
            <textarea id="note" v-model="note" rows="4" class="input h-auto py-2" placeholder="记录这个例句的分析…" />
            <button class="btn-outline btn-sm mt-2 w-full" :disabled="note === noteSaved" @click="saveNote">保存笔记</button>
          </div>
        </aside>
      </div>

      <section class="mt-10">
        <div class="mb-3 flex flex-wrap items-center gap-2">
          <h2 class="font-display text-xl font-semibold">上下文</h2>
          <div class="ml-auto flex flex-wrap gap-1">
            <button v-for="r in g.rows" :key="r.version_id" class="chip h-7" :class="ctxVersion === r.version_id && 'chip-on'"
                    @click="ctxVersion = r.version_id">{{ meta.versionById.get(r.version_id)?.label }}</button>
          </div>
        </div>
        <ol class="card divide-y divide-line">
          <li v-for="c in g.context" :key="c.id">
            <RouterLink :to="{ name: 'group', params: { id: c.id } }"
                        class="grid gap-x-6 gap-y-1 px-5 py-3 transition md:grid-cols-2"
                        :class="c.is_current ? 'bg-accent-soft shadow-[inset_2px_0_0_var(--accent)]' : 'hover:bg-surface-2/60'" :aria-current="c.is_current ? 'true' : undefined">
              <p class="corpus-text text-[15px]">{{ c.source }}</p>
              <p class="corpus-text text-[15px] text-ink-2">{{ ctxVersion ? c.targets[ctxVersion] : '' }}</p>
            </RouterLink>
          </li>
        </ol>
      </section>
    </template>

    <AnnotationEditor v-if="editing && g" v-model="editOpen" :segment-id="editing.id" :corpus-id="g.corpus_id"
                      :values="editing.annotations" :context="editing.target"
                      :ai="editing.ai" @saved="(v, ai) => { if (editing) { editing.annotations = v; editing.ai = ai } }" />
  </div>
</template>
