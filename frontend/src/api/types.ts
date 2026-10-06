export interface User {
  id: number
  username: string
  display_name: string
  role: 'admin' | 'editor' | 'user'
  institution: string
  can_edit: boolean
  is_admin: boolean
}

export interface AnnotationValue { id: number; label: string; usage: number; ai_usage: number; defined_in_legacy: boolean }
export interface AnnotationGroup {
  id: number; name: string; key: string; widget: string; description: string; values: AnnotationValue[]
}
export interface Version {
  id: number; kind: 'source' | 'translation'; lang: string; label: string; person: string
  bibliography: string; segments: number
}
export interface Work { id: number; title_source: string; title_target: string; author: string; groups: number }
export interface Corpus {
  id: number; name: string; description: string; source_lang: string; target_lang: string
  status: 'published' | 'hidden'
  versions: Version[]; works: Work[]; annotation_groups: AnnotationGroup[]
}

export type Span = [number, number]
export interface AiInfo { method: string; evidence: string; confidence: string; replaced: number | null }
export interface Segment {
  id: number; source: string; target: string; target_hl: Span[]; annotations: number[]
  ai: Record<number, AiInfo>
  unsplit: boolean; hit: boolean
}
export interface GroupRow { version_id: number; segments: Segment[] }
export interface Group {
  id: number; corpus_id: number; work_id: number; paragraph_id: number; paragraph_seq: number; seq: number
  position: number; source: string; source_hl: Span[]; rows: GroupRow[]; favorite: boolean
}
export interface GroupDetail extends Group {
  context: { id: number; source: string; is_current: boolean; paragraph_seq: number; targets: Record<number, string> }[]
  prev: number | null; next: number | null; work_total: number
}

export interface Facet { id: number; count: number }
export interface SearchResponse {
  total: number; total_segments: number; page: number; size: number
  facets: { corpora: Facet[]; works: Facet[]; versions: Facet[]; values: Facet[] }
  results: Group[]
  history_id: number | null
}

export interface SearchParams {
  q?: string; mode?: 'morph' | 'exact'; corpora?: number[]; works?: number[]; versions?: number[]
  values?: number[]; exclude?: number[]; logic?: 'or' | 'and' | 'group'; origin?: 'all' | 'human' | 'ai'
  page?: number; size?: number
}

export interface Paged<T> { total: number; page?: number; size?: number; results: T[] }
