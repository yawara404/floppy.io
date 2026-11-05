<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import Composer from '../components/Composer.vue'
import PostList from '../components/PostList.vue'
import { apiGet } from '~/utils/api'
import { isLoggedIn, authReady } from '~/composables/useAuth'

const props = defineProps({
  // 'timeline'  = 全体タイムライン（#/）
  // 'following' = フォロー中タイムライン（#/following・要ログイン）
  feed: { type: String, default: 'timeline' },
})

const posts = ref([])
const error = ref('')

const isFollowingFeed = computed(() => props.feed === 'following')

// 未ログインのタイムラインでのみランディング用ヒーローを出す
// (認証状態の復元前に一瞬表示されないよう authReady を待つ)
const showLanding = computed(
  () => authReady.value && !isLoggedIn.value && !isFollowingFeed.value,
)

function scrollToTimeline() {
  document
    .getElementById('timeline')
    ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}


// 誰をフォローしているかは本人にしか見せないため、フォロー中 TL はログイン必須
const needsLogin = computed(() => isFollowingFeed.value && !isLoggedIn.value)

const emptyText = computed(() =>
  isFollowingFeed.value
    ? 'フォロー中のユーザーの投稿はまだありません。気になる人をフォローしてみましょう'
    : 'まだ投稿がありません。最初の投稿をしてみましょう',
)

async function load() {
  error.value = ''

  // 未ログインでは取得できない（401）ので、案内だけ表示する
  if (needsLogin.value) {
    posts.value = []
    return
  }

  try {
    const path = isFollowingFeed.value ? '/posts?feed=following' : '/posts'
    const data = await apiGet(path)
    posts.value = data.posts || []
  } catch (e) {
    error.value = e.message
    posts.value = []
  }
}

function onPosted(post) {
  // フォロー中 TL にも自分の投稿が含まれるので、どちらのタブでも先頭に足す
  posts.value.unshift(post)
}

// タブ（タイムライン / フォロー中）を切り替えたら読み直す
watch(() => props.feed, load)

// 保存済みトークンの確認は非同期なので、ログイン状態が確定してから読み込む
watch(
  () => [isLoggedIn.value, authReady.value],
  () => {
    if (isFollowingFeed.value) load()
  },
)

onMounted(load)
</script>

<template>
  <div>
    <!-- ランディング: 未ログインのタイムライン -->
    <section v-if="showLanding" class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="hero-eyebrow">
          <span class="pulse-dot"></span>
          FLOPPY ARCHIVE / ONLINE
        </p>

        <h1 id="hero-title" class="hero-title">
          <span class="hero-title-line">1.44MB</span>
          <span class="hero-title-line hero-title-sub">しか、使えない。</span>
        </h1>

        <p class="hero-lead">
          ドット絵、画像、8bit 曲、そして短い言葉。
          1 投稿あたりフロッピーディスク 1 枚分に収めて残す、
          静かなレトロ SNS です。
        </p>

        <div class="hero-actions">
          <NuxtLink class="btn btn-primary btn-lg" to="/register">
            アカウントを作る
          </NuxtLink>
          <button type="button" class="btn btn-ghost btn-lg" @click="scrollToTimeline">
            タイムラインを見る
          </button>
        </div>

        <dl class="hero-stats">
          <div>
            <dt>1 POST</dt>
            <dd>1.44 MB</dd>
          </div>
          <div>
            <dt>PIXEL ART</dt>
            <dd>256 B</dd>
          </div>
          <div>
            <dt>FEED</dt>
            <dd>CHRONO</dd>
          </div>
        </dl>
      </div>

      <div class="hero-visual" aria-hidden="true">
        <span class="hero-pixel-frame"></span>

        <div class="floppy-pixel">
          <svg
            class="floppy-pixel-svg"
            viewBox="0 0 64 64"
            shape-rendering="crispEdges"
          >
            <rect x="9" y="8" width="48" height="52" fill="#b9b3a1" />
            <rect x="5" y="3" width="48" height="52" fill="#e8e4d2" />
            <rect
              x="5"
              y="3"
              width="48"
              height="52"
              fill="none"
              stroke="#22252a"
              stroke-width="2"
            />
            <rect x="11" y="3" width="26" height="14" fill="#a9b3aa" />
            <rect x="11" y="3" width="8" height="14" fill="#30363a" />
            <rect x="13" y="25" width="32" height="24" fill="#fffdf1" />
            <rect x="13" y="25" width="32" height="4" fill="#d4cfba" />
            <rect x="25" y="46" width="8" height="2" fill="#30363a" />
          </svg>
          <span class="floppy-pixel-tag">floppy.io<br /><i>1.44MB</i></span>
        </div>

        <span class="hero-chip chip-a">[READY] DISK 01</span>
        <span class="hero-chip chip-b">16 × 16 DOT</span>
        <span class="hero-chip chip-c">NO ALGORITHM</span>
      </div>
    </section>

    <!-- 特徴カード -->
    <section v-if="showLanding" class="feature-grid" aria-label="floppy.io の特徴">
      <article class="feature-card">
        <span class="feature-index">01 / CAPACITY</span>
        <h3>1 投稿、1 枚。</h3>
        <p>
          本文もドット絵も画像も、合計 1.44MB まで。
          容量を意識すると、残す言葉が選ばれる。
        </p>
        <span class="feature-tag">1,474,560 BYTES / POST</span>
      </article>

      <article class="feature-card">
        <span class="feature-index">02 / PIXEL</span>
        <h3>256 バイトのドット絵。</h3>
        <p>
          16×16 のグリッドを 16 色で描く。画像に変換せず、
          16 進数の文字列として保存するから、驚くほど軽い。
        </p>
        <span class="feature-tag">16 COLORS · 16 × 16</span>
      </article>

      <article class="feature-card">
        <span class="feature-index">03 / FEED</span>
        <h3>アルゴリズムは、ない。</h3>
        <p>
          新しい順に流れるだけ。おすすめも広告もない、
          静かな距離感のタイムラインです。
        </p>
        <span class="feature-tag">CHRONOLOGICAL ONLY</span>
      </article>
    </section>

    <!-- フォロー中 TL はログイン必須 -->
    <div v-if="needsLogin" class="callout">
      <span>フォロー中のタイムラインを見るにはログインが必要です。</span>
      <NuxtLink class="btn btn-primary" to="/login">ログイン</NuxtLink>
      <NuxtLink class="btn" to="/register">新規登録</NuxtLink>
    </div>

    <template v-else>
      <template v-if="isLoggedIn">
        <div class="section-head">
          <div>
            <p class="section-kicker">WRITE TO DISK</p>
            <h2 class="section-title">今日のフロッピー</h2>
            <p class="section-note">
              本文・ドット絵・画像・ファイル。合計 1.44MB まで書き込めます。
            </p>
          </div>
          <span class="timeline-count">DISK READY</span>
        </div>

        <Composer @posted="onPosted" />
      </template>

      <div v-else class="callout">
        <span>投稿するにはアカウントが必要です。</span>
        <NuxtLink class="btn btn-primary" to="/register">新規登録</NuxtLink>
        <NuxtLink class="btn" to="/login">ログイン</NuxtLink>
      </div>
    </template>

    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <section id="timeline" class="timeline-wrap">
      <div class="section-head">
        <div>
          <p class="section-kicker">LIVE FEED / CHRONOLOGICAL</p>
          <h2 class="section-title">タイムライン</h2>
        </div>
        <span class="timeline-count">{{ posts.length }} POSTS</span>
      </div>

      <div class="timeline-head">
        <!-- タブ切り替え（URL も共有できる） -->
        <nav class="feed-tabs">
          <NuxtLink
            class="feed-tab"
            :class="{ active: !isFollowingFeed }"
            :aria-current="!isFollowingFeed ? 'page' : undefined"
            to="/"
          >タイムライン</NuxtLink>
          <NuxtLink
            class="feed-tab"
            :class="{ active: isFollowingFeed }"
            :aria-current="isFollowingFeed ? 'page' : undefined"
            to="/following"
          >フォロー中</NuxtLink>
        </nav>
        <span class="timeline-count">NEWEST FIRST</span>
      </div>

      <PostList
        v-if="!needsLogin"
        :posts="posts"
        :empty-text="emptyText"
        @changed="load"
      />
    </section>
  </div>
</template>
