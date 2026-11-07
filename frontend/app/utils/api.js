// floppy.io — API クライアント (フェッチヘルパー)
//
// 接続先の優先順位:
//   1. public/config.js が設定する実行時の値 (window.__FLOPPY_API_BASE__)
//   2. 同一オリジンの /api
//
// config.js は Nuxt の head で先に読み込まれるが、読み込み順に依存しないよう
// リクエストのたびに評価する。
function resolveBase() {
  if (typeof window !== 'undefined' && window.__FLOPPY_API_BASE__) {
    return window.__FLOPPY_API_BASE__
  }
  return '/api'
}

const TOKEN_KEY = 'floppy_token'

/**
 * API が返すアップロード URL を、現在のページ階層に依存しない URL にする。
 *
 * 以前の API は './uploads/xxx' を返していたため、/u/name では
 * '/u/uploads/xxx' に解決されて画像が 404 になっていた。
 * 絶対 URL / data: / blob: はそのまま返す。
 */
export function resolveMediaUrl(path) {
  if (!path) return ''

  const value = String(path)
  if (/^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(value)) return value

  // '/api' または '/floppy.io/api' → '' または '/floppy.io'
  const root = resolveBase().replace(/\/api\/?$/, '')

  if (value.startsWith('/')) {
    // '/uploads/...' と '/floppy.io/uploads/...' のどちらも、いまのアプリの
    // ルート配下 (/uploads または /floppy.io/uploads) に置き直す。
    // これで本番ビルドと開発サーバー (baseURL '/') の両方で表示できる。
    const uploadsAt = value.indexOf('/uploads/')
    if (uploadsAt >= 0) return `${root}${value.slice(uploadsAt)}`
    return value
  }

  return `${root}/${value.replace(/^\.\//, '')}`
}

// サーバー停止 / DNS 不達 / オフライン時にブラウザが投げる TypeError を
// そのまま見せると「Failed to fetch」で原因が分からないため差し替える。
const OFFLINE_MESSAGE =
  'サーバーに接続できません。時間をおいて再試行してください。'


function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch (e) {
    return ''
  }
}

let authToken = readToken()

/** 認証トークンを設定する (空文字で解除) */
export function setAuthToken(token) {
  authToken = token || ''
}

/** HTTP ステータス付きのエラー */
export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function errorMessage(data, res) {
  const message =
    data.error || data.detail || data.message || data.statusMessage

  if (typeof message === 'string' && message.trim()) return message
  if (Array.isArray(message)) {
    const messages = message.map((item) => item?.msg).filter((item) => typeof item === 'string')
    if (messages.length) return messages.join(' / ')
  }

  // リバースプロキシ (nginx / Vite) が返す「API に繋がらない」系のステータス。
  // 本文が HTML などで JSON でないため、ここで分かりやすい文言に差し替える。
  if (res.status === 502 || res.status === 503 || res.status === 504) {
    return OFFLINE_MESSAGE
  }

  return `リクエストに失敗しました（${res.status}）。再試行してください。`
}

/** fetch を実行し、通信断と HTTP エラーを ApiError に正規化する */
async function fetchJson(url, options) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 20000)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    const data = await res.json().catch((error) => {
      if (controller.signal.aborted) throw error
      return null
    })

    if (!res.ok) {
      throw new ApiError(errorMessage(data || {}, res), res.status)
    }
    if (!data || typeof data !== 'object' || Array.isArray(data)) {
      throw new ApiError('サーバーから正しいデータを取得できませんでした。再試行してください。', res.status)
    }
    return data
  } catch (e) {
    if (e instanceof ApiError) throw e
    if (controller.signal.aborted) {
      throw new ApiError('通信に時間がかかっています。接続を確認して再試行してください。', 0)
    }
    throw new ApiError(OFFLINE_MESSAGE, 0)
  } finally {
    clearTimeout(timer)
  }
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  return fetchJson(resolveBase() + path, { ...options, headers })
}

export const apiGet = (path) => request(path)

export const apiPost = (path, body) =>
  request(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

export const apiDelete = (path, body) =>
  request(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

/**
 * multipart/form-data で送る (画像アップロード用)。
 * Content-Type はブラウザに boundary 付きで設定させるため、指定しない。
 */
export async function apiUpload(path, formData) {
  const headers = {}
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  return fetchJson(resolveBase() + path, {
    method: 'POST',
    body: formData,
    headers,
  })
}
