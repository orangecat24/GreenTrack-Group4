import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  build: {
    // Recharts has a sizeable dependency tree. Keep it in a reusable chart chunk
    // rather than bundling it into the application's own first-party code.
    rollupOptions: { output: { manualChunks: { charts: ['recharts'] } } },
  },
  server: {
    port: 5173,
    strictPort: true,
    // The browser requests /api/consumption from Vite. Only the development
    // server removes /api and forwards /consumption to the existing Python API.
    proxy: {
      '/api': {
        // Browser tests use their own API port so normal development servers
        // can stay running. This is a server-only override, never a VITE_* secret.
        target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api(?=\/|$)/, ''),
      },
    },
  },
  test: {
    // Playwright specs use a real browser; only src/ belongs to Vitest/jsdom.
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
    clearMocks: true,
  },
})
