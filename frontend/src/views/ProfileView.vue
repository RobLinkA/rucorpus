<script setup lang="ts">
import { ref } from 'vue'
import { api } from '@/api/client'
import type { User } from '@/api/types'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const session = useSession()
const toast = useToast()
const display = ref(session.user?.display_name ?? '')
const institution = ref(session.user?.institution ?? '')
const oldPw = ref('')
const newPw = ref('')
const newPw2 = ref('')
const ROLE = { admin: '管理员', editor: '标注员', user: '普通用户' }

async function saveProfile() {
  try {
    const r = await api.put<{ user: User }>('/auth/profile', { display_name: display.value, institution: institution.value })
    session.user = r.user
    toast.ok('已保存')
  } catch (e) { toast.error(e) }
}
async function changePw() {
  if (newPw.value !== newPw2.value) return toast.error('两次输入的新密码不一致')
  try {
    await api.post('/auth/password', { old_password: oldPw.value, new_password: newPw.value })
    oldPw.value = newPw.value = newPw2.value = ''
    toast.ok('密码已修改')
  } catch (e) { toast.error(e) }
}
</script>

<template>
  <div class="mx-auto max-w-2xl px-4 py-8 sm:px-6">
    <h1 class="font-display text-3xl font-semibold">个人设置</h1>
    <p class="mt-1 text-sm text-muted">{{ session.user?.username }} · {{ session.user ? ROLE[session.user.role] : '' }}</p>
    <form class="card mt-6 space-y-4 p-5" @submit.prevent="saveProfile">
      <h2 class="font-semibold">基本信息</h2>
      <div><label class="label" for="dn">显示名称</label><input id="dn" v-model="display" class="input" /></div>
      <div><label class="label" for="ins">所属机构</label><input id="ins" v-model="institution" class="input" /></div>
      <button class="btn-primary">保存</button>
    </form>
    <form class="card mt-6 space-y-4 p-5" @submit.prevent="changePw">
      <h2 class="font-semibold">修改密码</h2>
      <div><label class="label" for="o">原密码</label><input id="o" v-model="oldPw" type="password" class="input" autocomplete="current-password" required /></div>
      <div class="grid gap-4 sm:grid-cols-2">
        <div><label class="label" for="n1">新密码</label><input id="n1" v-model="newPw" type="password" class="input" autocomplete="new-password" minlength="6" required /></div>
        <div><label class="label" for="n2">确认新密码</label><input id="n2" v-model="newPw2" type="password" class="input" autocomplete="new-password" minlength="6" required /></div>
      </div>
      <button class="btn-primary">修改密码</button>
    </form>
  </div>
</template>
