<script setup lang="ts">
import { LoaderCircle } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSession } from '@/stores/session'

const session = useSession()
const router = useRouter()
const route = useRoute()
const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await session.login(username.value, password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/'
    router.replace(next)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally { busy.value = false }
}
</script>

<template>
  <div class="mx-auto flex max-w-sm flex-col px-4 py-16 sm:py-24">
    <span class="site-logo mx-auto size-12" aria-hidden="true" />
    <h1 class="mt-4 text-center font-display text-2xl font-semibold">登录</h1>
    <p class="mt-1 text-center text-sm text-muted">账号由管理员创建。登录后可收藏句组、保存检索历史。</p>
    <form class="card mt-8 space-y-4 p-6" @submit.prevent="submit">
      <div>
        <label class="label" for="u">用户名</label>
        <input id="u" v-model="username" class="input h-10" autocomplete="username" required autofocus />
      </div>
      <div>
        <label class="label" for="p">密码</label>
        <input id="p" v-model="password" type="password" class="input h-10" autocomplete="current-password" required />
      </div>
      <p v-if="error" class="text-sm text-seal" role="alert">{{ error }}</p>
      <button class="btn-primary h-10 w-full" :disabled="busy"><LoaderCircle v-if="busy" class="size-4 animate-spin" />登录</button>
    </form>
  </div>
</template>
