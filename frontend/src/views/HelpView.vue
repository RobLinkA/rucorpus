<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useMeta } from '@/stores/meta'

const meta = useMeta()
interface AiReport {
  generated_at: string; added: number; corrected: number
  labels: { corpus_id: number; group: string; label: string; added: number; corrected: number }[]
}
const report = ref<AiReport | null>(null)
onMounted(async () => {
  const result = await api.get<Partial<AiReport>>('/ai/report').catch(() => null)
  if (result && Array.isArray(result.labels) && typeof result.added === 'number' && typeof result.corrected === 'number') {
    report.value = result as AiReport
  }
})
const reportCorpora = computed(() => meta.corpora.map((c) => ({
  id: c.id,
  name: c.name,
  rows: report.value?.labels.filter((r) => r.corpus_id === c.id) ?? [],
})).filter((c) => c.rows.length))
const syntax = [
  { q: 'человек', d: '模糊匹配（默认）：命中该词的全部变化形式，如 человека、людей、человеком。' },
  { q: 'человек（精确匹配）', d: '精确匹配：只命中与输入完全相同的词形（不区分大小写，ё 与 е 视为相同）。' },
  { q: 'шел домой', d: '多个词以空格分隔，表示同一句对中同时出现（与关系）。' },
  { q: '"на шее"', d: '用引号括起的短语，按词序连续匹配。也可用 « » 或 “ ”。' },
  { q: 'чинов*', d: '星号表示前缀匹配：чиновник、чиновника、чинов…' },
  { q: '语言', d: '中文按字符串匹配；不同语言可混合输入。' },
]
</script>

<template>
  <div class="mx-auto max-w-3xl px-4 py-10 sm:px-6">
    <h1 class="font-display text-3xl font-semibold">使用说明</h1>
    <p class="mt-4 text-sm leading-7 text-ink-2">俄语支持词形还原。英语、法语和西语支持大小写无关的单词、短语与前缀检索，保留重音差别；不提供这些语言的词形还原。检索示例展示语法，是否有结果取决于你导入的数据。</p>

    <section class="mt-8">
      <h2 class="mb-3 font-display text-xl font-semibold">检索语法</h2>
      <dl class="card divide-y divide-line">
        <div v-for="s in syntax" :key="s.q" class="grid gap-1 px-5 py-3 sm:grid-cols-[11rem_1fr]">
          <dt class="font-display text-[15px] text-accent">{{ s.q }}</dt>
          <dd class="text-sm text-ink-2">{{ s.d }}</dd>
        </div>
      </dl>
      <p class="mt-3 text-sm leading-relaxed text-ink-2">
        检索结果以<strong>对齐句组</strong>为单位：同一段原文在各译本中的对应译文放在一起。不同译者对原文的断句并不相同，
        系统会把各译本都能对齐的最小原文片段作为一个句组，因此个别句组包含某一译本的多个句子。
        检索框下方的“范围、译本、标注”可缩小检索范围；多个标注项可选择“任一”“全部”或“组内任一、组间全部”。
      </p>
    </section>

    <section class="mt-10">
      <h2 class="mb-3 font-display text-xl font-semibold">平行阅读</h2>
      <p class="text-sm leading-relaxed text-ink-2">
        可按句或按段对照原文与译文，自由选择显示的译本。按句对照默认显示标注，可取消“显示标注”来隐藏。
        使用键盘 <kbd>←</kbd> 翻到上一页、<kbd>→</kbd> 翻到下一页，
        也可使用页面底部的分页按钮。输入页码、选择作品或操作下拉菜单时，方向键不会触发翻页。
      </p>
    </section>

    <section class="mt-10">
      <h2 class="mb-3 font-display text-xl font-semibold">标注体系</h2>
      <p class="mb-4 text-sm text-ink-2">标注分为“标注组 → 标注项”两层，各语料库独立定义，标注附着于具体译本的句对。</p>
      <div v-for="c in meta.corpora.filter((x) => x.annotation_groups.length)" :key="c.id" class="card mb-4 p-5">
        <h3 class="font-semibold">{{ c.name }}</h3>
        <dl class="mt-3 space-y-2 text-sm">
          <div v-for="g in c.annotation_groups" :key="g.id" class="grid gap-1 sm:grid-cols-[7rem_1fr]">
            <dt class="text-muted">{{ g.name }}</dt>
            <dd class="flex flex-wrap gap-1"><span v-for="v in g.values" :key="v.id" class="tag">{{ v.label }}</span></dd>
          </div>
        </dl>
      </div>
    </section>

    <section id="sources" class="mt-10">
      <h2 class="mb-3 font-display text-xl font-semibold">版本与出处</h2>
      <div v-for="c in meta.corpora.filter((x) => x.versions.length)" :key="c.id" class="card mb-4 p-5">
        <h3 class="font-semibold">{{ c.name }}</h3>
        <ul class="mt-3 space-y-2 text-sm">
          <li v-for="v in c.versions" :key="v.id" class="grid gap-1 sm:grid-cols-[9rem_1fr]">
            <span class="font-medium">{{ v.label }}</span>
            <span class="text-ink-2">{{ [v.person, v.bibliography].filter(Boolean).join('　') || '—' }}</span>
          </li>
        </ul>
      </div>
    </section>

    <section id="ai" class="mt-10">
      <h2 class="mb-3 font-display text-xl font-semibold">✦ AI 辅助标注统计</h2>
      <p class="text-sm leading-relaxed text-ink-2">
        以下为最近一次自动标注的统计。“新增”指补充的标注，“更正”指修正的原有人工标注。两类均以 ✦ 标出，可在高级检索中选择“仅 AI”查看。
      </p>
      <template v-if="report">
        <dl class="mt-5 grid grid-cols-3 gap-3">
          <div v-for="s in [
            { label: 'AI 标注合计', value: report.added + report.corrected },
            { label: '新增标注', value: report.added },
            { label: '更正人工标注', value: report.corrected },
          ]" :key="s.label" class="card px-2 py-5 text-center sm:px-4">
            <dd class="font-display text-2xl font-semibold text-accent tabular-nums sm:text-3xl">{{ s.value.toLocaleString() }}</dd>
            <dt class="mt-2 text-[12px] text-muted sm:text-[13px]">{{ s.label }}</dt>
          </div>
        </dl>
        <div v-for="c in reportCorpora" :key="c.id" class="card mt-5 overflow-hidden">
          <h3 class="border-b border-line bg-surface-2/50 px-4 py-3 text-sm font-semibold">{{ c.name }}</h3>
          <table class="w-full text-sm">
            <thead class="border-b border-line text-left text-[12px] text-muted">
              <tr>
                <th scope="col" class="px-4 py-2.5 font-medium">标注项</th>
                <th scope="col" class="w-16 px-2 py-2.5 text-right font-medium sm:w-20">新增</th>
                <th scope="col" class="w-16 pr-4 pl-2 py-2.5 text-right font-medium sm:w-20">更正</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-line">
              <tr v-for="r in c.rows" :key="`${r.group}-${r.label}`">
                <th scope="row" class="px-4 py-3 text-left font-normal">
                  <span class="block text-[11px] text-muted">{{ r.group }}</span>
                  <span class="mt-0.5 block">{{ r.label }}</span>
                </th>
                <td class="px-2 py-3 text-right tabular-nums">{{ r.added.toLocaleString() }}</td>
                <td class="pr-4 pl-2 py-3 text-right tabular-nums">{{ r.corrected.toLocaleString() }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
      <p v-else class="card mt-5 px-5 py-6 text-sm text-muted">暂无 AI 标注统计。</p>
    </section>

  </div>
</template>
