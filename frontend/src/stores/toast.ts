import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Toast { id: number; kind: 'ok' | 'error' | 'info'; text: string }

export const useToast = defineStore('toast', () => {
  const items = ref<Toast[]>([])
  let seq = 0
  function push(kind: Toast['kind'], text: string, ms = 3200) {
    const id = ++seq
    items.value.push({ id, kind, text })
    setTimeout(() => { items.value = items.value.filter((t) => t.id !== id) }, ms)
  }
  return {
    items,
    ok: (t: string) => push('ok', t),
    info: (t: string) => push('info', t),
    error: (e: unknown) => push('error', e instanceof Error ? e.message : String(e), 5000),
  }
})
