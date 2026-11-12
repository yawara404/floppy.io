export default defineNuxtPlugin((nuxtApp) => {
  // 開発時にキャッシュや登録を残さず、静的ビルドでのみ有効にする。
  if (import.meta.dev || !('serviceWorker' in navigator) || !window.isSecureContext) return

  nuxtApp.hook('app:mounted', () => {
    const baseURL = useRuntimeConfig().app.baseURL
    navigator.serviceWorker.register(`${baseURL}sw.js`, {
      scope: baseURL,
      updateViaCache: 'none',
    }).catch((error) => {
      console.warn('[floppy.io] オフライン機能を登録できませんでした。', error)
    })
  })
})
