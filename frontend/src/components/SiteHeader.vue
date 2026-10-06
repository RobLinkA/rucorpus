<script setup lang="ts">
import { site } from '@/site'
import { onKeyStroke } from '@vueuse/core'
import { ChevronDown, History, LayoutDashboard, LogOut, Menu, Moon, Star, Sun, UserRound, X } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Dropdown from '@/components/ui/Dropdown.vue'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const session = useSession()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const mobileOpen = ref(false)
const dark = ref(document.documentElement.classList.contains('dark'))

watch(() => route.fullPath, () => { mobileOpen.value = false })

// "/" focuses the search box from anywhere
onKeyStroke('/', (e) => {
  const t = e.target as HTMLElement
  if (t.closest('input, textarea, select, [contenteditable]')) return
  const el = document.querySelector('main input[type=search]') as HTMLInputElement | null
  if (el) { e.preventDefault(); el.focus() }
})

const nav = [
  { to: '/search', label: '高级检索', match: ['search'] },
  { to: '/read', label: '平行阅读', match: ['read', 'group'] },
  { to: '/help', label: '使用说明', match: ['help'] },
  { to: '/citation', label: '引用规范', match: ['citation'] },
]


function toggleTheme() {
  dark.value = !dark.value
  document.documentElement.classList.toggle('dark', dark.value)
  try { localStorage.setItem('theme', dark.value ? 'dark' : 'light') } catch { /* private mode */ }
}

async function logout() {
  await session.logout()
  toast.ok('已退出登录')
  if (route.matched.some((r) => r.meta.auth || r.meta.editor)) router.push('/')
}
</script>

<template>
  <header class="sticky top-0 z-40 border-b border-line bg-bg/70 backdrop-blur-xl">
    <div class="mx-auto flex h-14 max-w-[1440px] items-center gap-3 px-4 sm:px-6">
      <RouterLink to="/" class="group flex shrink-0 items-center gap-2.5" aria-label="首页">
        <span class="site-logo size-8" aria-hidden="true" />
        <span class="hidden flex-col leading-none sm:flex md:hidden lg:flex">
          <span class="font-display text-[16px] font-semibold tracking-tight">{{ site.name }}</span>
          <span class="mt-1 text-[9px] tracking-[0.01em] text-muted">{{ site.subtitle }}</span>
        </span>
      </RouterLink>

      <nav class="ml-2 hidden shrink-0 items-center md:flex xl:ml-4">
        <RouterLink v-for="n in nav" :key="n.to" :to="n.to"
                    class="relative flex h-14 items-center gap-1.5 px-2.5 text-[13.5px] whitespace-nowrap text-ink-2 transition hover:text-ink xl:px-3"
                    :class="n.match.includes(String(route.name)) && '!text-ink'">
          {{ n.label }}
          <span v-if="n.match.includes(String(route.name))"
                class="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-accent" />
        </RouterLink>
      </nav>

      <div class="ml-auto" />

      <button class="btn-icon" :aria-label="dark ? '浅色模式' : '深色模式'" :title="dark ? '浅色模式' : '深色模式'" @click="toggleTheme">
        <Sun v-if="dark" class="size-[18px]" /><Moon v-else class="size-[18px]" />
      </button>

      <template v-if="session.ready">
        <Dropdown v-if="session.user" align="right" class="hidden md:block">
          <template #trigger>
            <button class="btn-ghost h-9 gap-2 pr-2 pl-1.5">
              <span class="grid size-7 place-items-center rounded-md bg-accent-soft text-[12px] font-semibold text-accent">
                {{ session.user.display_name.slice(0, 1).toUpperCase() }}
              </span>
              <span class="max-w-28 truncate">{{ session.user.display_name }}</span>
              <ChevronDown class="size-4 text-muted" />
            </button>
          </template>
          <div class="px-2.5 pt-1.5 pb-2 text-[11px] text-muted">{{ ({ admin: '管理员', editor: '标注员', user: '普通用户' } as Record<string, string>)[session.user.role] }}</div>
          <RouterLink to="/me/favorites" class="menu-item"><Star class="size-4" />我的收藏</RouterLink>
          <RouterLink to="/me/history" class="menu-item"><History class="size-4" />检索历史</RouterLink>
          <RouterLink to="/me" class="menu-item"><UserRound class="size-4" />个人设置</RouterLink>
          <template v-if="session.canEdit">
            <div class="my-1 border-t border-line" />
            <RouterLink to="/admin" class="menu-item"><LayoutDashboard class="size-4" />管理后台</RouterLink>
          </template>
          <div class="my-1 border-t border-line" />
          <button class="menu-item w-full" @click="logout"><LogOut class="size-4" />退出登录</button>
        </Dropdown>
        <RouterLink v-else-if="route.name !== 'login'" :to="{ name: 'login', query: { next: route.fullPath } }" class="btn-outline hidden md:inline-flex">登录</RouterLink>
      </template>

      <button class="btn-icon md:hidden" aria-label="菜单" @click="mobileOpen = !mobileOpen">
        <X v-if="mobileOpen" class="size-5" /><Menu v-else class="size-5" />
      </button>
    </div>

    <Transition name="fade">
      <div v-if="mobileOpen" class="border-t border-line bg-surface/95 px-4 py-3 backdrop-blur-xl md:hidden">
        <nav class="grid gap-1">
          <RouterLink v-for="n in nav" :key="n.to" :to="n.to" class="menu-item">{{ n.label }}</RouterLink>
          <div class="my-1 border-t border-line" />
          <template v-if="session.user">
            <RouterLink to="/me/favorites" class="menu-item"><Star class="size-4" />我的收藏</RouterLink>
            <RouterLink to="/me/history" class="menu-item"><History class="size-4" />检索历史</RouterLink>
            <RouterLink to="/me" class="menu-item"><UserRound class="size-4" />个人设置</RouterLink>
            <RouterLink v-if="session.canEdit" to="/admin" class="menu-item"><LayoutDashboard class="size-4" />管理后台</RouterLink>
            <button class="menu-item" @click="logout"><LogOut class="size-4" />退出登录</button>
          </template>
          <RouterLink v-else to="/login" class="menu-item"><UserRound class="size-4" />登录</RouterLink>
        </nav>
      </div>
    </Transition>
  </header>
</template>
