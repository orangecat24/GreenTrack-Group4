import { defineConfig, devices } from '@playwright/test'

// This config never starts a mock server or falls back to local fixtures. The
// operator must explicitly choose already-running gold API and website origins.
if (process.env.GOLD_SMOKE_ENABLED !== 'true') throw new Error('Opt in with GOLD_SMOKE_ENABLED=true after the gold load and application setup.')
for (const key of ['GOLD_WEBSITE_URL', 'GOLD_API_BASE_URL']) {
  const value = process.env[key] || ''
  if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(value)
    && !(key === 'GOLD_WEBSITE_URL' ? /^https:\/\/[a-z0-9]+\.cloudfront\.net$/ : /^https:\/\/[a-z0-9]+\.execute-api\.eu-central-1\.amazonaws\.com$/).test(value)) {
    throw new Error(`Set an explicit local or GreenTrack HTTPS origin in ${key}.`)
  }
}
if (!process.env.GOLD_EXPORT_MANIFEST) throw new Error('Set GOLD_EXPORT_MANIFEST to the reviewed stage 2 manifest.')

export default defineConfig({
  testDir: './gold', workers: 1, forbidOnly: true, timeout: 120_000,
  expect: { timeout: 20_000 }, retries: 0, reporter: 'list',
  use: { baseURL: process.env.GOLD_WEBSITE_URL, trace: 'off', screenshot: 'off' },
  projects: [{ name: 'gold-chromium', use: { ...devices['Desktop Chrome'] } }],
})
