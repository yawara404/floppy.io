// floppy.io — 実行環境まわりの小さなヘルパー

const IPV4_RE = /^\d{1,3}(\.\d{1,3}){3}$/

/** IP アドレスで開かれているか（YouTube の埋め込み制限の案内に使う） */
export function isIpHost() {
  return typeof window !== 'undefined' && IPV4_RE.test(window.location.hostname)
}

/** 同じパスのまま localhost に置き換えた URL */
export function localhostUrl() {
  if (typeof window === 'undefined') return '#'
  const { protocol, port, pathname, search, hash } = window.location
  return `${protocol}//localhost${port ? ':' + port : ''}${pathname}${search}${hash}`
}
