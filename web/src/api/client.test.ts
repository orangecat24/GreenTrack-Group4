import { describe, expect, it, vi } from 'vitest'
import { apiUrl, postChat, readPath, requestJson } from './client'
import { jsonResponse } from '../test/data'

describe('shared API transport', () => {
  it('uses the complete base prefix and normalizes trailing slashes', () => {
    expect(apiUrl('/health', '/api/')).toBe('/api/health')
    expect(apiUrl('/health', '/')).toBe('/health')
    expect(apiUrl('/forecast', 'https://example.test/stage/')).toBe('https://example.test/stage/forecast')
    vi.stubEnv('VITE_API_BASE_URL', 'https://example.test/api')
    expect(apiUrl('/health')).toBe('https://example.test/api/health')
  })
  it('encodes timezone offsets and household IDs as query parameters', () => {
    const path = readPath('/consumption', { household_id: 'household-1', start: '2009-06-01T02:00:00+02:00', end: '2009-06-02T00:00:00Z' }, 'daily')
    expect(new URL(path, 'https://example.test').searchParams.get('start')).toBe('2009-06-01T02:00:00+02:00')
    expect(path).toContain('grain=daily')
  })
  it('turns FastAPI validation details into a useful message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: [{ loc: ['query', 'end'], msg: 'end must be later than start' }] }, 422)))
    await expect(requestJson('/consumption')).rejects.toThrow('query.end: end must be later than start')
  })
  it('explains network failures and non-JSON proxy errors', async () => {
    const fetch = vi.fn().mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValueOnce(new Response('Bad gateway', { status: 502 }))
    vi.stubGlobal('fetch', fetch)
    await expect(requestJson('/health')).rejects.toThrow('Start FastAPI on port 8000')
    await expect(requestJson('/health')).rejects.toThrow('502')
  })
  it('reports successful but invalid JSON instead of crashing the whole page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>wrong server</html>')))
    await expect(requestJson('/health')).rejects.toThrow('invalid JSON')
  })
  it('preserves cancellation and passes the POST body and signal', async () => {
    const controller = new AbortController()
    const body = { household_id: 'household-1', start: '2009-06-01T00:00:00Z', end: '2009-06-08T00:00:00Z', request_type: 'weekly_summary' as const }
    const fetch = vi.fn().mockResolvedValue(jsonResponse({ status: 'placeholder' }))
    vi.stubGlobal('fetch', fetch)
    await postChat(body, controller.signal)
    expect(fetch).toHaveBeenCalledWith('/api/chat', expect.objectContaining({ method: 'POST', signal: controller.signal, body: JSON.stringify(body) }))
    controller.abort()
    fetch.mockRejectedValue(new DOMException('Aborted', 'AbortError'))
    await expect(postChat(body, controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
  })
})
