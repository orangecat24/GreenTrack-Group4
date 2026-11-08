import type { ChatRequest, ChatResponse, WindowQuery } from './types'

/** The base includes the deployment prefix; endpoints always start with '/'. */
export function apiUrl(path: string, base = import.meta.env.VITE_API_BASE_URL || '/api'): string {
  return `${base.trim().replace(/\/+$/, '')}${path}`
}

/** Convert FastAPI's validation list into text instead of showing [object Object]. */
function errorDetail(body: unknown): string | null {
  if (typeof body !== 'object' || body === null || !('detail' in body)) return null
  const detail = body.detail
  if (typeof detail === 'string') return detail
  if (!Array.isArray(detail)) return null
  return detail.map((item: unknown) => {
    if (typeof item !== 'object' || item === null || !('msg' in item)) return 'Invalid input'
    const location = 'loc' in item && Array.isArray(item.loc) ? item.loc.join('.') : 'request'
    return `${location}: ${String(item.msg)}`
  }).join('; ')
}

/** One transport for all tabs. A failed request stays a local panel error. */
export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(apiUrl(path), {
      ...options,
      headers: { Accept: 'application/json', ...options.headers },
    })
  } catch (error) {
    // Preserve AbortError so an intentional cancellation is never shown as a failure.
    if (options.signal?.aborted) throw error
    throw new Error('Cannot reach the API. Start FastAPI on port 8000 and check the API base URL.', { cause: error })
  }
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    throw new Error(errorDetail(body) || `API request failed (${response.status}). Check that FastAPI is running, then retry.`)
  }
  try {
    // TypeScript checks callers at build time; the server's Pydantic response
    // models remain the runtime contract. This is not runtime JSON validation.
    return await response.json() as T
  } catch {
    throw new Error('The API returned invalid JSON. Check the API base URL and server response.')
  }
}

/** URLSearchParams encodes offsets and IDs without hand-built escaping. */
export function readPath(endpoint: string, query: WindowQuery, grain?: string): string {
  const params = new URLSearchParams({ ...query })
  if (grain) params.set('grain', grain)
  return `${endpoint}?${params}`
}

export function postChat(body: ChatRequest, signal: AbortSignal): Promise<ChatResponse> {
  return requestJson<ChatResponse>('/chat', {
    method: 'POST', signal,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
