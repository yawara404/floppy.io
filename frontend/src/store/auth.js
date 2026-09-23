// floppy.io — 認証ストア (ログイン中のユーザーを保持)

import { ref, computed } from 'vue'
import { apiGet, apiPost, setAuthToken } from '../utils/api.js'

const TOKEN_KEY = 'floppy_token'

const user = ref(null)
const ready = ref(false)

export const currentUser = user
export const authReady = ready
export const isLoggedIn = computed(() => user.value !== null)

function readToken() {
  try {
    return localStorage.getItem(TOKEN_KEY) || ''
  } catch (e) {
    return ''
  }
}

function saveToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch (e) {
    // localStorage が使えない環境では無視
  }
  setAuthToken(token)
}

/** 起動時に保存済みトークンでログイン状態を復元する */
export async function loadMe() {
  if (!readToken()) {
    user.value = null
    ready.value = true
    return
  }

  try {
    const data = await apiGet('/me.php')
    user.value = data.user
  } catch (e) {
    user.value = null
    if (e.status === 401) saveToken('')
  } finally {
    ready.value = true
  }
}

/** ログイン中のユーザー情報 (統計を含む) を取り直す */
export async function refreshUser() {
  if (!readToken()) return
  try {
    const data = await apiGet('/me.php')
    user.value = data.user
  } catch (e) {
    if (e.status === 401) {
      saveToken('')
      user.value = null
    }
  }
}

export async function login(username, password) {
  const data = await apiPost('/login.php', { username, password })
  saveToken(data.token)
  user.value = data.user
  return data.user
}

export async function register(username, password, displayName) {
  const data = await apiPost('/register.php', {
    username,
    password,
    display_name: displayName,
  })
  saveToken(data.token)
  user.value = data.user
  return data.user
}

export async function logout() {
  try {
    await apiPost('/logout.php', {})
  } catch (e) {
    // サーバー側で無効化できなくてもクライアント側はログアウトする
  }
  saveToken('')
  user.value = null
}

/** API から返った最新のユーザー情報を反映する (プロフィール更新後など) */
export function applyUser(updated) {
  user.value = updated
}
