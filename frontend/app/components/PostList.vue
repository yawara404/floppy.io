<script setup>
import { computed, ref, nextTick } from 'vue'
import PostItem from './PostItem.vue'
import ShareDialog from './ShareDialog.vue'
import { apiPost, apiDelete } from '~/utils/api'
import { isLoggedIn, currentUser, refreshUser } from '~/composables/useAuth'
import { formatDate } from '~/utils/format'

const props = defineProps({
  posts: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  messageLog: { type: Boolean, default: false },
  emptyText: {
    type: String,
    default: 'まだ投稿がありません。最初の 1 枚を書き込んでみましょう。',
  },
  // フッター右側の並び順ラベル。おすすめ TL では呼び出し側が RECOMMENDED を渡す
  footLabel: {
    type: String,
    default: 'CHRONO / LIMIT 200',
  },
})

const emit = defineEmits(['changed', 'like-changed', 'deleted'])

const rows = computed(() => {
  let previousDate = ''
  return props.posts.map((post) => {
    const date = props.messageLog ? formatDate(post.created_at) : ''
    const separator = date !== previousDate ? date : ''
    previousDate = date
    return { post, separator }
  })
})

const error = ref('')
const sharePost = ref(null)
const liking = new Set()
const reposting = new Set()
let lastFocused = null

function openShare(post) {
  lastFocused = typeof document !== 'undefined' ? document.activeElement : null
  sharePost.value = post
}

// ダイアログを閉じたら、開く前に押していた「共有」ボタンへフォーカスを戻す
async function closeShare() {
  sharePost.value = null
  await nextTick()
  lastFocused?.focus?.()
}

async function removePost(post) {
  error.value = ''

  try {
    await apiDelete('/delete_post', { id: post.id })
    await refreshUser()
    emit('deleted', post)
    emit('changed')
  } catch (e) {
    error.value = e.message
  }
}

async function toggleLike(post) {
  if (liking.has(post.id)) return
  error.value = ''

  if (!isLoggedIn.value) {
    error.value = 'いいねするにはログインが必要です。'
    return
  }

  liking.add(post.id)
  try {
    const data = await apiPost('/like', { id: post.id })
    post.liked = data.liked
    post.like_count = data.like_count
    emit('like-changed', post)
  } catch (e) {
    error.value = e.message
  } finally {
    liking.delete(post.id)
  }
}

async function toggleRepost(post) {
  if (reposting.has(post.id)) return
  error.value = ''

  if (!isLoggedIn.value) {
    error.value = 'リポストするにはログインが必要です。'
    return
  }

  reposting.add(post.id)
  try {
    const data = await apiPost('/repost', { id: post.id })
    post.reposted = data.reposted
    post.repost_count = data.repost_count
  } catch (e) {
    error.value = e.message
  } finally {
    reposting.delete(post.id)
  }
}

function canDelete(post) {
  return isLoggedIn.value && currentUser.value?.id === post.user_id
}
</script>

<template>
  <div>
    <p v-if="error" class="msg msg-error" role="alert">{{ error }}</p>

    <div
      v-if="loading"
      class="timeline skeleton-list"
      aria-busy="true"
      aria-label="投稿を読み込み中"
    >
      <div v-for="n in 3" :key="n" class="skeleton-post">
        <span class="skeleton-avatar" aria-hidden="true"></span>
        <span class="skeleton-body" aria-hidden="true">
          <span class="skeleton-line skeleton-line-sm"></span>
          <span class="skeleton-line skeleton-line-lg"></span>
          <span class="skeleton-line skeleton-line-md"></span>
        </span>
      </div>
    </div>

    <div v-else-if="props.posts.length === 0" class="empty" role="status">
      <span class="empty-mark" aria-hidden="true">[ NO POSTS ]</span>
      <p class="empty-text">{{ emptyText }}</p>
    </div>

    <template v-else>
      <div class="timeline" :class="{ 'timeline-messages': messageLog }">
        <template v-for="{ post, separator } in rows" :key="post.timeline_key || post.id">
          <p v-if="separator" class="message-date">{{ separator }}</p>
          <PostItem
            :post="post"
            :can-delete="canDelete(post)"
            :message-log="messageLog"
            @delete="removePost"
            @like="toggleLike"
            @repost="toggleRepost"
            @share="openShare"
          />
        </template>
      </div>
      <div v-if="!messageLog" class="timeline-foot">
        <span>DAT No.001-{{ String(props.posts.length).padStart(3, '0') }}</span>
        <span>{{ props.footLabel }}</span>
      </div>
    </template>

    <!-- 共有ダイアログ (X / Twitter 風のカード) -->
    <ShareDialog
      v-if="sharePost"
      :post="sharePost"
      @close="closeShare"
    />
  </div>
</template>

<style scoped>
.timeline-messages {
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.message-date {
  display: flex;
  align-items: center;
  gap: .75rem;
  margin: 1rem .75rem .35rem;
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: .8rem;
}

.message-date::before,
.message-date::after {
  flex: 1;
  border-bottom: 1px dashed var(--line);
  content: '';
}
</style>
