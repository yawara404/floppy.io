/**
 * floppy.io — 実行時 API 接続先の設定
 *
 * ビルドし直さなくても、このファイル 1 枚を書き換えれば
 * フロントエンドの API 接続先を変更できる。
 * （Vite は public/ の中身を dist/ の直下にそのままコピーする）
 *
 * ただし、このファイルを書き換えたあとは `npm run build` で
 * dist にコピーし直す必要がある。
 */
(function () {
  // ===================================================================
  // 環境ごとの設定（変えたらここを直して再ビルド）
  // ===================================================================

  // --- MAMP PRO の専用ホスト ---
  //   DocumentRoot = frontend/dist
  //   Alias /floppy_io/api     → backend/api
  //   Alias /floppy_io/uploads → backend/uploads
  //
  // 例: https://floppy.io:8890/ で開く場合
  //
  // ※ ルートの /api は使えないことがある。サーバー全体に
  //    ProxyPass /api/ が設定されていると、ProxyPass は Alias より
  //    優先されるため横取りされる。そのため /floppy_io/api を使う。
  var MAMP_PRO_HOSTS = ['floppy.io']

  // --- MAMP PRO (推奨) ---
  //   http://floppy.io:8080/ で配信（ホスト名 floppy.io は上の MAMP_PRO_HOSTS）
  //   Live Server など別オリジンからは、この URL の API を直接叩く
  var MAMP_ORIGIN = 'http://floppy.io:8080'
  var MAMP_API_PATH = '/floppy_io/api'

  // --- MAMP（無料版・旧構成）でパス方式を使う場合の例 ---
  //   var MAMP_ORIGIN = 'http://localhost:8888'
  //   var MAMP_API_PATH = '/floppy_io/api'

  // ===================================================================

  var loc = window.location
  var base

  if (MAMP_PRO_HOSTS.indexOf(loc.hostname) !== -1) {
    // MAMP PRO の専用ホスト → 同一オリジンの PHP API
    base = loc.origin + MAMP_API_PATH
  } else if (loc.pathname !== '/' && !/\.[a-z0-9]+$/i.test(loc.pathname)) {
    // サブディレクトリ配下で配信（例: https://example.com/<name>/）→ 同じ階層の /api
    var dir = loc.pathname.slice(-1) === '/' ? loc.pathname : loc.pathname + '/'
    base = dir + 'api'
  } else if (loc.port === '8888') {
    // MAMP（無料版）→ 同一オリジン
    base = loc.origin + MAMP_API_PATH
  } else if (loc.port === '5173') {
    // Vite 開発サーバー → vite.config.js の proxy (/api → :8000) を使う
    base = '/api'
  } else {
    // Live Server などの静的サーバー → PHP は動かないので MAMP の API を直接叩く
    base = MAMP_ORIGIN + MAMP_API_PATH
  }

  window.__FLOPPY_API_BASE__ = base
})()
