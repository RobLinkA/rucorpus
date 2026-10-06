<script setup lang="ts">
import { ArrowLeftRight, Gauge, Library, ScrollText, TextQuote, Users } from 'lucide-vue-next'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSession } from '@/stores/session'

const session = useSession()
const route = useRoute()
const items = computed(() => [
  { to: '/admin', label: '概览', icon: Gauge, exact: true },
  { to: '/admin/corpora', label: '语料库与标注体系', icon: Library, admin: true },
  { to: '/admin/segments', label: '句对与标注', icon: TextQuote },
  { to: '/admin/transfer', label: '导入导出', icon: ArrowLeftRight },
  { to: '/admin/users', label: '用户', icon: Users, admin: true },
  { to: '/admin/audit', label: '操作日志', icon: ScrollText, admin: true },
].filter((i) => !i.admin || session.isAdmin))
const active = (i: { to: string; exact?: boolean }) => (i.exact ? route.path === i.to : route.path.startsWith(i.to))
</script>

<template>
  <div class="mx-auto flex max-w-[1500px] flex-col gap-6 px-4 py-6 sm:px-6 md:flex-row">
    <aside class="shrink-0 md:w-56">
      <div class="card p-2 md:sticky md:top-20">
        <div class="hidden px-2.5 pt-1.5 pb-2.5 md:block">
          <div class="kicker">Console</div>
          <div class="mt-0.5 text-[13px] font-semibold">管理后台</div>
        </div>
        <nav class="flex gap-1 overflow-x-auto md:flex-col">
          <RouterLink v-for="i in items" :key="i.to" :to="i.to"
                      class="relative flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-[13.5px] transition"
                      :class="active(i) ? 'bg-accent-soft text-accent' : 'text-ink-2 hover:bg-surface-3/60 hover:text-ink'">
            <span v-if="active(i)" class="absolute inset-y-1.5 left-0 hidden w-0.5 rounded-full bg-accent md:block" />
            <component :is="i.icon" class="size-4" />{{ i.label }}
          </RouterLink>
        </nav>
      </div>
    </aside>
    <div class="min-w-0 flex-1"><RouterView /></div>
  </div>
</template>
