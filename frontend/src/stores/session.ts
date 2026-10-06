import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { User } from '@/api/types'

export const useSession = defineStore('session', () => {
  const user = ref<User | null>(null)
  const ready = ref(false)
  let loading: Promise<void> | null = null

  function load() {
    loading ??= api.get<{ user: User | null }>('/auth/session').then((r) => {
      user.value = r.user
      ready.value = true
    }).catch(() => { ready.value = true })
    return loading
  }

  async function login(username: string, password: string) {
    const r = await api.post<{ user: User }>('/auth/login', { username, password })
    // the session cookie rotated the CSRF token; refresh it
    loading = null
    await load()
    user.value = r.user
  }

  async function logout() {
    await api.post('/auth/logout')
    user.value = null
    loading = null
    await load()
  }

  return {
    user, ready, load, login, logout,
    loggedIn: computed(() => !!user.value),
    canEdit: computed(() => !!user.value?.can_edit),
    isAdmin: computed(() => !!user.value?.is_admin),
  }
})
