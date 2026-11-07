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
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api(?=\/|$)/, ''),
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
    clearMocks: true,
  },
})
