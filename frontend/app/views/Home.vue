<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
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
const feedScroll = ref(null)
const postNotice = ref('')
let loadSequence = 0
let postedDuringLoad = []
let noticeTimer

// 'all' = すべて, 'human' = 人間のみ, 'only' = Botのみ
const botFilter = ref('all')

if (typeof window !== 'undefined') {
  const saved = localStorage.getItem('floppy_bot_filter')
  if (saved && ['all', 'human', 'only'].includes(saved)) {
    botFilter.value = saved
  }
}

function setBotFilter(filter) {
  if (botFilter.value === filter) return
  botFilter.value = filter
  if (typeof window !== 'undefined') {
    localStorage.setItem('floppy_bot_filter', filter)
  }
  resetVisible()
  scrollToFeedStart()
  load()
}

const isFollowingFeed = computed(() => props.feed === 'following')

// おすすめ順になるのは「デフォルト TL × bot フィルター: すべて」のときだけ
const isRecommendedFeed = computed(
  () => !isFollowingFeed.value && botFilter.value === 'all',
)

// メイン TL は 50 件ずつ表示する (旧 Twitter 風)。フォロー中は一括表示のまま
const PAGE_SIZE = 50
const visibleCount = ref(PAGE_SIZE)
const displayedPosts = computed(() =>
  isFollowingFeed.value
    ? posts.value
    : posts.value.slice(0, visibleCount.value),
)
const hasMorePosts = computed(
  () => !isFollowingFeed.value && posts.value.length > visibleCount.value,
)

function showMore() {
  visibleCount.value += PAGE_SIZE
}

function resetVisible() {
  visibleCount.value = PAGE_SIZE
}

// 下までスクロールしたら次の 50 件を自動で足す (ボタンでも開ける)
function onScroll() {
  if (loading.value || !hasMorePosts.value) return
  const scroller = isLoggedIn.value ? feedScroll.value : document.scrollingElement
  if (!scroller) return
  const nearBottom = scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 800
  if (nearBottom) showMore()
}

function scrollToFeedStart() {
  if (isLoggedIn.value && feedScroll.value) feedScroll.value.scrollTop = 0
}

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
  postedDuringLoad = []

  // 未ログインでは取得できない（401）ので、案内だけ表示する
  if (needsLogin.value) {
    posts.value = []
    loading.value = false
    return
  }

  loading.value = true

  try {
    const params = new URLSearchParams()
    if (isFollowingFeed.value) {
      params.set('feed', 'following')
    } else if (botFilter.value === 'all') {
      // デフォルト TL はおすすめ順 (bot 控えめ)。人間のみ/Botのみは時系列のまま
      params.set('feed', 'recommended')
    }
    if (botFilter.value === 'human') {
      params.set('bot', '0')
    } else if (botFilter.value === 'only') {
      params.set('bot', 'only')
    }
    const queryString = params.toString()
    const path = queryString ? `/posts?${queryString}` : '/posts'
    const data = await apiGet(path)
    if (sequence === loadSequence) {
      const incoming = data.posts || []
      const ids = new Set(postedDuringLoad.map((post) => post.id))
      posts.value = [...postedDuringLoad, ...incoming.filter((post) => !ids.has(post.id) || post.is_repost)]
    }
  } catch (e) {
    if (sequence === loadSequence) error.value = e.message
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

async function onPosted(post) {
  clearTimeout(noticeTimer)
  postNotice.value = '投稿しました。'
  noticeTimer = setTimeout(() => { postNotice.value = '' }, 3500)
  if (
    (botFilter.value === 'only' && !post.is_bot) ||
    (botFilter.value === 'human' && post.is_bot)
  ) {
    return
  }
  if (loading.value) postedDuringLoad.unshift(post)
  posts.value = [post, ...posts.value.filter((item) => item.id !== post.id || item.is_repost)]
  await nextTick()
  scrollToFeedStart()
}

// タブ（タイムライン / フォロー中）を切り替えたら読み直す
watch(() => props.feed, () => {
  resetVisible()
  postNotice.value = ''
  scrollToFeedStart()
  load()
})

// 保存済みトークンの確認は非同期なので、ログイン状態が確定してから読み込む
watch(
  () => [isLoggedIn.value, authReady.value],
  () => {
    if (authReady.value) load()
  },
)

onMounted(() => {
  load()
  window.addEventListener('scroll', onScroll, { passive: true })
})

onUnmounted(() => {
  loadSequence++
  clearTimeout(noticeTimer)
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <div class="home-page" :class="{ 'home-docked': isLoggedIn }">
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
            <dd>RECOMMENDED</dd>
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
        <span class="hero-chip chip-c">QUIET FEED</span>
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
        <h3>うるさくない、おすすめ。</h3>
        <p>
          デフォルトのタイムラインは、bot の投稿を控えめにしたおすすめ順。
          フォロー中やディスクは、これまで通り新しい順のままです。
        </p>
        <span class="feature-tag">RECOMMENDED + CHRONOLOGICAL</span>
      </article>
    </section>

    <NuxtLink v-if="showLanding" class="discover-link" to="/disks">
      <span class="discover-mark" aria-hidden="true">[D]</span>
      <span><strong>好きなものを、同じディスクに。</strong><span>趣味でつながるコミュニティを探す</span></span>
      <span class="discover-arrow" aria-hidden="true">→</span>
    </NuxtLink>

    <section id="timeline" class="timeline-wrap">
      <header class="home-feed-header">
        <div v-if="authReady && !isLoggedIn" class="section-head">
          <div>
            <p class="section-kicker">
              {{ isFollowingFeed ? 'FOLLOWING / CHRONOLOGICAL' : isRecommendedFeed ? 'HOME / RECOMMENDED' : 'HOME / CHRONOLOGICAL' }}
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
            <NuxtLink v-if="!isLoggedIn" class="feed-tab" to="/disks">ディスク</NuxtLink>
          </nav>
          <div v-if="isLoggedIn" class="home-feed-controls">
            <label class="home-filter">
              <select
                :value="botFilter"
                aria-label="Botの表示"
                @change="setBotFilter($event.target.value)"
              >
                <option value="all">すべて</option>
                <option value="human">人間のみ</option>
                <option value="only">Botのみ</option>
              </select>
            </label>
            <button
              type="button"
              class="link-btn home-feed-refresh"
              :disabled="loading"
              :aria-busy="loading"
              aria-label="タイムラインを更新"
              @click="load"
            >更新</button>
          </div>
          <div v-else class="timeline-meta">
            <div class="bot-filter-group" role="group" aria-label="Bot切り替え">
              <button
                type="button"
                class="bot-filter-btn"
                :class="{ active: botFilter === 'all' }"
                :aria-pressed="botFilter === 'all'"
                title="Botを含むすべての投稿を表示"
                @click="setBotFilter('all')"
              >すべて</button>
              <button
                type="button"
                class="bot-filter-btn"
                :class="{ active: botFilter === 'human' }"
                :aria-pressed="botFilter === 'human'"
                title="Botを除いた投稿のみを表示"
                @click="setBotFilter('human')"
              >人間のみ</button>
              <button
                type="button"
                class="bot-filter-btn"
                :class="{ active: botFilter === 'only' }"
                :aria-pressed="botFilter === 'only'"
                title="Botの投稿のみを表示"
                @click="setBotFilter('only')"
              >Botのみ</button>
            </div>
            <span class="timeline-count">{{ isRecommendedFeed ? 'RECOMMENDED' : 'NEWEST FIRST' }}</span>
          </div>
        </div>
      </header>

      <div
        ref="feedScroll"
        class="home-feed-scroll"
        :role="isLoggedIn ? 'region' : undefined"
        :aria-label="isLoggedIn ? 'タイムラインの投稿' : undefined"
        :tabindex="isLoggedIn ? 0 : undefined"
        @scroll.passive="onScroll"
      >
        <div v-if="needsLogin" class="callout">
          <span>フォロー中のタイムラインを見るにはログインが必要です。</span>
          <NuxtLink class="btn btn-primary" to="/login">ログイン</NuxtLink>
          <NuxtLink class="btn" to="/register">新規登録</NuxtLink>
        </div>

        <RequestError v-else-if="error" :message="error" @retry="load" />

        <PostList
          v-else
          :posts="displayedPosts"
          :loading="loading"
          :empty-text="emptyText"
          :foot-label="isLoggedIn ? '' : isRecommendedFeed ? 'RECOMMENDED / LIMIT 200' : 'CHRONO / LIMIT 200'"
          @changed="load"
        />

        <button
          v-if="hasMorePosts"
          type="button"
          class="btn"
          style="display: block; margin: 16px auto 0"
          @click="showMore"
        >
          さらに表示（残り {{ posts.length - visibleCount }} 件）
        </button>
      </div>

      <div v-if="isLoggedIn" class="home-composer-dock">
        <div class="home-post-status" role="status">
          <span v-if="postNotice">{{ postNotice }}</span>
        </div>
        <Composer message-bar @posted="onPosted" />
      </div>
    </section>
  </div>
</template>

<style scoped>
.home-feed-header > .section-head {
  margin-bottom: 1rem;
}

.home-docked,
.home-docked .timeline-wrap {
  height: 100%;
  min-height: 0;
}

.home-docked .timeline-wrap {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr) auto;
}

.home-docked .home-feed-header {
  padding: 0 clamp(.5rem, 2vw, 1.2rem);
  border-bottom: 1px solid var(--line-strong);
}

.home-docked .timeline-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0 .4rem;
  margin: 0;
  padding: 0;
  border: 0;
}

.home-docked .feed-tabs {
  width: auto;
  min-width: 0;
  gap: .3rem;
  overflow-x: auto;
}

.home-docked .feed-tab {
  flex: 0 0 auto;
  min-height: 44px;
  padding: 0 .4rem;
  white-space: nowrap;
}

.home-docked .feed-tab.active {
  font-weight: 700;
}

.home-docked .feed-tab:focus-visible {
  outline-offset: -2px;
}

.home-feed-controls {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: .2rem;
}

.home-filter {
  position: relative;
}

.home-filter::after {
  position: absolute;
  right: .6rem;
  top: 50%;
  width: .35rem;
  height: .35rem;
  border-right: 1px solid currentColor;
  border-bottom: 1px solid currentColor;
  color: var(--ink-2);
  pointer-events: none;
  content: '';
  transform: translateY(-70%) rotate(45deg);
}

.home-filter select {
  min-height: 34px;
  padding: 0 1.35rem 0 .45rem;
  appearance: none;
  border: 1px solid var(--line-strong);
  border-radius: 2px;
  background: var(--paper-2);
  color: var(--ink);
  font-family: var(--font-body);
  font-size: .8rem;
  cursor: pointer;
}

.home-feed-refresh {
  min-width: 44px;
  min-height: 44px;
  font-size: .8rem;
  text-align: center;
}

.home-docked .home-feed-scroll {
  min-width: 0;
  min-height: 0;
  padding: .4rem clamp(.5rem, 2vw, 1.2rem);
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.home-docked .home-feed-scroll :deep(.post) {
  gap: .6rem;
  padding: .75rem clamp(.55rem, 2vw, .9rem);
}

.home-docked .home-feed-scroll :deep(.post-avatar img),
.home-docked .home-feed-scroll :deep(.post-avatar canvas) {
  width: 100%;
  height: auto;
  aspect-ratio: 1;
}

.home-docked .home-feed-scroll :deep(.post-bytes) {
  flex: 0 1 auto;
  margin-inline-start: auto;
}

.home-docked .home-feed-scroll :deep(.post-text) {
  margin-block: .25rem;
}

.home-docked .home-feed-scroll :deep(.post-actions) {
  gap: .2rem .45rem;
  margin-top: .25rem;
}

.home-composer-dock {
  position: relative;
  min-width: 0;
  padding: .35rem clamp(.5rem, 2vw, 1.2rem) max(.5rem, env(safe-area-inset-bottom));
  background: var(--paper);
}

.home-post-status {
  position: absolute;
  z-index: 2;
  inset-inline-end: .85rem;
  inset-block-end: 100%;
}

.home-post-status span {
  display: block;
  padding: .15rem .6rem;
  border: 1px solid var(--accent-line);
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-size: .85rem;
}

@media (pointer: coarse) {
  .home-filter select {
    min-height: 40px;
    font-size: 1rem;
  }
}

@media (max-width: 380px) {
  .home-docked .timeline-head,
  .home-docked .feed-tabs {
    column-gap: .15rem;
  }

  .home-docked .feed-tab {
    padding-inline: .25rem;
  }

  .home-filter select {
    padding-inline: .3rem 1rem;
  }

  .home-filter::after {
    right: .4rem;
  }
}
</style>
