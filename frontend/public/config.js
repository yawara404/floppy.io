/**
 * floppy.io — 実行時 API 接続先の設定
 *
 * ビルドし直さなくても、このファイル 1 枚を書き換えれば
 * フロントエンドの API 接続先を変更できる。
 * （Nuxt は public/ の中身を dist の直下にそのままコピーする）
 *
 * 既定は同一オリジンの /api。
 * - 開発: Nuxt (Vite) の proxy が /api → http://127.0.0.1:8000 に転送する
 * - 本番: リバースプロキシが /api と /uploads を FastAPI に転送する
 * - サブディレクトリ配信: /floppy.io/api のように自動で補正する
 */
(function () {
  var loc = window.location
  var base

  if (loc.pathname !== '/' && !/\.[a-z0-9]+$/i.test(loc.pathname)) {
    // サブディレクトリ配信 (例: https://example.com/floppy.io/) → 同じ階層の /api
    var dir = loc.pathname.slice(-1) === '/' ? loc.pathname : loc.pathname + '/'
    base = dir + 'api'
  } else {
    // ルート配信 / Nuxt(Vite) 開発サーバー → 同一オリジン
    base = '/api'
  }

  window.__FLOPPY_API_BASE__ = base
})()
