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
 *
 * 重要: このスクリプト自身の URL からアプリのルートを求める。
 *   /p/12 のような深いパスでは location.pathname を基準にすると
 *   /p/12/api になってしまう（共有ページで API が壊れる原因）。
 */
(function () {
  function dirname(pathname) {
    var i = pathname.lastIndexOf('/')
    return i >= 0 ? pathname.slice(0, i + 1) : '/'
  }

  // 自分自身の <script src> を探す（currentScript が使えない環境も考慮）
  var src = (document.currentScript && document.currentScript.src) || ''
  if (!src) {
    var scripts = document.getElementsByTagName('script')
    for (var i = 0; i < scripts.length; i++) {
      if (/(^|\/)config\.js(\?|#|$)/.test(scripts[i].src || '')) {
        src = scripts[i].src
        break
      }
    }
  }

  var base = '/api'

  if (src) {
    try {
      // 例: https://example.com/floppy.io/config.js → /floppy.io/
      var root = dirname(new URL(src, window.location.href).pathname)
      base = root + 'api'
    } catch (e) {
      base = '/api'
    }
  }

  window.__FLOPPY_API_BASE__ = base
})()
