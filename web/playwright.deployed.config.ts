import { defineConfig, devices } from '@playwright/test'

// Never start local servers or silently fall back to localhost for a deployment
// test. These public values come from the validated Terraform application output.
const website = process.env.DEPLOYED_WEBSITE_URL || ''
const api = process.env.DEPLOYED_API_BASE_URL || ''
if (!/^https:\/\/[a-z0-9]+\.cloudfront\.net$/.test(website)
  || !/^https:\/\/[a-z0-9]+\.execute-api\.eu-central-1\.amazonaws\.com$/.test(api)) {
  throw new Error('Set the exact DEPLOYED_WEBSITE_URL and DEPLOYED_API_BASE_URL from the dev application output.')
}

export default defineConfig({
  testDir: './deployed',
  workers: 1,
  forbidOnly: true,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  retries: 2, // Bounded retries for IAM/gateway/CDN propagation, not endless polling.
  reporter: 'list',
  use: { baseURL: website, trace: 'off', screenshot: 'off' },
  projects: [{ name: 'deployed-chromium', use: { ...devices['Desktop Chrome'] } }],
})
