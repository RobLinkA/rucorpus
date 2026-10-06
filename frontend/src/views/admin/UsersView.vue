<script setup lang="ts">
import { KeyRound, Pencil, Plus, Search, Trash2 } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { api } from '@/api/client'
import Modal from '@/components/ui/Modal.vue'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

interface U { id: number; username: string; display_name: string; institution: string; email: string; role: string
  is_active: boolean; date_joined: string; last_login: string | null; favorites: number; searches: number }

const toast = useToast()
const session = useSession()
const users = ref<U[]>([])
const q = ref('')
const form = ref<(Partial<U> & { password?: string }) | null>(null)
const pw = ref<{ user: U; password: string } | null>(null)
const ROLE: Record<string, string> = { admin: '管理员', editor: '标注员', user: '普通用户' }

async function load() { users.value = await api.get<U[]>('/manage/users', { q: q.value }) }
onMounted(load)

function body(u: Partial<U> & { password?: string }) {
  return { username: u.username, display_name: u.display_name ?? '', institution: u.institution ?? '', email: u.email ?? '',
    role: u.role ?? 'user', is_active: u.is_active ?? true, password: u.password || null }
}
async function save() {
  const u = form.value!
  try {
    if (u.id) await api.put(`/manage/users/${u.id}`, body(u))
    else await api.post('/manage/users', body(u))
    form.value = null
    toast.ok('已保存')
    load()
  } catch (e) { toast.error(e) }
}
async function resetPw() {
  const p = pw.value!
  try {
    await api.put(`/manage/users/${p.user.id}`, { ...body(p.user), password: p.password })
    pw.value = null
    toast.ok('密码已重置')
  } catch (e) { toast.error(e) }
}
async function toggleActive(u: U) {
  try { await api.put(`/manage/users/${u.id}`, { ...body(u), is_active: !u.is_active }); load() } catch (e) { toast.error(e) }
}
async function remove(u: U) {
  if (!confirm(`删除用户“${u.username}”？其收藏和检索历史将一并删除。`)) return
  try { await api.del(`/manage/users/${u.id}`); toast.ok('已删除'); load() } catch (e) { toast.error(e) }
}
const date = (s: string | null) => (s ? new Date(s).toLocaleDateString('zh-CN') : '—')
</script>

<template>
  <div>
    <div class="flex flex-wrap items-center gap-3">
      <h1 class="text-2xl font-semibold">用户</h1>
      <form class="relative ml-auto w-60" @submit.prevent="load">
        <Search class="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
        <input v-model="q" type="search" class="input pl-9" placeholder="用户名 / 名称 / 机构" />
      </form>
      <button class="btn-primary" @click="form = { role: 'user', is_active: true }"><Plus class="size-4" />新建用户</button>
    </div>
    <p class="mt-1 text-sm text-muted">系统不开放注册。标注员可编辑句对与标注、导入标注；管理员拥有全部权限。</p>

    <div class="card mt-5 overflow-x-auto">
      <table class="w-full min-w-[760px] text-sm">
        <thead class="border-b border-line text-left text-[13px] text-muted">
          <tr><th class="px-4 py-2.5 font-medium">用户</th><th class="px-2 py-2.5 font-medium">角色</th><th class="px-2 py-2.5 font-medium">机构</th>
            <th class="px-2 py-2.5 text-right font-medium">收藏 / 检索</th><th class="px-2 py-2.5 font-medium">最近登录</th><th class="px-2 py-2.5 font-medium">状态</th><th /></tr>
        </thead>
        <tbody class="divide-y divide-line">
          <tr v-for="u in users" :key="u.id" :class="!u.is_active && 'opacity-55'">
            <td class="px-4 py-2.5"><div class="font-medium">{{ u.display_name }}</div><div class="text-xs text-muted">{{ u.username }}</div></td>
            <td class="px-2 py-2.5"><span class="tag" :class="u.role === 'admin' && 'tag-seal'">{{ ROLE[u.role] }}</span></td>
            <td class="max-w-48 truncate px-2 py-2.5 text-ink-2">{{ u.institution || '—' }}</td>
            <td class="px-2 py-2.5 text-right text-ink-2 tabular-nums">{{ u.favorites }} / {{ u.searches }}</td>
            <td class="px-2 py-2.5 text-ink-2 tabular-nums">{{ date(u.last_login) }}</td>
            <td class="px-2 py-2.5">
              <button class="text-[13px] hover:underline" :class="u.is_active ? 'text-ok' : 'text-muted'" :disabled="u.id === session.user?.id"
                      @click="toggleActive(u)">{{ u.is_active ? '启用' : '已停用' }}</button>
            </td>
            <td class="px-2 py-2">
              <div class="flex justify-end">
                <button class="btn-icon size-8" title="编辑" @click="form = { ...u }"><Pencil class="size-4" /></button>
                <button class="btn-icon size-8" title="重置密码" @click="pw = { user: u, password: '' }"><KeyRound class="size-4" /></button>
                <button class="btn-icon size-8 hover:text-seal" title="删除" :disabled="u.id === session.user?.id" @click="remove(u)"><Trash2 class="size-4" /></button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <Modal :model-value="!!form" :title="form?.id ? '编辑用户' : '新建用户'" @update:model-value="(o) => !o && (form = null)">
      <form v-if="form" id="uf" class="space-y-3" @submit.prevent="save">
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label" for="un">用户名</label><input id="un" v-model="form.username" class="input" :disabled="!!form.id" required autocomplete="off" /></div>
          <div><label class="label" for="ur">角色</label>
            <select id="ur" v-model="form.role" class="input"><option v-for="(l, k) in ROLE" :key="k" :value="k">{{ l }}</option></select></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="label" for="ud">显示名称</label><input id="ud" v-model="form.display_name" class="input" /></div>
          <div><label class="label" for="ui">机构</label><input id="ui" v-model="form.institution" class="input" /></div>
        </div>
        <div><label class="label" for="ue">邮箱</label><input id="ue" v-model="form.email" type="email" class="input" /></div>
        <div v-if="!form.id"><label class="label" for="up">初始密码</label><input id="up" v-model="form.password" type="password" class="input" minlength="6" required autocomplete="new-password" /></div>
        <label class="flex items-center gap-2 text-sm"><input v-model="form.is_active" type="checkbox" class="accent-[var(--accent)]" />启用</label>
      </form>
      <template #footer><button class="btn-ghost" @click="form = null">取消</button><button form="uf" class="btn-primary">保存</button></template>
    </Modal>

    <Modal :model-value="!!pw" :title="`重置密码 · ${pw?.user.username}`" @update:model-value="(o) => !o && (pw = null)">
      <form v-if="pw" id="pf" @submit.prevent="resetPw">
        <label class="label" for="np">新密码</label>
        <input id="np" v-model="pw.password" type="password" class="input" minlength="6" required autocomplete="new-password" />
      </form>
      <template #footer><button class="btn-ghost" @click="pw = null">取消</button><button form="pf" class="btn-primary">重置</button></template>
    </Modal>
  </div>
</template>
