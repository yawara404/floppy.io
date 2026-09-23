// floppy.io — 依存なしのハッシュルーター
//
// MAMP (静的配信) でも Live Server でも、サーバー側のリライト設定なしで
// 動くようにハッシュ (#/...) 方式にしている。

import { ref } from 'vue'

function parseHash() {
  const raw = window.location.hash.replace(/^#/, '')
  const [pathPart, queryPart] = raw.split('?')

  return {
    path: pathPart || '/',
    query: new URLSearchParams(queryPart || ''),
  }
}

export const route = ref(parseHash())

export function navigate(to, { replace = false } = {}) {
  if (replace) {
    window.location.replace('#' + to)
  } else {
    window.location.hash = to
  }
}

export function initRouter() {
  window.addEventListener('hashchange', () => {
    route.value = parseHash()
    window.scrollTo({ top: 0 })
  })

  if (!window.location.hash) {
    navigate('/', { replace: true })
  }
}
