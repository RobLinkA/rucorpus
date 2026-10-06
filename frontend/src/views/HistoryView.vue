<script setup lang="ts">
import { History, Pencil, Pin, PinOff, Play, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import type { Paged, SearchParams } from '@/api/types'
import { toQuery } from '@/composables/searchQuery'
import { useToast } from '@/stores/toast'

interface Item { id: number; params: SearchParams; summary: string; result_count: number; name: string; pinned: boolean; created_at: string }

const router = useRouter()
const toast = useToast()
const data = ref<Paged<Item> | null>(null)
const page = ref(1)
const renaming = ref<number | null>(null)
const draft = ref('')

async function load() { data.value = await api.get<Paged<Item>>('/me/history', { page: page.value, size: 50 }) }
onMounted(load)

const rerun = (h: Item) => router.push({ name: 'search', query: toQuery(h.params) })
async function pin(h: Item) { await api.patch(`/me/history/${h.id}`, { pinned: !h.pinned }); load() }
async function remove(h: Item) { await api.del(`/me/history/${h.id}`); load() }
async function rename(h: Item) {
  await api.patch(`/me/history/${h.id}`, { name: draft.value })
  renaming.value = null
  load()
}
async function clear() {
  if (!confirm('清空所有未置顶的检索历史？')) return
  const r = await api.del<{ deleted: number }>('/me/history')
  toast.ok(`已清除 ${r.deleted} 条`)
  load()
}
const fmt = (s: string) => new Date(s).toLocaleString('zh-CN', { dateStyle: 'short', timeStyle: 'short' })
</script>

<template>
  <div class="mx-auto max-w-4xl px-4 py-8 sm:px-6">
    <div class="flex items-end gap-3">
      <div>
        <h1 class="font-display text-3xl font-semibold">检索历史</h1>
        <p class="mt-1 text-sm text-muted">登录后每次检索自动保存。置顶并命名常用检索，随时一键复用。</p>
      </div>
      <button v-if="data?.total" class="btn-ghost ml-auto" @click="clear"><Trash2 class="size-4" />清空</button>
    </div>
    <div v-if="data && !data.total" class="card mt-6 px-6 py-12 text-center">
      <History class="mx-auto size-8 text-muted" />
      <p class="mt-3 text-ink-2">还没有检索记录</p>
    </div>
    <ul v-else class="card mt-6 divide-y divide-line">
      <li v-for="h in data?.results ?? []" :key="h.id" class="group flex items-center gap-3 px-4 py-3">
        <Pin v-if="h.pinned" class="size-4 shrink-0 text-seal" />
        <div class="min-w-0 flex-1">
          <form v-if="renaming === h.id" class="flex gap-2" @submit.prevent="rename(h)">
            <input v-model="draft" class="input h-8" placeholder="为这次检索命名" autofocus />
            <button class="btn-primary btn-sm">保存</button>
            <button type="button" class="btn-ghost btn-sm" @click="renaming = null">取消</button>
          </form>
          <button v-else class="block w-full truncate text-left" @click="rerun(h)">
            <span v-if="h.name" class="font-medium">{{ h.name }}<span class="mx-2 text-muted">·</span></span>
            <span class="font-display">{{ h.summary || '（仅筛选条件）' }}</span>
          </button>
          <div class="mt-0.5 text-xs text-muted tabular-nums">{{ fmt(h.created_at) }} · {{ h.result_count.toLocaleString() }} 个结果</div>
        </div>
        <div class="flex shrink-0 opacity-70 group-hover:opacity-100">
          <button class="btn-icon size-8" title="重新检索" aria-label="重新检索" @click="rerun(h)"><Play class="size-4" /></button>
          <button class="btn-icon size-8" title="命名" aria-label="命名" @click="renaming = h.id; draft = h.name"><Pencil class="size-4" /></button>
          <button class="btn-icon size-8" :title="h.pinned ? '取消置顶' : '置顶'" :aria-label="h.pinned ? '取消置顶' : '置顶'" @click="pin(h)">
            <PinOff v-if="h.pinned" class="size-4" /><Pin v-else class="size-4" />
          </button>
          <button class="btn-icon size-8" title="删除" aria-label="删除" @click="remove(h)"><Trash2 class="size-4" /></button>
        </div>
      </li>
    </ul>
  </div>
</template>
