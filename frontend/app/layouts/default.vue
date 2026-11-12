<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  currentUser,
  isLoggedIn,
  authReady,
  loadMe,
  logout,
} from '~/composables/useAuth'
import ProfileCard from '~/components/ProfileCard.vue'

const route = useRoute()
const menuOpen = ref(false)
const moreMenuOpen = ref(false)
const moreMenuRef = ref(null)
const navToggle = ref(null)
const moreToggle = ref(null)

const path = computed(() => route.path || '/')
const isProfilePage = computed(() => /^\/u\/[^/]+(?:\/(?:following|followers))?$/.test(path.value))
const isHome = computed(() => path.value === '/' || path.value === '/following')
const isLanding = computed(() => path.value === '/' && authReady.value && !isLoggedIn.value)

const isDisks = computed(
  () => path.value === '/disks' || /^\/d\/[^/]+$/.test(path.value),
)
const isMoreActive = computed(
  () => path.value === '/settings' || path.value === '/help',
)

const profileHref = computed(() =>
  isLoggedIn.value ? `/u/${currentUser.value.username}` : '/login',
)

// 画面遷移したらメニューを閉じる
watch(
  () => route.fullPath,
  () => {
    menuOpen.value = false
    moreMenuOpen.value = false
  },
)

// 三点メニューの外側をクリックしたら閉じる
function onDocumentClick(event) {
  if (!moreMenuOpen.value) return
  if (moreMenuRef.value && !moreMenuRef.value.contains(event.target)) {
    moreMenuOpen.value = false
  }
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    if (menuOpen.value) navToggle.value?.focus()
    else if (moreMenuOpen.value) moreToggle.value?.focus()
    menuOpen.value = false
    moreMenuOpen.value = false
  }
}

async function onLogout() {
  menuOpen.value = false
  moreMenuOpen.value = false
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
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKeydown)
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

onMounted(() => {
  loadMe()
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onKeydown)
})
</script>

<template>
  <div
    class="app"
    @contextmenu="onContextMenu"
    @dragstart="onDragStart"
    @copy="onCopy"
    @cut="onCut"
  >
    <!-- 背景演出（ピクセルグリッド / ディザ / 走査線） -->
    <div class="app-bg" aria-hidden="true">
      <span class="bg-grid"></span>
      <span class="bg-dither"></span>
      <span class="bg-scanlines"></span>
    </div>

    <a class="skip-link" href="#main" @click="skipToMain">本文へスキップ</a>

    <!-- トップバー -->
    <header class="topbar">
      <div class="topbar-inner">
        <button
          ref="navToggle"
          type="button"
          class="hamburger"
          :class="{ open: menuOpen }"
          :aria-expanded="menuOpen ? 'true' : 'false'"
          aria-controls="primary-nav"
          aria-label="メニュー"
          @click="menuOpen = !menuOpen; moreMenuOpen = false"
        >
          <span></span><span></span><span></span>
        </button>

        <NuxtLink class="logo" to="/">
          <span class="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 16 16" shape-rendering="crispEdges">
              <rect x="1" y="1" width="14" height="14" fill="currentColor" />
              <rect x="5" y="1" width="6" height="4" fill="#0b1a12" />
              <rect x="3" y="8" width="10" height="6" fill="#0b1a12" />
            </svg>
          </span>
          <span class="brand-word">floppy<span class="brand-dot">.</span>io</span>
          <span class="brand-badge">1.44MB</span>
        </NuxtLink>

        <nav id="primary-nav" class="nav" :class="{ open: menuOpen }" aria-label="メインナビゲーション">
          <NuxtLink class="nav-link" :class="{ active: isHome }" :aria-current="isHome ? 'page' : undefined" to="/">
            ホーム
          </NuxtLink>
          <NuxtLink class="nav-link" :class="{ active: isDisks }" :aria-current="isDisks ? 'page' : undefined" to="/disks">
            ディスク
          </NuxtLink>
          <NuxtLink
            class="nav-link"
            :class="{ active: path === '/search' }"
            :aria-current="path === '/search' ? 'page' : undefined"
            to="/search"
          >
            検索
          </NuxtLink>
          <NuxtLink
            class="nav-link"
            :class="{ active: isProfilePage }"
            :aria-current="isProfilePage ? 'page' : undefined"
            :to="profileHref"
          >
            プロフィール
          </NuxtLink>
        </nav>

        <div class="topbar-user">
          <template v-if="isLoggedIn">
            <NuxtLink class="user-chip" :to="'/u/' + currentUser.username">
              <span class="user-led"></span>@{{ currentUser.username }}
            </NuxtLink>
          </template>
          <template v-else>
            <NuxtLink class="topbar-join" to="/register">[ 参加 ]</NuxtLink>
          </template>

          <!-- 設定 / ヘルプ / ログアウトは右端の三点メニューに集約 -->
          <div ref="moreMenuRef" class="gnav-more">
            <button
              ref="moreToggle"
              type="button"
              class="gnav-more-btn"
              :class="{ active: isMoreActive || moreMenuOpen }"
              :aria-expanded="moreMenuOpen ? 'true' : 'false'"
              aria-controls="more-navigation"
              aria-label="設定とヘルプ"
              @click.stop="moreMenuOpen = !moreMenuOpen; menuOpen = false"
            >
              <span aria-hidden="true">⋮</span>
            </button>

            <div v-if="moreMenuOpen" id="more-navigation" class="gnav-more-menu">
              <div class="gnav-more-head">MENU / FLOPPY.IO</div>

              <NuxtLink
                class="gnav-more-item"
                :class="{ active: path === '/settings' }"
                to="/settings"
                @click="moreMenuOpen = false"
              >
                <span class="gnav-more-key">SET</span>設定
              </NuxtLink>
              <NuxtLink
                class="gnav-more-item"
                :class="{ active: path === '/help' }"
                to="/help"
                @click="moreMenuOpen = false"
              >
                <span class="gnav-more-key">HLP</span>ヘルプ
              </NuxtLink>

              <div class="gnav-more-sep" aria-hidden="true"></div>

              <template v-if="isLoggedIn">
                <button
                  type="button"
                  class="gnav-more-item danger"
                    @click="onLogout"
                >
                  <span class="gnav-more-key">OUT</span>ログアウト
                </button>
              </template>
              <template v-else>
                <NuxtLink
                  class="gnav-more-item"
                  to="/login"
                    @click="moreMenuOpen = false"
                >
                  <span class="gnav-more-key">IN</span>ログイン
                </NuxtLink>
                <NuxtLink
                  class="gnav-more-item"
                  to="/register"
                    @click="moreMenuOpen = false"
                >
                  <span class="gnav-more-key">NEW</span>新規登録
                </NuxtLink>
              </template>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- モバイル: メニュー外をタップしたら閉じる -->
    <div v-if="menuOpen" class="nav-backdrop" @click="menuOpen = false"></div>

    <div class="page" :class="{ 'page-profile': isProfilePage, 'page-landing': isLanding }">
      <!-- 左カラム -->
      <aside class="sidebar" :class="{ 'sidebar-guest': !isLoggedIn }">
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
          <div class="status-row"><span>FEED</span><b>RECOMMENDED</b></div>
          <div class="status-row"><span>NOISE</span><b class="ok">0%</b></div>
        </div>

        <div class="sidebar-note">[DISK] 1 投稿 = 1.44MB</div>
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
            <svg viewBox="0 0 16 16" shape-rendering="crispEdges">
              <rect x="1" y="1" width="14" height="14" fill="currentColor" />
              <rect x="5" y="1" width="6" height="4" fill="#0b1a12" />
              <rect x="3" y="8" width="10" height="6" fill="#0b1a12" />
            </svg>
          </span>
          <div>
            <div class="footer-word">floppy<span class="brand-dot">.</span>io</div>
            <div class="footer-tag">A QUIET 1.44MB ARCHIVE</div>
          </div>
        </div>

        <nav class="footer-nav" aria-label="フッターナビゲーション">
          <NuxtLink to="/">タイムライン</NuxtLink>
          <NuxtLink to="/disks">ディスク</NuxtLink>
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
