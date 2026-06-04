import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// dev 时把 /api 代理到本地 FastAPI（make serve, :8000）
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
})
