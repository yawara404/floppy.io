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

  if (message) return message

  // リバースプロキシ (nginx / Vite) が返す「API に繋がらない」系のステータス。
  // 本文が HTML などで JSON でないため、ここで分かりやすい文言に差し替える。
  if (res.status === 502 || res.status === 503 || res.status === 504) {
    return OFFLINE_MESSAGE
  }

  return `Request failed (${res.status})`
}

/** fetch を実行し、通信断と HTTP エラーを ApiError に正規化する */
async function fetchJson(url, options) {
  let res
  try {
    res = await fetch(url, options)
  } catch (e) {
    // サーバー停止 / DNS 不達 / オフライン (TypeError: Failed to fetch)
    throw new ApiError(OFFLINE_MESSAGE, 0)
  }

  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new ApiError(errorMessage(data, res), res.status)
  }

  return data
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
