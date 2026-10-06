<script setup lang="ts">
import { Star } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '@/api/client'
import { useSession } from '@/stores/session'
import { useToast } from '@/stores/toast'

const props = defineProps<{ groupId: number; small?: boolean; showLabel?: boolean }>()
const favorite = defineModel<boolean>({ default: false })
const session = useSession()
const toast = useToast()
const router = useRouter()
const route = useRoute()
const busy = ref(false)

async function toggle() {
  if (busy.value) return
  if (!session.loggedIn) {
    toast.info('登录后可收藏句组')
    router.push({ name: 'login', query: { next: route.fullPath } })
    return
  }
  busy.value = true
  const nextFavorite = !favorite.value
  try {
    if (nextFavorite) await api.post('/me/favorites', { group_id: props.groupId })
    else await api.del(`/me/favorites/by-group/${props.groupId}`)
    favorite.value = nextFavorite
    toast.ok(nextFavorite ? '已收藏' : '已取消收藏')
  } catch (e) { toast.error(e) } finally { busy.value = false }
}
</script>

<template>
  <button type="button" :class="showLabel ? 'menu-item w-full disabled:cursor-wait disabled:opacity-60' : small ? 'btn-icon size-8' : 'btn-icon'"
          :disabled="busy" :aria-pressed="favorite" :title="favorite ? '取消收藏' : '收藏'"
          :aria-label="showLabel ? undefined : favorite ? '取消收藏' : '收藏'" @click.stop="toggle">
    <Star class="shrink-0 transition" :class="[showLabel ? 'size-4' : 'size-[18px]', favorite ? 'fill-seal text-seal' : '']" aria-hidden="true" />
    <span v-if="showLabel">{{ favorite ? '已收藏' : '收藏此句组' }}</span>
  </button>
</template>
