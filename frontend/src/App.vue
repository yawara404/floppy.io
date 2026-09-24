<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { route, navigate, initRouter } from './utils/router.js'
import { currentUser, isLoggedIn, loadMe, logout } from './store/auth.js'
import ProfileCard from './components/ProfileCard.vue'
import Home from './views/Home.vue'
import Search from './views/Search.vue'
import Profile from './views/Profile.vue'
import Settings from './views/Settings.vue'
import Help from './views/Help.vue'
import Auth from './views/Auth.vue'
import PostView from './views/PostView.vue'

initRouter()

// モバイル用ハンバーガーメニュー
const menuOpen = ref(false)

const view = computed(() => {
  const path = route.value.path

  if (path === '/' || path === '') return { name: 'home' }
  if (path === '/search') return { name: 'search' }
  if (path === '/help') return { name: 'help' }
  if (path === '/settings') return { name: 'settings' }
  if (path === '/login') return { name: 'auth', mode: 'login' }
  if (path === '/register') return { name: 'auth', mode: 'register' }

  const match = path.match(/^\/u\/([^/]+)$/)
  if (match) return { name: 'profile', username: decodeURIComponent(match[1]) }

  const postMatch = path.match(/^\/p\/(\d+)$/)
  if (postMatch) return { name: 'post', id: postMatch[1] }

  return { name: 'notfound' }
})

const profileHref = computed(() =>
  isLoggedIn.value ? `#/u/${currentUser.value.username}` : '#/login',
)

// 画面遷移したらメニューを閉じる
watch(
  () => route.value.path + '?' + route.value.query.toString(),
  () => {
    menuOpen.value = false
  },
)

async function onLogout() {
  menuOpen.value = false
  await logout()
  navigate('/')
}

onMounted(loadMe)
</script>

<template>
  <div class="app">
    <!-- 昔の Twitter 風トップバー -->
    <header class="topbar">
      <div class="topbar-inner">
        <!-- モバイル用ハンバーガー -->
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

        <a class="logo" href="#/">floppy.io</a>

        <nav class="nav" :class="{ open: menuOpen }">
          <a
            class="nav-link"
            :class="{ active: view.name === 'home' }"
            href="#/"
          >ホーム</a>
          <a
            class="nav-link"
            :class="{ active: view.name === 'search' }"
            href="#/search"
          >検索</a>
          <a
            class="nav-link"
            :class="{ active: view.name === 'profile' }"
            :href="profileHref"
          >プロフィール</a>
          <a
            class="nav-link"
            :class="{ active: view.name === 'settings' }"
            href="#/settings"
          >設定</a>
          <a
            class="nav-link"
            :class="{ active: view.name === 'help' }"
            href="#/help"
          >ヘルプ</a>
        </nav>

        <div class="topbar-user">
          <template v-if="isLoggedIn">
            <a class="nav-link" :href="'#/u/' + currentUser.username">
              @{{ currentUser.username }}
            </a>
            <button type="button" class="link-btn" @click="onLogout">
              ログアウト
            </button>
          </template>
          <template v-else>
            <a class="nav-link" href="#/login">ログイン</a>
            <a class="nav-link" href="#/register">新規登録</a>
          </template>
        </div>
      </div>
    </header>

    <div class="page" :class="{ 'page-profile': view.name === 'profile' }">
      <!-- 左カラム -->
      <aside class="sidebar">
        <ProfileCard v-if="isLoggedIn" :user="currentUser" />

        <div v-else class="profile-card login-cta">
          <div class="login-cta-title">floppy.io へようこそ</div>
          <p class="login-cta-text">
            1.44MB しか使えない静寂のレトロ SNS。アカウントを作って投稿してみましょう。
          </p>
          <div class="login-cta-actions">
            <a class="btn btn-primary" href="#/register">新規登録</a>
            <a class="btn" href="#/login">ログイン</a>
          </div>
        </div>

        <div class="sidebar-note">💾 1 投稿あたり 1.44MB</div>
      </aside>

      <!-- 右カラム -->
      <main class="content">
        <Home v-if="view.name === 'home'" />
        <Search v-else-if="view.name === 'search'" />
        <Profile
          v-else-if="view.name === 'profile'"
          :key="view.username"
          :username="view.username"
        />
        <Settings v-else-if="view.name === 'settings'" />
        <Help v-else-if="view.name === 'help'" />
        <PostView v-else-if="view.name === 'post'" :key="view.id" :id="view.id" />
        <Auth v-else-if="view.name === 'auth'" :key="view.mode" :mode="view.mode" />
        <div v-else class="empty">ページが見つかりません。</div>
      </main>
    </div>
  </div>
</template>
