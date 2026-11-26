import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
import { dirname, resolve } from 'node:path'
import type { ConsumptionResponse } from '../src/api/types'

const hash = (bytes: Buffer) => createHash('sha256').update(bytes).digest('hex')
// These expectations are bound to the independently verified stage 2 evidence.
// A changed export needs an explicit new review, not a silently updated total.
const manifestPath = resolve(process.env.GOLD_EXPORT_MANIFEST!)
const raw = readFileSync(manifestPath)
if (hash(raw) !== '2cc84aceabcf19e830028648252cae300ff03eb0cc1f99af311e5e046f91e347') throw new Error('Gold manifest differs from the reviewed stage 2 evidence.')
const manifest = JSON.parse(raw.toString())
for (const grain of ['hourly', 'daily']) {
  const source = manifest.exports[grain]
  if (hash(readFileSync(resolve(dirname(manifestPath), source.file))) !== source.sha256) throw new Error('Export checksum differs.')
}

test('verified gold consumption through real API and all four browser tabs', async ({ page, request }) => {
  const api = process.env.GOLD_API_BASE_URL!
  const site = process.env.GOLD_WEBSITE_URL!
  const total = Number(manifest.exports.daily.observed_energy_kwh)
  const dayTotal = Number(manifest.daily_comparisons[0].actual_daily_kwh)
  const query = new URLSearchParams({ household_id: manifest.household_id, start: manifest.requested_start, end: manifest.requested_end })
  const health = await request.get(`${api}/health`, { headers: { Origin: site } })
  expect(health.status()).toBe(200)
  expect(await health.json()).toMatchObject({ data_mode: 'dynamodb', data_source: 'gold', is_demo: false })
  if (api.startsWith('https:')) {
    expect(health.headers()['access-control-allow-origin']).toBe(site)
    const preflight = await request.fetch(`${api}/chat`, { method: 'OPTIONS', headers: {
      Origin: site, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'content-type',
    } })
    expect(preflight.ok()).toBe(true)
    expect(preflight.headers()['access-control-allow-origin']).toBe(site)
    expect(preflight.headers()['access-control-allow-methods']).toContain('POST')
    expect(preflight.headers()['access-control-allow-headers'].toLowerCase()).toContain('content-type')
  }
  for (const grain of ['hourly', 'daily']) {
    const response = await request.get(`${api}/consumption?${query}&grain=${grain}`)
    expect(response.status()).toBe(200)
    const data: ConsumptionResponse = await response.json()
    expect(data).toMatchObject({ data_source: 'gold', is_demo: false, units: { energy_kwh: 'kWh' } })
    expect(data.items).toHaveLength(manifest.exports[grain].row_count)
    expect(data.items.every(item => item.is_complete && item.energy_kwh !== null)).toBe(true)
    expect(data.items.reduce((sum, item) => sum + item.energy_kwh!, 0)).toBeCloseTo(total, 6)
  }
  const errors: string[] = []
  const seen = new Set<string>()
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', req => {
    const url = new URL(req.url())
    if (url.origin === api) seen.add(url.pathname)
    // Local Vite sends /api through its proxy; production must call API Gateway.
    if (site.startsWith('http:') && url.origin === site && url.pathname.startsWith('/api/')) seen.add(url.pathname.slice(4))
  })
  // Allow only configured origins and keep all responses real: no fulfill/mock.
  await page.route('**/*', route => {
    if (![api, site].includes(new URL(route.request().url()).origin)) { errors.push('Unexpected external request'); return route.abort() }
    return route.continue()
  })
  await page.goto('/')
  const card = page.getByRole('article').filter({ hasText: 'Total consumption' })
  await expect(card).toContainText(total.toFixed(2))
  await expect(page.getByText('Historical source data')).toBeVisible()
  await expect(page.getByText('Demo data')).toHaveCount(0)
  const history = page.getByRole('group', { name: 'Historical period (UTC)' })
  await history.getByLabel('Through', { exact: false }).fill('2009-06-01')
  await expect(card).toContainText(dayTotal.toFixed(2))
  await history.getByLabel('Through', { exact: false }).fill('2009-06-07')
  await expect(card).toContainText(total.toFixed(2))
  await page.getByLabel('Consumption interval').selectOption('hourly')
  await expect(page.getByRole('img', { name: /168 actual and 0 forecast/ })).toBeVisible()
  const tabs = page.getByRole('navigation', { name: 'Energy views' })
  await tabs.getByRole('button', { name: 'Anomalies' }).click()
  await expect(page.getByText(/Anomaly detection is not integrated/)).toBeVisible()
  await tabs.getByRole('button', { name: 'Forecast' }).click()
  await expect(page.getByText('Forecast model is not integrated.')).toBeVisible()
  await expect(page.getByText(/Origin:/)).toHaveCount(0)
  await expect(page.getByRole('img', { name: /168 actual and 0 forecast/ })).toBeVisible()
  await tabs.getByRole('button', { name: 'Assistant' }).click()
  await page.getByLabel('Your question').fill('Summarize my historical consumption.')
  await page.getByRole('button', { name: 'Send question' }).click()
  await expect(page.getByText('Placeholder: chat is not implemented. Bedrock is not connected.', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Request weekly summary' }).click()
  await expect(page.getByText('Placeholder: weekly summary is not implemented. Bedrock is not connected.', { exact: true })).toBeVisible()
  expect(errors).toEqual([])
  for (const path of ['/consumption', '/anomalies', '/forecast', '/chat']) expect(seen.has(path), `Browser must call ${api}${path}`).toBe(true)
})
