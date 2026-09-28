<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import Composer from '../components/Composer.vue'
import PostList from '../components/PostList.vue'
import { apiGet } from '../utils/api.js'
import { isLoggedIn, authReady } from '../store/auth.js'

const props = defineProps({
  // 'timeline'  = 全体タイムライン（#/）
  // 'following' = フォロー中タイムライン（#/following・要ログイン）
  feed: { type: String, default: 'timeline' },
})

const posts = ref([])
const error = ref('')

const isFollowingFeed = computed(() => props.feed === 'following')

// 誰をフォローしているかは本人にしか見せないため、フォロー中 TL はログイン必須
const needsLogin = computed(() => isFollowingFeed.value && !isLoggedIn.value)

const emptyText = computed(() =>
  isFollowingFeed.value
    ? 'フォロー中のユーザーの投稿はまだありません。気になる人をフォローしてみましょう 💾'
    : 'まだ投稿がありません。最初の投稿をしてみましょう 💾',
)

async function load() {
  error.value = ''

  // 未ログインでは取得できない（401）ので、案内だけ表示する
  if (needsLogin.value) {
    posts.value = []
    return
  }

  try {
    const path = isFollowingFeed.value ? '/posts.php?feed=following' : '/posts.php'
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
    <!-- フォロー中タイムラインはログイン必須 -->
    <div v-if="needsLogin" class="callout">
      <span>フォロー中のタイムラインを見るにはログインが必要です。</span>
      <a class="btn btn-primary" href="#/login">ログイン</a>
      <a class="btn" href="#/register">新規登録</a>
    </div>

    <template v-else>
      <Composer v-if="isLoggedIn" @posted="onPosted" />

      <div v-else class="callout">
        <span>投稿するにはアカウントが必要です。</span>
        <a class="btn btn-primary" href="#/register">新規登録</a>
        <a class="btn" href="#/login">ログイン</a>
      </div>
    </template>

    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <section class="timeline-wrap">
      <div class="timeline-head">
        <!-- 昔の Twitter 風のタブ切り替え（リンクなので URL も共有できる） -->
        <nav class="feed-tabs">
          <a
            class="feed-tab"
            :class="{ active: !isFollowingFeed }"
            :aria-current="!isFollowingFeed ? 'page' : undefined"
            href="#/"
          >タイムライン</a>
          <a
            class="feed-tab"
            :class="{ active: isFollowingFeed }"
            :aria-current="isFollowingFeed ? 'page' : undefined"
            href="#/following"
          >フォロー中</a>
        </nav>
        <span class="timeline-count">{{ posts.length }} 件</span>
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
