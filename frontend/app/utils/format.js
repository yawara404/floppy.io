// floppy.io — 表示用の整形ヘルパー
// 各コンポーネントに散らばっていた fmt / fmtDate をここへ集約する。

const LOCALE = 'ja-JP'

const pad = (n) => String(n).padStart(2, '0')

/** MySQL の "YYYY-MM-DD HH:MM:SS" などを Date に変換（不正なら null） */
function toDate(value) {
  if (!value) return null
  const date = new Date(String(value).replace(' ', 'T'))
  return Number.isNaN(date.getTime()) ? null : date
}

/** 3,388 のような桁区切り */
export function formatNumber(value) {
  return (Number(value) || 0).toLocaleString(LOCALE)
}

/** YYYY/MM/DD HH:MM（不正値は fallback、未指定なら元の文字列） */
export function formatDateTime(value, fallback = '') {
  const date = toDate(value)
  if (!date) return fallback || (value ? String(value) : '')
  return (
    `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

/** YYYY/MM/DD（不正値は fallback） */
export function formatDate(value, fallback = '') {
  const date = toDate(value)
  if (!date) return fallback
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`
}

/** HH:MM（不正値は ''） */
export function formatClock(value) {
  const date = toDate(value)
  return date ? `${pad(date.getHours())}:${pad(date.getMinutes())}` : ''
}

/** 共有カード用に { time, date } へ分ける（不正値は date に元の文字列） */
export function formatDateParts(value) {
  const date = toDate(value)
  if (!date) return { time: '', date: value ? String(value) : '' }
  return {
    time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
    date: `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`,
  }
}

/** 2026年9月 のような年月表記（プロフィールの登録月） */
export function formatMonth(value) {
  const date = toDate(value)
  if (!date) return value ? String(value) : ''
  return `${date.getFullYear()}年${date.getMonth() + 1}月`
}
