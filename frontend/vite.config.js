import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// El front llama a /api y Vite lo reenvía al backend (sin problemas de CORS en desarrollo)
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { '/api': process.env.VITE_PROXY_TARGET || 'http://localhost:8000' } },
})
