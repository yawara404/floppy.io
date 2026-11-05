<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import PostItem from './PostItem.vue'
import FloppyCard from './FloppyCard.vue'
import { apiGet, apiPost, apiDelete } from '~/utils/api'
import { isLoggedIn, currentUser, refreshUser } from '~/composables/useAuth'

const props = defineProps({
  posts: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  emptyText: {
    type: String,
    default: 'まだ投稿がありません。最初の 1 枚を書き込んでみましょう。',
  },
})

const emit = defineEmits(['changed'])

const error = ref('')
const sharePost = ref(null)
const embedHtml = ref('')
const shareUrl = ref('')
const copied = ref('')
const modalClose = ref(null)
let lastFocused = null

function onModalKeydown(event) {
  if (event.key === 'Escape') closeShare()
}

async function openShare(post) {
  lastFocused = typeof document !== 'undefined' ? document.activeElement : null
  sharePost.value = post
  shareUrl.value = buildShareUrl(post)
  embedHtml.value = ''
  copied.value = ''

  try {
    const data = await apiGet(`/preview?id=${post.id}`)
    embedHtml.value = data.html || ''
  } catch (e) {
    embedHtml.value = '（プレビューの取得に失敗しました）'
  }
}

function closeShare() {
  sharePost.value = null
  embedHtml.value = ''
  shareUrl.value = ''
  copied.value = ''
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onModalKeydown)
  }
  lastFocused?.focus?.()
}

watch(sharePost, async (post) => {
  if (typeof window === 'undefined') return

  if (post) {
    window.addEventListener('keydown', onModalKeydown)
    await nextTick()
    modalClose.value?.focus()
  } else {
    window.removeEventListener('keydown', onModalKeydown)
  }
})

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onModalKeydown)
  }
})

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
  error.value = ''

  if (!isLoggedIn.value) {
    error.value = 'いいねするにはログインが必要です。'
    return
  }

  try {
    const data = await apiPost('/like', { id: post.id })
    post.liked = data.liked
    post.like_count = data.like_count
  } catch (e) {
    error.value = e.message
  }
}

// 投稿ごとの共有リンク（ハッシュルーターの #/p/ID を開く）
function buildShareUrl(post) {
  if (typeof window === 'undefined') return ''
  const { origin, pathname } = window.location
  return `${origin}${pathname}#/p/${post.id}`
}

function canDelete(post) {
  return isLoggedIn.value && currentUser.value?.id === post.user_id
}

// クリップボードへコピー（非対応環境は textarea フォールバック）
async function copyText(text, label) {
  if (!text) return

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }

    copied.value = label
    setTimeout(() => {
      if (copied.value === label) copied.value = ''
    }, 2000)
  } catch (e) {
    copied.value = ''
  }
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

    <!-- 共有ダイアログ -->
    <div
      v-if="sharePost"
      class="modal-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="share-title"
      @click.self="closeShare"
    >
      <div class="modal-window">
        <div class="modal-head">
          <span id="share-title">[LINK] 共有</span>
          <button
            ref="modalClose"
            type="button"
            class="modal-close"
            aria-label="閉じる"
            @click="closeShare"
          >
            ×
          </button>
        </div>
        <div class="modal-body">
          <FloppyCard :post="sharePost" />

          <p class="modal-note">共有リンク:</p>
          <div class="share-link-row">
            <input
              class="input share-link"
              type="text"
              readonly
              :value="shareUrl"
              aria-label="共有リンク"
              @focus="$event.target.select()"
            />
            <button
              type="button"
              class="btn btn-sm"
              @click="copyText(shareUrl, 'link')"
            >
              {{ copied === 'link' ? 'コピー済み' : 'コピー' }}
            </button>
          </div>

          <p class="modal-note">外部サイトに貼り付ける HTML:</p>
          <textarea class="input embed-code" readonly :value="embedHtml"></textarea>
          <div class="share-actions">
            <button
              type="button"
              class="btn btn-sm"
              @click="copyText(embedHtml, 'embed')"
            >
              {{ copied === 'embed' ? 'コピー済み' : 'HTML をコピー' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
