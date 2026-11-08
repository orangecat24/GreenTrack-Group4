import { defineConfig, devices } from '@playwright/test'

// Keep these ports separate from development's 8000/5173. Always start fresh
// servers: accidentally testing an old/live server would make a demo misleading.
export default defineConfig({
  testDir: './e2e',
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:15173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'node scripts/start-mock-api.mjs',
      url: 'http://127.0.0.1:18000/health',
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 15173 --strictPort',
      // Waiting through the proxy proves that both web and API are ready.
      url: 'http://127.0.0.1:15173/api/health',
      env: {
        VITE_API_BASE_URL: '/api',
        API_PROXY_TARGET: 'http://127.0.0.1:18000',
      },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
})
