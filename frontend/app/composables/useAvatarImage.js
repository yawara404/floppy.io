// floppy.io — 投稿 / 返信のアバター画像
// 「アイコン URL を解決 → 読み込み失敗なら canvas 描画に切り替える」を
// PostItem / PostDetail / ReplyBubble / ShareDialog で共通化する。

import { computed, ref } from 'vue'
import { resolveMediaUrl } from '~/utils/api'

/**
 * @param {() => { author_icon_url?: string, author_avatar_url?: string } | null} getSource
 */
export function useAvatarImage(getSource) {
  const failed = ref(false)

  const image = computed(() => {
    if (failed.value) return ''
    const source = getSource() || {}
    return resolveMediaUrl(source.author_icon_url || source.author_avatar_url || '')
  })

  /** 別の投稿に切り替わったときに再挑戦する */
  function reset() {
    failed.value = false
  }

  function onError() {
    failed.value = true
  }

  return { image, failed, reset, onError }
}
