import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  // ビルド成果物のパスを相対 (./assets/...) にする。
  // MAMP のサブディレクトリ (/floppy_io/) でも Live Server のルートでも
  // 同じ dist をそのまま配信できる。
  base: './',
  server: {
    port: 5173,
    // 開発時: /api/* へのリクエストを PHP 内蔵サーバー (:8000) に転送する
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
