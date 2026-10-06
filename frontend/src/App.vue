<script setup lang="ts">
import { site } from '@/site'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SiteHeader from '@/components/SiteHeader.vue'
import ToastHost from '@/components/ToastHost.vue'
import { useMeta } from '@/stores/meta'

const route = useRoute()
const meta = useMeta()
meta.load()
const isAdmin = computed(() => route.path.startsWith('/admin'))
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <SiteHeader />
    <main class="flex-1">
      <RouterView />
    </main>
    <footer v-if="!isAdmin" class="mt-16 border-t border-line bg-surface">
      <div class="mx-auto flex max-w-[1440px] flex-wrap items-center gap-x-8 gap-y-3 px-4 py-8 text-[13px] text-muted sm:px-6">
        <div class="flex items-center gap-2.5">
          <span class="site-logo size-7" aria-hidden="true" />
          <span class="font-display text-[15px] font-semibold text-ink">{{ site.name }}</span>
        </div>
        <span>{{ site.subtitle }}</span>
        <nav aria-label="页脚导航" class="ml-auto flex flex-wrap gap-x-5 gap-y-2">
          <RouterLink to="/citation" class="muted-link">引用规范</RouterLink>
          <RouterLink to="/help" class="muted-link">使用说明</RouterLink>
          <RouterLink to="/help#sources" class="muted-link">版本与出处</RouterLink>
          <RouterLink to="/help#ai" class="muted-link">AI 标注</RouterLink>
        </nav>
      </div>
    </footer>
    <ToastHost />
  </div>
</template>
