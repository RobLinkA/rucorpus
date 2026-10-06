import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/api/client'
import type { AnnotationGroup, AnnotationValue, Corpus, Version, Work } from '@/api/types'

/** Corpus metadata used everywhere for labels, scopes and filters. */
export const useMeta = defineStore('meta', () => {
  const corpora = ref<Corpus[]>([])
  const loaded = ref(false)
  let pending: Promise<void> | null = null

  function load(force = false) {
    if (force) pending = null
    pending ??= api.get<{ corpora: Corpus[] }>('/meta').then((r) => {
      corpora.value = r.corpora
      loaded.value = true
    })
    return pending
  }

  const corpusById = computed(() => new Map(corpora.value.map((c) => [c.id, c])))
  const workById = computed(() => {
    const m = new Map<number, Work & { corpus_id: number }>()
    corpora.value.forEach((c) => c.works.forEach((w) => m.set(w.id, { ...w, corpus_id: c.id })))
    return m
  })
  const versionById = computed(() => {
    const m = new Map<number, Version & { corpus_id: number }>()
    corpora.value.forEach((c) => c.versions.forEach((v) => m.set(v.id, { ...v, corpus_id: c.id })))
    return m
  })
  const valueById = computed(() => {
    const m = new Map<number, AnnotationValue & { group: AnnotationGroup; corpus_id: number }>()
    corpora.value.forEach((c) => c.annotation_groups.forEach((g) =>
      g.values.forEach((v) => m.set(v.id, { ...v, group: g, corpus_id: c.id }))))
    return m
  })

  // each annotation group gets a stable colour (by its order within the corpus)
  const PALETTE = ['#2f7d73', '#3b5f9a', '#8a4f7d', '#b7832a', '#b4441c', '#5c7a3a', '#7a5c3e']
  const groupColor = computed(() => {
    const m = new Map<number, string>()
    corpora.value.forEach((c) => c.annotation_groups.forEach((g, i) => m.set(g.id, PALETTE[i % PALETTE.length])))
    return m
  })

  function workTitle(id: number) {
    const w = workById.value.get(id)
    if (!w) return ''
    return w.title_target && w.title_target !== w.title_source ? `${w.title_target}` : w.title_source
  }

  return { corpora, loaded, load, corpusById, workById, versionById, valueById, groupColor, workTitle }
})
