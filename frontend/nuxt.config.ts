// floppy.io — Nuxt 4 設定
//
// SSR は使わず SPA として生成する。認証トークンを localStorage に置く
// 既存の設計と、FastAPI を同一オリジンで叩く構成をそのまま活かすため。
// ルーティングは履歴モード（/u/name, /p/12）。静的配信側では未知パスを
// index.html にフォールバックさせる（tools/public_gateway.py / .htaccess）。
// 開発時: フロントエンド (Nuxt :5173) から Python API へ転送する。
// ポート 8000 が他のアプリと衝突する場合は FLOPPY_API_PORT でずらせる。
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

const apiTarget =
  process.env.FLOPPY_API_TARGET ||
  `http://127.0.0.1:${process.env.FLOPPY_API_PORT || '8000'}`

// public/ の静的ファイルは app.baseURL を前置した絶対パスで参照する。
//   './config.js' のままだと共有ページ /p/12 で /p/config.js を探して 404 になり、
//   実行時 API 接続先 (window.__FLOPPY_API_BASE__) が読まれない。
const appBase = (process.env.NUXT_APP_BASE_URL || '/').replace(/\/?$/, '/')
const publicPath = (file: string) => `${appBase}${file}`

// config.js の中身が変わったら URL も変える（Cloudflare / ブラウザの
// 古いキャッシュが残り、API 接続先の修正が反映されないのを防ぐ）。
const configVersion = createHash('sha1')
  .update(readFileSync(new URL('./public/config.js', import.meta.url)))
  .digest('hex')
  .slice(0, 8)

export default defineNuxtConfig({
  ssr: false,

  devtools: { enabled: true },

  // Vite 開発サーバー
  devServer: { port: 5173 },

  compatibilityDate: '2025-07-15',

  css: ['~/assets/css/main.css', '~/assets/css/refinements.css'],

  app: {
    head: {
      htmlAttrs: { lang: 'ja' },

      title: 'floppy.io — 1.44MB しか使えない静寂のレトロ SNS',
      titleTemplate: '%s',

      meta: [
        {
          name: 'google-site-verification',
          content: 'QEND1wFNaZp1AQkewXw8BQcRELQNfWwU_W_G9aUs5XQ',
        },
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
        { name: 'color-scheme', content: 'light' },
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-title', content: 'floppy.io' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },

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
        { rel: 'manifest', href: publicPath('manifest.webmanifest') },
        { rel: 'icon', type: 'image/svg+xml', href: publicPath('favicon.svg') },
        {
          rel: 'icon',
          type: 'image/png',
          sizes: '32x32',
          href: publicPath('favicon-32.png'),
        },
        {
          rel: 'icon',
          type: 'image/png',
          sizes: '512x512',
          href: publicPath('favicon.png'),
        },
        {
          rel: 'apple-touch-icon',
          sizes: '180x180',
          href: publicPath('apple-touch-icon.png'),
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
      // 中身のハッシュを ?v= に付けて、古いキャッシュを引かないようにする。
      script: [
        {
          src: `${publicPath('config.js')}?v=${configVersion}`,
          tagPosition: 'head',
        },
      ],
    },

    pageTransition: { name: 'page', mode: 'out-in' },
  },

  // 履歴モード: /u/name, /p/12 のような通常のパスで表示する。
  router: {
    options: {
      scrollBehaviorType: 'smooth',
    },
  },

  // 開発時: フロントエンド (Nuxt :5173) から Python API へ転送する。
  // ポート 8000 が他のアプリと衝突する場合は次のようにずらせる:
  //   cd backend && PORT=8001 ./run.sh
  //   cd frontend && FLOPPY_API_PORT=8001 npm run dev
  vite: {
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/uploads': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  },

  experimental: {
    payloadExtraction: false,
  },
})
