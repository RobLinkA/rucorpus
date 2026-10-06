<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '@/api/client'
import type { AiInfo, AnnotationGroup } from '@/api/types'
import Modal from '@/components/ui/Modal.vue'
import { useMeta } from '@/stores/meta'
import { useToast } from '@/stores/toast'

const props = defineProps<{ segmentId: number; corpusId: number; values: number[]; context?: string; ai?: Record<number, AiInfo> }>()
const emit = defineEmits<{ saved: [values: number[], ai: Record<number, AiInfo>] }>()
const confirmAi = ref(false)
const open = defineModel<boolean>({ default: false })
const meta = useMeta()
const toast = useToast()
const selected = ref<Set<number>>(new Set())
const saving = ref(false)

watch(open, (o) => { if (o) selected.value = new Set(props.values) })
const groups = computed<AnnotationGroup[]>(() => meta.corpusById.get(props.corpusId)?.annotation_groups ?? [])

function toggle(g: AnnotationGroup, id: number) {
  const s = new Set(selected.value)
  if (s.has(id)) s.delete(id)
  else {
    if (g.widget === 'radio' || g.widget === 'select') g.values.forEach((v) => s.delete(v.id))
    s.add(id)
  }
  selected.value = s
}

async function save() {
  saving.value = true
  try {
    const r = await api.put<{ annotations: number[]; ai: Record<number, AiInfo> }>(`/segments/${props.segmentId}/annotations`,
      { values: [...selected.value], confirm_ai: confirmAi.value })
    emit('saved', r.annotations, r.ai)
    toast.ok('标注已保存')
    open.value = false
  } catch (e) { toast.error(e) } finally { saving.value = false }
}
</script>

<template>
  <Modal v-model="open" title="编辑标注" width="max-w-2xl">
    <p v-if="context" class="corpus-text mb-4 line-clamp-3 rounded-lg bg-surface-2 px-3 py-2 text-[15px]">{{ context }}</p>
    <div class="space-y-4">
      <section v-for="g in groups" :key="g.id">
        <h3 class="mb-2 flex items-baseline gap-2 text-[13px] font-semibold text-ink-2">
          {{ g.name }}
          <span v-if="g.widget === 'radio' || g.widget === 'select'" class="font-normal text-muted">单选</span>
        </h3>
        <div class="flex flex-wrap gap-1.5">
          <button v-for="v in g.values" :key="v.id" type="button" class="chip" :class="selected.has(v.id) && 'chip-on'"
                  :aria-pressed="selected.has(v.id)" @click="toggle(g, v.id)">
            <span v-if="ai?.[v.id]" class="text-[11px]" title="AI 标注">✦</span>{{ v.label }}</button>
        </div>
      </section>
      <p v-if="!groups.length" class="text-sm text-muted">该语料库尚未定义标注体系。</p>
    </div>
    <template #footer>
      <label v-if="ai && Object.keys(ai).length" class="mr-auto flex items-center gap-2 text-[13px] text-ink-2">
        <input v-model="confirmAi" type="checkbox" />将保留的 ✦ AI 标注确认为人工标注
      </label>
      <button class="btn-ghost" @click="open = false">取消</button>
      <button class="btn-primary" :disabled="saving" @click="save">保存</button>
    </template>
  </Modal>
</template>
