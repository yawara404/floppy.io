<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import Composer from '../components/Composer.vue'
import PostList from '../components/PostList.vue'
import { apiGet } from '~/utils/api'
import { isLoggedIn, authReady } from '~/composables/useAuth'

const props = defineProps({
  // 'timeline'  = 全体タイムライン（/）
  // 'following' = フォロー中タイムライン（/following・要ログイン）
  feed: { type: String, default: 'timeline' },
})

const posts = ref([])
const error = ref('')
const loading = ref(true)
let loadSequence = 0

const isFollowingFeed = computed(() => props.feed === 'following')

// 未ログインの全体タイムラインでのみランディング用ヒーローを出す
// (認証状態の復元前に一瞬表示されないよう authReady を待つ)
const showLanding = computed(
  () => authReady.value && !isLoggedIn.value && !isFollowingFeed.value,
)

// 誰をフォローしているかは本人にしか見せないため、フォロー中 TL はログイン必須
const needsLogin = computed(() => authReady.value && isFollowingFeed.value && !isLoggedIn.value)

const emptyText = computed(() =>
  isFollowingFeed.value
    ? 'フォロー中のユーザーの投稿はまだありません。気になる人をフォローしてみましょう。'
    : 'まだ投稿がありません。最初の 1 枚を書き込んでみましょう。',
)

function scrollToTimeline() {
  document
    .getElementById('timeline')
    ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

async function load() {
  if (!authReady.value) return
  const sequence = ++loadSequence
  error.value = ''

  // 未ログインでは取得できない（401）ので、案内だけ表示する
  if (needsLogin.value) {
    posts.value = []
    loading.value = false
    return
  }

  loading.value = true

  try {
    const path = isFollowingFeed.value ? '/posts?feed=following' : '/posts'
    const data = await apiGet(path)
    if (sequence === loadSequence) posts.value = data.posts || []
  } catch (e) {
    if (sequence === loadSequence) error.value = e.message
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

function onPosted(post) {
  // どちらのフィードでも自分の投稿を先頭に足す
  posts.value.unshift(post)
}

// タブ（タイムライン / フォロー中）を切り替えたら読み直す
watch(() => props.feed, load)

// 保存済みトークンの確認は非同期なので、ログイン状態が確定してから読み込む
watch(
  () => [isLoggedIn.value, authReady.value],
  () => {
    if (authReady.value) load()
  },
)

onMounted(load)
</script>

<template>
  <div class="home-page">
    <!-- ランディング: 未ログインのタイムライン -->
    <section v-if="showLanding" class="hero" aria-labelledby="hero-title">
      <div class="hero-copy">
        <p class="hero-eyebrow">
          <span class="pulse-dot"></span>
          A SMALL SPACE FOR YOUR IDEAS
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
            <dd>1,024 B</dd>
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
        <span class="hero-chip chip-b">32 × 32 DOT</span>
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
        <h3>小さな絵に、大きな個性。</h3>
        <p>
          32×32 のキャンバスと、16 色のパレット。
          絵を描くのが久しぶりでも、ひとマスから始められます。
        </p>
        <span class="feature-tag">16 COLORS · 32 × 32</span>
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

    <div v-else-if="!needsLogin && !showLanding && authReady" class="callout">
      <span>投稿するにはアカウントが必要です。</span>
      <NuxtLink class="btn btn-primary" to="/register">新規登録</NuxtLink>
      <NuxtLink class="btn" to="/login">ログイン</NuxtLink>
    </div>

    <NuxtLink v-if="showLanding" class="discover-link" to="/disks">
      <span class="discover-mark" aria-hidden="true">[D]</span>
      <span><strong>好きなものを、同じディスクに。</strong><span>趣味でつながるコミュニティを探す</span></span>
      <span class="discover-arrow" aria-hidden="true">→</span>
    </NuxtLink>

    <section id="timeline" class="timeline-wrap">
      <div class="section-head">
        <div>
          <p class="section-kicker">
            {{ isFollowingFeed ? 'FOLLOWING / CHRONOLOGICAL' : 'LIVE FEED / CHRONOLOGICAL' }}
          </p>
          <h2 class="section-title">
            {{ isFollowingFeed ? 'フォロー中' : 'タイムライン' }}
          </h2>
        </div>
        <button type="button" class="link-btn feed-refresh" :disabled="loading" @click="load">
          <span aria-hidden="true">↻</span> {{ loading ? '読み込み中…' : '更新する' }}
        </button>
      </div>

      <div class="timeline-head">
        <!-- ホームとディスク一覧をつなぐ（フィードの重複は廃止） -->
        <nav class="feed-tabs" aria-label="フィード">
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
          <NuxtLink class="feed-tab" to="/disks">ディスク</NuxtLink>
        </nav>
        <span class="timeline-count">NEWEST FIRST</span>
      </div>

      <div v-if="needsLogin" class="callout">
        <span>フォロー中のタイムラインを見るにはログインが必要です。</span>
        <NuxtLink class="btn btn-primary" to="/login">ログイン</NuxtLink>
        <NuxtLink class="btn" to="/register">新規登録</NuxtLink>
      </div>

      <RequestError v-else-if="error" :message="error" @retry="load" />

      <PostList
        v-else
        :posts="posts"
        :loading="loading"
        :empty-text="emptyText"
        @changed="load"
      />
    </section>
  </div>
</template>
