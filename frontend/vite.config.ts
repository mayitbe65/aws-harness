import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    middlewareMode: false,
    hmr: {
      host: 'localhost',
      port: 5173,
      protocol: 'http',
    },
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'd1vc0y0etec2o0.cloudfront.net',
      '*.cloudfront.net',
    ],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
