// floppy.io — <dialog> モーダルの共通処理
// 開いたときのフォーカス退避 / 背景スクロールのロック / 閉じたときの復元を
// ShareDialog などで使い回す。

import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'

export function useDialog() {
  const dialogEl = ref(null)
  const closeEl = ref(null)
  let returnFocus = null
  let hadScrollLock = false

  onMounted(async () => {
    returnFocus = document.activeElement
    hadScrollLock = document.body.classList.contains('is-modal-open')
    document.body.classList.add('is-modal-open')

    await nextTick()
    dialogEl.value?.showModal()
    closeEl.value?.focus()
  })

  onBeforeUnmount(() => {
    dialogEl.value?.close()
    if (!hadScrollLock) document.body.classList.remove('is-modal-open')
    returnFocus?.focus?.()
  })

  return { dialogEl, closeEl }
}
