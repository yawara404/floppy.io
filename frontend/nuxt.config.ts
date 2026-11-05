// floppy.io — Nuxt 4 設定
//
// SSR は使わず SPA として生成する。認証トークンを localStorage に置く
// 既存の設計と、FastAPI を同一オリジンで叩く構成をそのまま活かすため。
// ルーティングは静的ホスティング (リバースプロキシ / サブディレクトリ) で
// リライト設定が不要なハッシュモードを維持する。
export default defineNuxtConfig({
  ssr: false,

  devtools: { enabled: true },

  // Vite 開発サーバー
  devServer: { port: 5173 },

  compatibilityDate: '2025-07-15',

  css: ['~/assets/css/main.css'],

  app: {
    head: {
      htmlAttrs: { lang: 'ja' },

      title: 'floppy.io — 1.44MB しか使えない静寂のレトロ SNS',
      titleTemplate: '%s',

      meta: [
        {
          name: 'description',
          content:
            '1 投稿あたり 1.44MB。ドット絵・画像・YouTube・8bit 曲をフロッピーディスク 1 枚に収めて投稿する、レトロコンピューティング趣味のミニマル SNS。',
        },
        { property: 'og:type', content: 'website' },
        { property: 'og:site_name', content: 'floppy.io' },
        {
          property: 'og:title',
          content: 'floppy.io — 1.44MB しか使えない静寂のレトロ SNS',
        },
        {
          property: 'og:description',
          content:
            '1 投稿あたり 1.44MB。ドット絵・画像・YouTube・8bit 曲を、フロッピーディスク 1 枚に収めて投稿するレトロ SNS。',
        },
        { property: 'og:url', content: 'https://fdd.wawa-app.me/floppy.io/' },
        {
          property: 'og:image',
          content: 'https://fdd.wawa-app.me/floppy.io/card.png',
        },
        {
          property: 'og:image:secure_url',
          content: 'https://fdd.wawa-app.me/floppy.io/card.png',
        },
        { property: 'og:image:type', content: 'image/png' },
        { property: 'og:image:width', content: '1200' },
        { property: 'og:image:height', content: '630' },
        {
          property: 'og:image:alt',
          content: 'floppy.io — 1.44MB しか使えない静寂のレトロ SNS',
        },
        { property: 'og:locale', content: 'ja_JP' },

        { name: 'theme-color', content: '#cfe9d8' },
        { name: 'color-scheme', content: 'dark' },

        { name: 'twitter:card', content: 'summary_large_image' },
        {
          name: 'twitter:title',
          content: 'floppy.io — 1.44MB しか使えない静寂のレトロ SNS',
        },
        {
          name: 'twitter:description',
          content:
            '1 投稿あたり 1.44MB。ドット絵・画像・YouTube・8bit 曲を、フロッピーディスク 1 枚に収めて投稿するレトロ SNS。',
        },
        {
          name: 'twitter:image',
          content: 'https://fdd.wawa-app.me/floppy.io/card.png',
        },
        {
          name: 'twitter:image:alt',
          content: 'floppy.io — 1.44MB しか使えない静寂のレトロ SNS',
        },
      ],

      link: [
        { rel: 'icon', type: 'image/svg+xml', href: './favicon.svg' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: './favicon-32.png' },
        { rel: 'icon', type: 'image/png', sizes: '512x512', href: './favicon.png' },
        {
          rel: 'apple-touch-icon',
          sizes: '180x180',
          href: './apple-touch-icon.png',
        },
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        {
          rel: 'preconnect',
          href: 'https://fonts.gstatic.com',
          crossorigin: '',
        },
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=DotGothic16&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Sans+JP:wght@400;500;700&family=Press+Start+2P&display=swap',
        },
      ],

      // API の接続先を実行時に決める (public/config.js)。
      // Nuxt のエントリより先に読み込まれるよう head に置く。
      script: [{ src: './config.js', tagPosition: 'head' }],
    },

    pageTransition: { name: 'page', mode: 'out-in' },
  },

  // ハッシュルーティング: #/u/name, #/p/12 のような既存 URL を維持する。
  router: {
    options: {
      hashMode: true,
      scrollBehaviorType: 'smooth',
    },
  },

  // 開発時: フロントエンド (Nuxt :5173) から Python API (:8000) へ転送する
  vite: {
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/uploads': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  },

  experimental: {
    payloadExtraction: false,
  },
})
