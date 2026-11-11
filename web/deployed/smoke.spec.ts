import { expect, test } from '@playwright/test'
import { runStudentDemo } from '../e2e/studentDemo'

test('deployed HTTPS: real browser, public API contract and explicit CORS', async ({ page, request }) => {
  const website = process.env.DEPLOYED_WEBSITE_URL!
  const api = process.env.DEPLOYED_API_BASE_URL!
  const health = await request.get(`${api}/health`, { headers: { Origin: website } })
  expect(health.status()).toBe(200)
  expect(await health.json()).toEqual({ status: 'ok', data_mode: 'mock', is_demo: true })
  expect(health.headers()['access-control-allow-origin']).toBe(website)

  const preflight = await request.fetch(`${api}/chat`, {
    method: 'OPTIONS',
    headers: { Origin: website, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type' },
  })
  expect(preflight.ok()).toBe(true)
  expect(preflight.headers()['access-control-allow-origin']).toBe(website)
  expect(preflight.headers()['access-control-allow-methods']).toContain('POST')
  expect(preflight.headers()['access-control-allow-headers'].toLowerCase()).toContain('content-type')

  const seen = new Set<string>()
  page.on('request', req => {
    const url = new URL(req.url())
    if (url.origin === api) seen.add(url.pathname)
  })
  await runStudentDemo(page, [website, api])
  // This fails if a build forgot VITE_API_BASE_URL and still calls /api on S3.
  for (const path of ['/consumption', '/anomalies', '/forecast', '/chat']) {
    expect(seen.has(path), `Browser must call the deployed API's ${path}`).toBe(true)
  }
})
