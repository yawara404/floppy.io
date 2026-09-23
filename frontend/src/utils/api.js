// floppy.io — API クライアント (フェッチヘルパー)

// 優先順位:
//   1. public/config.js が設定する実行時の値 (window.__FLOPPY_API_BASE__)
//   2. ビルド時の環境変数 VITE_API_BASE
//   3. 同一オリジンの /api
const BASE =
  (typeof window !== 'undefined' && window.__FLOPPY_API_BASE__) ||
  import.meta.env.VITE_API_BASE ||
  '/api'

const TOKEN_KEY = 'floppy_token'

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

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) }

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`
  }

  const res = await fetch(BASE + path, { ...options, headers })
  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new ApiError(data.error || `Request failed (${res.status})`, res.status)
  }

  return data
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

  const res = await fetch(BASE + path, { method: 'POST', body: formData, headers })
  const data = await res.json().catch(() => ({}))

  if (!res.ok) {
    throw new ApiError(data.error || `Request failed (${res.status})`, res.status)
  }

  return data
}
