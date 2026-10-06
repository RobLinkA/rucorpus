import type { LocationQuery, LocationQueryRaw } from 'vue-router'
import type { SearchParams } from '@/api/types'

const ints = (v: unknown) =>
  (Array.isArray(v) ? v : v == null ? [] : [v]).map(Number).filter((n) => Number.isInteger(n) && n > 0)

export function fromQuery(q: LocationQuery): Required<SearchParams> {
  return {
    q: typeof q.q === 'string' ? q.q : '',
    mode: q.mode === 'exact' ? 'exact' : 'morph',
    corpora: ints(q.corpora),
    works: ints(q.works),
    versions: ints(q.versions),
    values: ints(q.values),
    exclude: ints(q.exclude),
    // default: any value within one annotation group, every group must match
    logic: q.logic === 'and' ? 'and' : q.logic === 'or' ? 'or' : 'group',
    origin: q.origin === 'human' ? 'human' : q.origin === 'ai' ? 'ai' : 'all',
    page: Math.max(1, Number(q.page) || 1),
    size: [10, 20, 50, 100].includes(Number(q.size)) ? Number(q.size) : 20,
  }
}

export function toQuery(p: SearchParams): LocationQueryRaw {
  const out: LocationQueryRaw = {}
  if (p.q) out.q = p.q
  if (p.mode === 'exact') out.mode = 'exact'
  for (const k of ['corpora', 'works', 'versions', 'values', 'exclude'] as const) {
    const v = p[k]
    if (v?.length) out[k] = v.map(String)
  }
  if (p.values?.length && p.logic && p.logic !== 'group') out.logic = p.logic
  if (p.origin && p.origin !== 'all') out.origin = p.origin
  if (p.page && p.page > 1) out.page = String(p.page)
  if (p.size && p.size !== 20) out.size = String(p.size)
  return out
}

export function hasCondition(p: SearchParams) {
  return !!(p.q?.trim() || p.values?.length || p.works?.length || p.versions?.length || p.corpora?.length
    || (p.origin && p.origin !== 'all'))
}
