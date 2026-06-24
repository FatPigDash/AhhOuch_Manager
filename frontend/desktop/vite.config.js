import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    vue(),
    VitePWA({
      registerType: 'autoUpdate',
      // 開發時也可預覽 Service Worker（方便測試）
      devOptions: { enabled: false },
      manifest: {
        name: 'AhhOuch_Manager',
        short_name: 'AhhOuch',
        description: '幹部資訊管理與班表發布',
        lang: 'zh-Hant',
        start_url: './',
        display: 'standalone',
        background_color: '#f5f7fa',
        theme_color: '#102a43',
        icons: [
          { src: 'icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
      },
      workbox: {
        // 快取所有靜態資源（HTML、JS、CSS、圖示）→ 離線可用
        globPatterns: ['**/*.{js,css,html,png,svg,woff2}'],
      },
    }),
  ],
  base: './',
  server: {
    port: 5173,
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
