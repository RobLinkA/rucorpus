<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import Pager from '@/components/ui/Pager.vue'

interface Log { id: number; user: string | null; action: string; target: string; summary: string; created_at: string }
const data = ref<{ total: number; results: Log[] } | null>(null)
const page = ref(1)
const action = ref('')
const ACTIONS: Record<string, string> = {
  annotate: '编辑标注', 'annotate.batch': '批量标注', 'segment.edit': '修改文本', 'segment.split': '拆分句对',
  'import.annotations': '导入标注', 'import.corpus': '导入语料', 'corpus.create': '新建语料库', 'corpus.update': '修改语料库',
  'corpus.delete': '删除语料库', 'version.create': '新建版本', 'version.update': '修改版本', 'version.delete': '删除版本',
  'work.create': '新建作品', 'work.update': '修改作品', 'work.delete': '删除作品', 'scheme.group.create': '新建标注组',
  'scheme.group.update': '修改标注组', 'scheme.group.delete': '删除标注组', 'scheme.value.create': '新建标注项',
  'scheme.value.update': '修改标注项', 'scheme.value.delete': '删除标注项', 'scheme.value.merge': '合并标注项',
  'user.create': '新建用户', 'user.update': '修改用户', 'user.delete': '删除用户',
}
async function load() { data.value = await api.get('/manage/audit', { page: page.value, size: 50, action: action.value }) }
onMounted(load)
watch([page, action], load)
const time = (s: string) => new Date(s).toLocaleString('zh-CN')
</script>

<template>
  <div>
    <div class="flex items-center gap-3">
      <h1 class="text-2xl font-semibold">操作日志</h1>
      <select v-model="action" class="input ml-auto w-44" aria-label="操作类型" @change="page = 1">
        <option value="">全部操作</option>
        <option v-for="(l, k) in ACTIONS" :key="k" :value="k">{{ l }}</option>
      </select>
    </div>
    <div class="card mt-5 overflow-x-auto">
      <table class="w-full min-w-[720px] text-sm">
        <tbody class="divide-y divide-line">
          <tr v-for="l in data?.results ?? []" :key="l.id">
            <td class="w-44 px-4 py-2.5 text-xs text-muted tabular-nums">{{ time(l.created_at) }}</td>
            <td class="w-24 px-2 py-2.5 text-ink-2">{{ l.user ?? '—' }}</td>
            <td class="w-28 px-2 py-2.5"><span class="tag">{{ ACTIONS[l.action] ?? l.action }}</span></td>
            <td class="px-2 py-2.5">{{ l.summary }}</td>
          </tr>
          <tr v-if="data && !data.results.length"><td class="px-4 py-10 text-center text-muted">暂无记录</td></tr>
        </tbody>
      </table>
    </div>
    <Pager v-if="data" class="mt-5" :page="page" :total="data.total" :size="50" @go="(p) => (page = p)" />
  </div>
</template>
