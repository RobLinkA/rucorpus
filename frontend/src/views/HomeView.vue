<script setup lang="ts">
import { ArrowRight, BookOpen, Search, SlidersHorizontal, Sparkles } from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import AlignmentFigure from '@/components/AlignmentFigure.vue'
import { useMeta } from '@/stores/meta'

const meta = useMeta()
const router = useRouter()
const q = ref('')
const mode = ref<'morph' | 'exact'>('morph')
const scope = ref<number | null>(null)
const stats = ref<{ works: number; groups: number; segments: number; annotations: number; ai_annotations: number } | null>(null)
const inputEl = ref<HTMLInputElement>()

onMounted(async () => {
  inputEl.value?.focus()
  stats.value = await api.get('/stats')
})

const examples = [
  { q: 'человек', note: '匹配不同变化形式' },
  { q: '"на шее"', note: '连续出现的短语' },
  { q: 'чинов*', note: '匹配相同开头' },
  { q: '语言', note: '直接输入中文' },
]

function submit(text = q.value, match = mode.value) {
  if (!text.trim()) return inputEl.value?.focus()
  router.push({ name: 'search', query: { q: text.trim(), mode: match === 'exact' ? 'exact' : undefined, corpora: scope.value ? [String(scope.value)] : undefined } })
}

const LANG: Record<string, string> = { ru: '俄', zh: '汉', en: '英', fr: '法', es: '西' }
const fmt = (n?: number) => (n ?? 0).toLocaleString('zh-CN')
const nonEmpty = computed(() => meta.corpora.filter((c) => c.works.length))
</script>

<template>
  <div>
    <section class="border-b border-line bg-surface">
      <div class="mx-auto grid max-w-[1240px] items-center gap-12 px-4 py-14 sm:px-6 lg:grid-cols-[1fr_1.05fr] lg:py-20">
        <div class="min-w-0">
          <h1 class="font-display text-[2rem] leading-[1.3] font-semibold tracking-tight sm:text-[2.6rem]">
            RuCorpus 平行语料库
          </h1>
          <p class="mt-4 max-w-xl text-[15.5px] leading-[1.8] text-ink-2">
            面向多译本对照、语料检索与句级标注。俄语支持词形还原；英语、法语和西语支持基础词语检索。
            请导入自己的文本和标注体系开始使用。
          </p>

          <form class="mt-8" role="search" @submit.prevent="submit()">
            <div class="flex items-center gap-2 rounded-xl border border-line-strong bg-surface p-1.5 shadow-lift transition focus-within:border-accent focus-within:shadow-glow">
              <Search class="ml-2.5 size-5 shrink-0 text-muted" />
              <input ref="inputEl" v-model="q" type="search" aria-label="检索词"
                     class="h-11 min-w-0 flex-1 border-0 bg-transparent font-serif text-[17px] outline-none focus-visible:outline-none placeholder:font-sans placeholder:text-[15px] placeholder:text-muted"
                     placeholder="输入关键词或短语" />
              <button class="btn-primary h-11 px-4 text-[15px] sm:px-6">检索</button>
            </div>
            <div class="mt-5 grid gap-4 min-[420px]:grid-cols-2 sm:gap-6">
              <fieldset class="min-w-0">
                <legend class="label">匹配方式</legend>
                <div class="flex h-9 rounded-lg bg-surface-2 p-0.5 text-[13px]" role="radiogroup" aria-label="匹配方式">
                  <button v-for="m in [{ v: 'morph', l: '模糊匹配' }, { v: 'exact', l: '精确匹配' }] as const" :key="m.v" type="button"
                          role="radio" :aria-checked="mode === m.v" class="flex-1 whitespace-nowrap rounded-md px-2 transition"
                          :class="mode === m.v ? 'bg-surface text-ink shadow-card font-medium' : 'text-muted hover:text-ink'"
                          @click="mode = m.v">{{ m.l }}</button>
                </div>
              </fieldset>
              <div class="min-w-0">
                <label for="home-scope" class="label">检索范围</label>
                <select id="home-scope" v-model="scope" class="input">
                  <option :value="null">全部语料</option>
                  <option v-for="c in nonEmpty" :key="c.id" :value="c.id">{{ c.name }}</option>
                </select>
              </div>
            </div>
            <p class="mt-2.5 text-[12px] leading-relaxed text-muted" aria-live="polite">
              {{ mode === 'morph' ? '模糊匹配：自动查找俄语单词的不同变化形式。' : '精确匹配：只查找输入的词形，不区分大小写。' }}
            </p>
          </form>

          <div class="mt-6 border-t border-line pt-4">
            <p class="mb-2 text-[12px] text-muted">试试这些检索</p>
            <div class="grid grid-cols-2 gap-x-3 gap-y-1">
              <button v-for="e in examples" :key="e.q" type="button"
                      class="group min-w-0 rounded-lg px-2 py-2 text-left transition hover:bg-surface-2" @click="submit(e.q, 'morph')">
                <span class="block whitespace-nowrap font-serif text-[16px] text-accent group-hover:underline">{{ e.q }}</span>
                <span class="mt-1 block text-[11px] leading-relaxed text-muted sm:text-[12px]">{{ e.note }}</span>
              </button>
            </div>
          </div>
        </div>

        <AlignmentFigure class="hidden md:block" />
      </div>
    </section>

    <section class="mx-auto max-w-[1240px] px-4 sm:px-6">
      <dl class="grid grid-cols-2 border-b border-line md:grid-cols-4">
        <div v-for="(s, i) in [
          { l: '作品', v: stats?.works }, { l: '对齐句组', v: stats?.groups },
          { l: '译文句对', v: stats?.segments }, { l: '句级标注', v: stats?.annotations }]" :key="s.l"
             class="py-7 md:px-6" :class="i > 0 && 'md:border-l md:border-line'">
          <dd class="font-display text-[2rem] leading-none font-semibold tabular-nums">{{ stats ? fmt(s.v) : '—' }}</dd>
          <dt class="mt-2 text-[13px] text-muted">{{ s.l }}
            <RouterLink v-if="s.l === '句级标注' && stats?.ai_annotations" to="/help#ai" class="ml-1 text-accent hover:underline">含 ✦ AI {{ fmt(stats.ai_annotations) }}</RouterLink>
          </dt>
        </div>
      </dl>

      <div class="mt-14 mb-6 flex items-end justify-between gap-4">
        <div>
          <div class="kicker">Collections</div>
          <h2 class="mt-1.5 font-display text-[1.75rem] font-semibold">语料库</h2>
        </div>
        <RouterLink to="/help#sources" class="text-[13px] muted-link">版本与出处 →</RouterLink>
      </div>

      <p v-if="meta.loaded && !meta.corpora.length" class="card p-6 text-sm leading-7 text-muted">当前数据库为空。请管理员登录后台，创建语料库并导入自己的文本、译本与标注体系。</p>
      <div class="grid gap-5 lg:grid-cols-3">
        <article v-for="(c, i) in meta.corpora" :key="c.id" class="card card-hover flex flex-col p-6"
                 :class="c.works.length > 0 && i === 0 ? 'lg:col-span-2' : ''">
          <div class="flex items-start gap-3">
            <div class="min-w-0 flex-1">
              <h3 class="font-display text-xl font-semibold">{{ c.name }}</h3>
              <p class="mt-1 text-[13.5px] text-ink-2">{{ c.description }}</p>
            </div>
            <span class="shrink-0 rounded-full bg-accent-soft px-2.5 py-1 text-[12px] font-medium text-accent">
              {{ LANG[c.source_lang] ?? c.source_lang }} → {{ LANG[c.target_lang] ?? c.target_lang }}
            </span>
          </div>

          <template v-if="c.works.length">
            <div class="mt-5 grid gap-6" :class="i === 0 ? 'sm:grid-cols-2' : ''">
              <div>
                <div class="label">版本</div>
                <ul class="divide-y divide-line">
                  <li v-for="v in c.versions" :key="v.id" class="flex items-baseline gap-2 py-1.5 text-[13.5px]" :title="v.bibliography">
                    <span :class="v.kind === 'source' ? 'font-medium text-accent' : 'text-ink'">{{ v.label }}</span>
                    <span v-if="v.segments" class="ml-auto text-[12px] text-muted tabular-nums">{{ fmt(v.segments) }} 句</span>
                  </li>
                </ul>
              </div>
              <div>
                <div class="label">作品</div>
                <div class="flex flex-wrap gap-1.5">
                  <RouterLink v-for="w in c.works" :key="w.id" :to="{ name: 'read', params: { workId: w.id } }"
                              class="chip h-7 text-[13px]" :title="w.title_source">{{ w.title_target || w.title_source }}</RouterLink>
                </div>
                <div class="label mt-5">标注维度</div>
                <div class="flex flex-wrap gap-x-3 gap-y-1.5">
                  <span v-for="g in c.annotation_groups" :key="g.id" class="inline-flex items-center gap-1.5 text-[13px] text-ink-2">
                    <span class="size-2 rounded-full" :style="{ background: meta.groupColor.get(g.id) }" />{{ g.name }}
                  </span>
                </div>
              </div>
            </div>
            <div class="mt-auto flex gap-2 pt-6">
              <RouterLink :to="{ name: 'read', params: { workId: c.works[0].id } }" class="btn-outline btn-sm"><BookOpen class="size-3.5" />平行阅读</RouterLink>
              <RouterLink :to="{ name: 'search', query: { corpora: String(c.id) } }" class="btn-ghost btn-sm">按标注筛选<ArrowRight class="size-3.5" /></RouterLink>
            </div>
          </template>
          <div v-else class="mt-5 flex flex-1 flex-col items-center justify-center rounded-lg border border-dashed border-line-strong px-4 py-10 text-center">
            <span class="text-[13px] font-medium text-warn">建设中</span>
            <span class="mt-1 text-[13px] text-muted">暂无语料</span>
          </div>
        </article>
      </div>

      <div class="mt-16 grid gap-8 border-t border-line pt-12 md:grid-cols-3">
        <RouterLink v-for="f in [
          { to: '/search', icon: SlidersHorizontal, t: '组合筛选', d: '语料库、作品、译本与标注项层层组合，标注可设“任一”“全部”或“组内任一、组间全部”，也可排除。' },
          { to: '/read', icon: BookOpen, t: '平行阅读', d: '原文与多个译本逐句或逐段对照，自由显隐译本列，点击任一句进入详情与上下文。' },
          { to: '/help#ai', icon: Sparkles, t: '人工智能辅助标注', d: '在人工标注之外，系统依据形态与句法分析补充标注，并以 ✦ 标出、注明依据，可随时区分检索。' }]"
                    :key="f.t" :to="f.to" class="group">
          <component :is="f.icon" class="size-5 text-accent" />
          <div class="mt-3 font-display text-lg font-semibold group-hover:text-accent">{{ f.t }}</div>
          <p class="mt-1.5 text-[13.5px] leading-[1.75] text-ink-2">{{ f.d }}</p>
        </RouterLink>
      </div>
    </section>
  </div>
</template>
