<script setup lang="ts">
import { Eye, EyeOff, Plus, Settings2, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api/client'
import Modal from '@/components/ui/Modal.vue'
import { useMeta } from '@/stores/meta'
import { useToast } from '@/stores/toast'

interface C { id: number; name: string; description: string; source_lang: string; target_lang: string; status: string; sort_order: number }
interface DashCorpus { id: number; works: number; segments: number; annotations: number }

const toast = useToast()
const meta = useMeta()
const router = useRouter()
const list = ref<C[]>([])
const stats = ref<Record<number, DashCorpus>>({})
const creating = ref(false)
const form = ref({ name: '', description: '', source_lang: 'ru', target_lang: 'zh', status: 'hidden', sort_order: 0 })
const deleting = ref<C | null>(null)
const confirmName = ref('')

async function load() {
  list.value = await api.get<C[]>('/manage/corpora')
  const d = await api.get<{ corpora: DashCorpus[] }>('/manage/dashboard')
  stats.value = Object.fromEntries(d.corpora.map((c) => [c.id, c]))
}
onMounted(load)

async function toggle(c: C) {
  try {
    await api.put(`/manage/corpora/${c.id}`, { ...c, status: c.status === 'published' ? 'hidden' : 'published' })
    toast.ok(c.status === 'published' ? `已下架“${c.name}”` : `已发布“${c.name}”`)
    await load(); meta.load(true)
  } catch (e) { toast.error(e) }
}
async function create() {
  try {
    const c = await api.post<C>('/manage/corpora', { ...form.value, sort_order: list.value.length })
    creating.value = false
    meta.load(true)
    router.push({ name: 'admin-corpus', params: { id: c.id } })
  } catch (e) { toast.error(e) }
}
async function remove() {
  if (!deleting.value) return
  try {
    await api.del(`/manage/corpora/${deleting.value.id}`, { confirm: confirmName.value })
    toast.ok('已删除')
    deleting.value = null
    await load(); meta.load(true)
  } catch (e) { toast.error(e) }
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3">
      <h1 class="text-2xl font-semibold">语料库与标注体系</h1>
      <button class="btn-primary ml-auto" @click="creating = true"><Plus class="size-4" />新建语料库</button>
    </div>
    <p class="mt-1 text-sm text-muted">下架后前台不可见，数据保留；删除将级联删除全部作品、句对与标注，不可恢复。</p>

    <div class="card mt-5 overflow-x-auto">
      <table class="w-full text-sm">
        <thead class="border-b border-line text-left text-[13px] text-muted">
          <tr><th class="px-4 py-2.5 font-medium">名称</th><th class="px-4 py-2.5 font-medium">语言</th>
            <th class="px-4 py-2.5 text-right font-medium">作品</th><th class="px-4 py-2.5 text-right font-medium">句对</th>
            <th class="px-4 py-2.5 text-right font-medium">标注</th><th class="px-4 py-2.5 font-medium">状态</th><th /></tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="c in list" :key="c.id" class="hover:bg-surface-2/50">
            <td class="px-4 py-3">
              <RouterLink :to="{ name: 'admin-corpus', params: { id: c.id } }" class="font-medium hover:text-accent">{{ c.name }}</RouterLink>
              <div class="max-w-md truncate text-xs text-muted">{{ c.description }}</div>
            </td>
            <td class="px-4 py-3 text-ink-2">{{ c.source_lang }} → {{ c.target_lang }}</td>
            <td class="px-4 py-3 text-right tabular-nums">{{ stats[c.id]?.works ?? '—' }}</td>
            <td class="px-4 py-3 text-right tabular-nums">{{ stats[c.id]?.segments.toLocaleString() ?? '—' }}</td>
            <td class="px-4 py-3 text-right tabular-nums">{{ stats[c.id]?.annotations.toLocaleString() ?? '—' }}</td>
            <td class="px-4 py-3"><span class="tag" :class="c.status === 'hidden' && 'tag-seal'">{{ c.status === 'hidden' ? '已下架' : '已发布' }}</span></td>
            <td class="px-2 py-3">
              <div class="flex justify-end">
                <button class="btn-icon size-8" :title="c.status === 'published' ? '下架' : '发布'" @click="toggle(c)">
                  <EyeOff v-if="c.status === 'published'" class="size-4" /><Eye v-else class="size-4" />
                </button>
                <RouterLink :to="{ name: 'admin-corpus', params: { id: c.id } }" class="btn-icon size-8" title="管理"><Settings2 class="size-4" /></RouterLink>
                <button class="btn-icon size-8 hover:text-seal" title="删除" @click="deleting = c; confirmName = ''"><Trash2 class="size-4" /></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal v-model="creating" title="新建语料库">
      <form id="cf" class="space-y-3" @submit.prevent="create">
        <div><label class="label" for="cn">名称</label><input id="cn" v-model="form.name" class="input" required /></div>
        <div><label class="label" for="cd">说明</label><textarea id="cd" v-model="form.description" class="input h-auto py-2" rows="3" /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label" for="sl">原文语言代码</label><input id="sl" v-model="form.source_lang" class="input" placeholder="ru" required /></div>
          <div><label class="label" for="tl">译文语言代码</label><input id="tl" v-model="form.target_lang" class="input" placeholder="zh" required /></div>
        </div>
        <p class="text-xs text-muted">新语料库默认为“已下架”，导入数据并检查无误后再发布。</p>
      </form>
      <template #footer><button class="btn-ghost" @click="creating = false">取消</button><button form="cf" class="btn-primary">创建</button></template>
    </Modal>

    <Modal :model-value="!!deleting" title="删除语料库" @update:model-value="(v) => !v && (deleting = null)">
      <p class="text-sm">将永久删除“<b>{{ deleting?.name }}</b>”及其全部作品、句对、标注和相关收藏。此操作不可恢复。</p>
      <label class="label mt-4" for="dc">请输入语料库名称确认</label>
      <input id="dc" v-model="confirmName" class="input" :placeholder="deleting?.name" />
      <template #footer>
        <button class="btn-ghost" @click="deleting = null">取消</button>
        <button class="btn-danger" :disabled="confirmName !== deleting?.name" @click="remove">永久删除</button>
      </template>
    </Modal>
  </div>
</template>
