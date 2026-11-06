// floppy.io — 旧ハッシュURLの後方互換リダイレクト
//
// これまで #/p/12 や #/u/name のようなハッシュURLで共有されていたリンクを、
// 履歴モードの /p/12, /u/name へ自動で読み替える。
export default defineNuxtPlugin((nuxtApp) => {
  if (typeof window === 'undefined') return

  const hash = window.location.hash
  if (!hash.startsWith('#/')) return

  const target = hash.slice(1) || '/'

  // 先にハッシュを消してから遷移する（ブラウザ履歴に残さない）
  window.history.replaceState(
    null,
    '',
    window.location.pathname + window.location.search,
  )

  nuxtApp.hook('app:mounted', () => {
    nuxtApp.$router.replace(target).catch(() => {})
  })
})
