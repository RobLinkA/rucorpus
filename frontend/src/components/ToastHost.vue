<script setup lang="ts">
import { CheckCircle2, Info, XCircle } from 'lucide-vue-next'
import { useToast } from '@/stores/toast'

const toast = useToast()
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-6 z-[100] flex flex-col items-center gap-2 px-4">
    <TransitionGroup name="pop">
      <div v-for="t in toast.items" :key="t.id" role="status"
           class="pointer-events-auto flex max-w-md items-start gap-2 rounded-xl border border-line bg-surface px-4 py-2.5 text-sm shadow-card">
        <CheckCircle2 v-if="t.kind === 'ok'" class="mt-0.5 size-4 shrink-0 text-ok" />
        <XCircle v-else-if="t.kind === 'error'" class="mt-0.5 size-4 shrink-0 text-seal" />
        <Info v-else class="mt-0.5 size-4 shrink-0 text-accent" />
        <span>{{ t.text }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>
