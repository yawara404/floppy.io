// floppy.io — 投稿の共有 URL / SNS 共有リンク
//
// 共有 URL は「サブディレクトリ配信」でも壊れないように組み立てる。
// 本番は https://fdd.wawa-app.me/floppy.io/ のように app.baseURL の下に
// 置かれるため、router.resolve() だけに頼らず baseURL を明示的に前置する
// （resolve() が base を含む / 含まないのどちらでも二重にならない）。

const X_INTENT = 'https://twitter.com/intent/tweet'
const LINE_SHARE = 'https://social-plugins.line.me/lineit/share'

export function usePostShare() {
  const router = useRouter()
  const baseURL = useRuntimeConfig().app.baseURL || '/'

  const canNativeShare = computed(
    () => typeof navigator !== 'undefined' && typeof navigator.share === 'function',
  )

  /** 投稿ページ (/p/:id) の絶対 URL */
  function postUrl(post) {
    if (!post || typeof window === 'undefined') return ''

    const id = Number(post.id)
    if (!Number.isFinite(id) || id <= 0) return ''

    const base = baseURL.endsWith('/') ? baseURL.slice(0, -1) : baseURL
    const resolved = router.resolve(`/p/${id}`).href || `/p/${id}`
    const path = base && !resolved.startsWith(`${base}/`) ? base + resolved : resolved

    try {
      return new URL(path, window.location.origin).toString()
    } catch (e) {
      return ''
    }
  }

  /**
   * 本文から外部 URL（YouTube など）を取り除く。
   * X は本文中の URL をカード化するため、そのまま渡すと YouTube のカードが
   * 表示されてしまう。共有文にはサイト本体の URL だけを載せる。
   */
  function stripExternalUrls(value) {
    return String(value || '')
      .replace(/https?:\/\/\S+/g, ' ')
      .replace(/[ \t]+/g, ' ')
      .replace(/\n{3,}/g, '\n\n')
      .trim()
  }

  /** SNS に添える本文（URL を除き、長すぎる場合は省略する） */
  function shareMessage(post) {
    const text = stripExternalUrls(post?.text).replace(/\s+/g, ' ').trim()

    if (!text) {
      const who = post?.display_name || post?.username || 'だれか'
      return `${who} が floppy.io に書き込みました`
    }

    return text.length > 110 ? `${text.slice(0, 110)}…` : text
  }

  /** X (Twitter) の投稿画面 */
  function xShareUrl(post) {
    const url = postUrl(post)
    const params = new URLSearchParams()

    // サイト本体の URL を先頭に置く（X のカードを YouTube ではなくサイトにする）
    params.set('text', [url, shareMessage(post)].filter(Boolean).join('\n'))

    return `${X_INTENT}?${params.toString()}`
  }

  /** LINE の送信画面 */
  function lineShareUrl(post) {
    const url = postUrl(post)
    return `${LINE_SHARE}?url=${encodeURIComponent(url)}`
  }

  /**
   * クリップボードへコピーする。
   * Clipboard API が使えない環境 (http / 古い Safari) は textarea で代替する。
   * @returns {Promise<boolean>} コピーできたら true
   */
  async function copyText(text) {
    if (!text) return false

    if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text)
        return true
      } catch (e) {
        // 権限が無い場合は textarea フォールバックへ
      }
    }

    if (typeof document === 'undefined') return false

    const previousFocus = document.activeElement
    const ta = document.createElement('textarea')
    try {
      ta.value = text
      ta.setAttribute('readonly', '')
      ta.style.position = 'fixed'
      ta.style.top = '-9999px'
      ta.style.opacity = '0'
      // Keep the fallback inside the active modal: the rest of the page is inert.
      const host = document.querySelector('dialog[open]') || document.body
      host.appendChild(ta)
      ta.select()
      const ok = document.execCommand('copy')
      return ok
    } catch (e) {
      return false
    } finally {
      ta.remove()
      previousFocus?.focus?.({ preventScroll: true })
    }
  }

  /** 端末の共有シート (iOS / Android / デスクトップの Web Share API) */
  async function shareNative(post) {
    if (!canNativeShare.value) return false

    try {
      await navigator.share({
        title: `${post?.display_name || post?.username || 'floppy.io'} の投稿 — floppy.io`,
        text: shareMessage(post),
        url: postUrl(post),
      })
      return true
    } catch (e) {
      // キャンセル (AbortError) もここに来る
      return false
    }
  }

  return {
    canNativeShare,
    postUrl,
    shareMessage,
    xShareUrl,
    lineShareUrl,
    copyText,
    shareNative,
  }
}
