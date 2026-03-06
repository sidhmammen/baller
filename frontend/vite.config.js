import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/notifications': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/roster': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/schedule': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/players': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/sleeper': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})