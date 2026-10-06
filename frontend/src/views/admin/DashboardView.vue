<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'

interface Dash {
  corpora: { id: number; name: string; status: string; works: number; versions: number; groups: number; segments: number
    annotated_segments: number; annotations: number; ai_annotations: number; unsplit: number }[]
  annotation_groups: { id: number; corpus_id: number; name: string; usage: number }[]
  users: { total: number; active: number; by_role: Record<string, number> }
  activity: { favorites: number; searches: number }
  recent: { id: number; user: string | null; action: string; summary: string; created_at: string }[]
}
const d = ref<Dash | null>(null)
onMounted(async () => { d.value = await api.get<Dash>('/manage/dashboard') })
const pct = (a: number, b: number) => (b ? Math.round((a / b) * 100) : 0)
const fmt = (n: number) => n.toLocaleString('zh-CN')
const time = (s: string) => new Date(s).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
const maxUsage = (cid: number) => Math.max(1, ...(d.value?.annotation_groups.filter((g) => g.corpus_id === cid).map((g) => g.usage) ?? [1]))
</script>

<template>
  <div v-if="d" class="space-y-6">
    <h1 class="text-2xl font-semibold">概览</h1>

    <div class="grid gap-4 xl:grid-cols-3">
      <article v-for="c in d.corpora" :key="c.id" class="card p-5">
        <div class="flex items-center gap-2">
          <h2 class="font-semibold">{{ c.name }}</h2>
          <span class="tag ml-auto" :class="c.status === 'hidden' && 'tag-seal'">{{ c.status === 'hidden' ? '已下架' : '已发布' }}</span>
        </div>
        <dl class="mt-4 grid grid-cols-3 gap-3 text-sm">
          <div><dt class="text-xs text-muted">作品</dt><dd class="text-lg font-semibold tabular-nums">{{ c.works }}</dd></div>
          <div><dt class="text-xs text-muted">版本</dt><dd class="text-lg font-semibold tabular-nums">{{ c.versions }}</dd></div>
          <div><dt class="text-xs text-muted">句组</dt><dd class="text-lg font-semibold tabular-nums">{{ fmt(c.groups) }}</dd></div>
          <div><dt class="text-xs text-muted">句对</dt><dd class="text-lg font-semibold tabular-nums">{{ fmt(c.segments) }}</dd></div>
          <div class="col-span-2"><dt class="text-xs text-muted">标注</dt><dd class="text-lg font-semibold tabular-nums">{{ fmt(c.annotations) }}<span v-if="c.ai_annotations" class="ml-1.5 text-[12px] font-normal text-accent">含 ✦ AI {{ fmt(c.ai_annotations) }}</span></dd></div>
        </dl>
        <div v-if="c.segments" class="mt-4">
          <div class="mb-1 flex justify-between text-xs text-muted"><span>已标注句对</span><span class="tabular-nums">{{ pct(c.annotated_segments, c.segments) }}%</span></div>
          <div class="h-2 overflow-hidden rounded-full bg-surface-2"><div class="h-full rounded-full bg-accent" :style="{ width: pct(c.annotated_segments, c.segments) + '%' }" /></div>
        </div>
        <ul v-if="d.annotation_groups.some((g) => g.corpus_id === c.id)" class="mt-4 space-y-1.5">
          <li v-for="g in d.annotation_groups.filter((x) => x.corpus_id === c.id)" :key="g.id" class="grid grid-cols-[6.5rem_1fr_3rem] items-center gap-2 text-xs">
            <span class="truncate text-ink-2">{{ g.name }}</span>
            <span class="h-1.5 overflow-hidden rounded-full bg-surface-2"><span class="block h-full rounded-full bg-accent-2/70" :style="{ width: (g.usage / maxUsage(c.id)) * 100 + '%' }" /></span>
            <span class="text-right text-muted tabular-nums">{{ fmt(g.usage) }}</span>
          </li>
        </ul>
        <RouterLink v-if="c.unsplit" :to="{ name: 'admin-segments', query: { corpus: c.id, unsplit: '1' } }"
                    class="mt-4 block rounded-lg bg-seal-soft px-3 py-2 text-xs text-seal hover:underline">
          {{ c.unsplit }} 个未切分整段待处理 →
        </RouterLink>
        <p v-if="!c.segments" class="mt-4 text-sm text-muted">暂无语料，可在“导入导出”中导入。</p>
      </article>
    </div>

    <div class="grid gap-4 lg:grid-cols-[1fr_20rem]">
      <section class="card">
        <h2 class="border-b border-line px-5 py-3 font-semibold">最近操作</h2>
        <ul class="divide-y divide-line text-sm">
          <li v-for="r in d.recent" :key="r.id" class="flex gap-3 px-5 py-2.5">
            <span class="w-28 shrink-0 text-xs text-muted tabular-nums">{{ time(r.created_at) }}</span>
            <span class="w-20 shrink-0 truncate text-ink-2">{{ r.user ?? '—' }}</span>
            <span class="min-w-0 flex-1 truncate">{{ r.summary }}</span>
          </li>
          <li v-if="!d.recent.length" class="px-5 py-6 text-center text-muted">暂无记录</li>
        </ul>
      </section>
      <section class="card p-5 text-sm">
        <h2 class="font-semibold">用户与使用</h2>
        <dl class="mt-3 space-y-2">
          <div class="flex justify-between"><dt class="text-muted">用户总数</dt><dd class="tabular-nums">{{ d.users.total }}（启用 {{ d.users.active }}）</dd></div>
          <div class="flex justify-between"><dt class="text-muted">管理员 / 标注员 / 普通</dt>
            <dd class="tabular-nums">{{ d.users.by_role.admin ?? 0 }} / {{ d.users.by_role.editor ?? 0 }} / {{ d.users.by_role.user ?? 0 }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">收藏句组</dt><dd class="tabular-nums">{{ fmt(d.activity.favorites) }}</dd></div>
          <div class="flex justify-between"><dt class="text-muted">检索记录</dt><dd class="tabular-nums">{{ fmt(d.activity.searches) }}</dd></div>
        </dl>
      </section>
    </div>
  </div>
</template>
