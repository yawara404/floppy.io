<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  currentUser,
  isLoggedIn,
  loadMe,
  logout,
} from '~/composables/useAuth'
import ProfileCard from '~/components/ProfileCard.vue'

const route = useRoute()
const menuOpen = ref(false)

const path = computed(() => route.path || '/')
const isProfilePage = computed(() => /^\/u\/[^/]+$/.test(path.value))
const isHome = computed(() => path.value === '/')
const isFollowing = computed(() => path.value === '/following')

const profileHref = computed(() =>
  isLoggedIn.value ? `/u/${currentUser.value.username}` : '/login',
)

// 画面遷移したらメニューを閉じる
watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false
  },
)

async function onLogout() {
  menuOpen.value = false
  await logout()
  await navigateTo('/')
}

// ---------------------------------------------------------------------------
// コピー抑止 (右クリック / 選択 / ドラッグ / コピー)
//
// 注意: これはブラウザ上の deterrence であり、HTML ソースの閲覧や
// スクリーンショット、開発者ツールを完全に防ぐものではない。
// 入力欄・共有リンク・埋め込みコードは通常どおりコピーできる。
// ---------------------------------------------------------------------------
const copyNotice = ref('')
let copyTimer = null

function isCopyAllowed(target) {
  return Boolean(
    target?.closest?.(
      'input, textarea, select, [contenteditable="true"], .allow-copy',
    ),
  )
}

function showCopyNotice(message = 'このサイトのコンテンツはコピーできません。') {
  copyNotice.value = message
  if (copyTimer) clearTimeout(copyTimer)
  copyTimer = setTimeout(() => {
    copyNotice.value = ''
  }, 2200)
}

function onContextMenu(event) {
  if (!isCopyAllowed(event.target)) event.preventDefault()
}

function onDragStart(event) {
  if (event.target?.closest?.('img, canvas, video, audio')) {
    event.preventDefault()
  }
}

function onCopy(event) {
  if (!isCopyAllowed(event.target)) {
    event.preventDefault()
    showCopyNotice()
  }
}

function onCut(event) {
  if (!isCopyAllowed(event.target)) {
    event.preventDefault()
    showCopyNotice()
  }
}

onBeforeUnmount(() => {
  if (copyTimer) clearTimeout(copyTimer)
})

// ハッシュルーターでは href="#main" がルート扱いになるため、
// スキップリンクは JS でフォーカス移動する
function skipToMain(event) {
  event.preventDefault()
  const main = document.getElementById('main')
  if (!main) return
  main.focus({ preventScroll: true })
  main.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

onMounted(loadMe)
</script>

<template>
  <div
    class="app"
    @contextmenu="onContextMenu"
    @dragstart="onDragStart"
    @copy="onCopy"
    @cut="onCut"
  >
    <!-- 背景演出 -->
    <div class="app-bg" aria-hidden="true">
      <span class="bg-glow bg-glow-a"></span>
      <span class="bg-glow bg-glow-b"></span>
      <span class="bg-grid"></span>
      <span class="bg-noise"></span>
    </div>

    <a class="skip-link" href="#main" @click="skipToMain">本文へスキップ</a>

    <!-- トップバー -->
    <header class="topbar">
      <div class="topbar-inner">
        <button
          type="button"
          class="hamburger"
          :class="{ open: menuOpen }"
          :aria-expanded="menuOpen ? 'true' : 'false'"
          aria-label="メニュー"
          @click="menuOpen = !menuOpen"
        >
          <span></span><span></span><span></span>
        </button>

        <NuxtLink class="logo" to="/">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M4 3.5h12.6L20 6.9V20.5H4V3.5Z" fill="currentColor" />
              <rect x="8.2" y="3.5" width="7.6" height="5.6" rx="1" fill="#0a1712" />
              <rect x="7" y="13" width="10" height="5.8" rx="1" fill="#0a1712" opacity=".88" />
            </svg>
          </span>
          <span class="brand-word">floppy<span class="brand-dot">.</span>io</span>
          <span class="brand-badge">1.44MB</span>
        </NuxtLink>

        <nav class="nav" :class="{ open: menuOpen }">
          <NuxtLink class="nav-link" :class="{ active: isHome }" to="/">
            ホーム
          </NuxtLink>
          <NuxtLink class="nav-link" :class="{ active: isFollowing }" to="/following">
            フォロー中
          </NuxtLink>
          <NuxtLink
            class="nav-link"
            :class="{ active: path === '/search' }"
            to="/search"
          >
            検索
          </NuxtLink>
          <NuxtLink
            class="nav-link"
            :class="{ active: isProfilePage }"
            :to="profileHref"
          >
            プロフィール
          </NuxtLink>
          <NuxtLink
            class="nav-link"
            :class="{ active: path === '/settings' }"
            to="/settings"
          >
            設定
          </NuxtLink>
          <NuxtLink
            class="nav-link"
            :class="{ active: path === '/help' }"
            to="/help"
          >
            ヘルプ
          </NuxtLink>
        </nav>

        <div class="topbar-user">
          <template v-if="isLoggedIn">
            <NuxtLink class="user-chip" :to="'/u/' + currentUser.username">
              <span class="user-led"></span>@{{ currentUser.username }}
            </NuxtLink>
            <button type="button" class="link-btn topbar-login" @click="onLogout">
              ログアウト
            </button>
          </template>
          <template v-else>
            <NuxtLink class="link-btn topbar-login" to="/login">ログイン</NuxtLink>
            <NuxtLink class="btn btn-primary btn-sm" to="/register">
              参加する
            </NuxtLink>
          </template>
        </div>
      </div>
    </header>

    <!-- モバイル: メニュー外をタップしたら閉じる -->
    <div v-if="menuOpen" class="nav-backdrop" @click="menuOpen = false"></div>

    <div class="page" :class="{ 'page-profile': isProfilePage }">
      <!-- 左カラム -->
      <aside class="sidebar">
        <ProfileCard v-if="isLoggedIn" :user="currentUser" />

        <div v-else class="profile-card login-cta">
          <p class="login-cta-kicker">WELCOME / DISK READY</p>
          <div class="login-cta-title">floppy.io へようこそ</div>
          <p class="login-cta-text">
            1.44MB しか使えない静寂のレトロ SNS。容量と相談しながら、
            残したいものを 1 枚に収めてください。
          </p>
          <div class="login-cta-actions">
            <NuxtLink class="btn btn-primary" to="/register">新規登録</NuxtLink>
            <NuxtLink class="btn" to="/login">ログイン</NuxtLink>
          </div>
        </div>

        <div class="sidebar-status">
          <div class="status-title">SYSTEM STATUS</div>
          <div class="status-row"><span>DISK</span><b>1.44 MB</b></div>
          <div class="status-row"><span>FEED</span><b>CHRONO</b></div>
          <div class="status-row"><span>NOISE</span><b class="ok">0%</b></div>
        </div>

        <div class="sidebar-note">💾 1 投稿あたり 1.44MB</div>
      </aside>

      <!-- 右カラム -->
      <main id="main" class="content" tabindex="-1">
        <slot />
      </main>
    </div>

    <!-- フッター -->
    <footer class="page-footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="brand-mark brand-mark-sm" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M4 3.5h12.6L20 6.9V20.5H4V3.5Z" fill="currentColor" />
              <rect x="8.2" y="3.5" width="7.6" height="5.6" rx="1" fill="#0a1712" />
              <rect x="7" y="13" width="10" height="5.8" rx="1" fill="#0a1712" opacity=".88" />
            </svg>
          </span>
          <div>
            <div class="footer-word">floppy<span class="brand-dot">.</span>io</div>
            <div class="footer-tag">A QUIET 1.44MB ARCHIVE</div>
          </div>
        </div>

        <nav class="footer-nav" aria-label="フッターナビゲーション">
          <NuxtLink to="/">タイムライン</NuxtLink>
          <NuxtLink to="/search">検索</NuxtLink>
          <NuxtLink to="/help">ヘルプ</NuxtLink>
          <NuxtLink to="/settings">設定</NuxtLink>
        </nav>

        <div class="footer-note">
          © {{ new Date().getFullYear() }} floppy.io — 容量と向き合う SNS
        </div>
      </div>
    </footer>

    <!-- コピー抑止の通知 -->
    <Transition name="toast">
      <div v-if="copyNotice" class="copy-toast" role="status" aria-live="polite">
        <span class="copy-toast-led"></span>
        {{ copyNotice }}
      </div>
    </Transition>
  </div>
</template>
