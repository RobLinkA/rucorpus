/** Thin fetch wrapper: JSON, session cookie, CSRF header, readable errors. */

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function csrfToken() {
  return document.cookie.split('; ').find((c) => c.startsWith('csrftoken='))?.split('=')[1] ?? ''
}

type Query = Record<string, string | number | boolean | null | undefined | (string | number)[]>

export function qs(params: Query = {}) {
  const u = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => u.append(k, String(x)))
    else u.append(k, String(v))
  }
  const s = u.toString()
  return s ? `?${s}` : ''
}

async function request<T>(method: string, url: string, body?: unknown, query?: Query): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  let payload: BodyInit | undefined
  if (body instanceof FormData) payload = body
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  if (method !== 'GET') headers['X-CSRFToken'] = csrfToken()
  const res = await fetch(`/api${url}${qs(query)}`, { method, headers, body: payload, credentials: 'same-origin' })
  if (!res.ok) {
    let msg = `请求失败（${res.status}）`
    try {
      const j = await res.json()
      if (typeof j.detail === 'string') msg = j.detail
      else if (Array.isArray(j.detail)) msg = j.detail.map((d: { msg: string }) => d.msg).join('；')
    } catch { /* not json */ }
    if (res.status === 401) msg = '请先登录'
    throw new ApiError(res.status, msg)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(url: string, query?: Query) => request<T>('GET', url, undefined, query),
  post: <T>(url: string, body?: unknown, query?: Query) => request<T>('POST', url, body ?? {}, query),
  put: <T>(url: string, body?: unknown) => request<T>('PUT', url, body ?? {}),
  patch: <T>(url: string, body?: unknown) => request<T>('PATCH', url, body ?? {}),
  del: <T>(url: string, query?: Query) => request<T>('DELETE', url, undefined, query),
  /** Same-origin download link (cookies are sent by the browser). */
  href: (url: string, query?: Query) => `/api${url}${qs(query)}`,
}
