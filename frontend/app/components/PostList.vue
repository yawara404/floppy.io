<script setup>
import { ref, nextTick } from 'vue'
import PostItem from './PostItem.vue'
import ShareDialog from './ShareDialog.vue'
import { apiPost, apiDelete } from '~/utils/api'
import { isLoggedIn, currentUser, refreshUser } from '~/composables/useAuth'

const props = defineProps({
  posts: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyText: {
    type: String,
    default: 'まだ投稿がありません。最初の 1 枚を書き込んでみましょう。',
  },
})

const emit = defineEmits(['changed', 'like-changed'])

const error = ref('')
const sharePost = ref(null)
const liking = new Set()
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
      <div class="timeline">
        <PostItem
          v-for="post in props.posts"
          :key="post.id"
          :post="post"
          :can-delete="canDelete(post)"
          @delete="removePost"
          @like="toggleLike"
          @share="openShare"
        />
      </div>
      <div class="timeline-foot">
        <span>DAT No.001-{{ String(props.posts.length).padStart(3, '0') }}</span>
        <span>CHRONO / LIMIT 200</span>
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
