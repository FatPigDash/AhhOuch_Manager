import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// base 用相對路徑，確保打包進 exe 由 FastAPI 提供時資源路徑正確。
export default defineConfig({
  plugins: [vue()],
  base: './',
  server: {
    port: 5173,
    // 開發時前端跑 5173，API 代理到後端 8000，避免 CORS。
    proxy: {
      '/api': 'http://localhost:8000',
      '/images': 'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
