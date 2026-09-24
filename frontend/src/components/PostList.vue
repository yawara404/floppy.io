<script setup>
import { ref } from 'vue'
import PostItem from './PostItem.vue'
import FloppyCard from './FloppyCard.vue'
import { apiGet, apiPost, apiDelete } from '../utils/api.js'
import { isLoggedIn, currentUser, refreshUser } from '../store/auth.js'

const props = defineProps({
  posts: { type: Array, default: () => [] },
  emptyText: {
    type: String,
    default: 'まだ投稿がありません。最初の投稿をしてみましょう 💾',
  },
})

const emit = defineEmits(['changed'])

const error = ref('')
const sharePost = ref(null)
const embedHtml = ref('')
const shareUrl = ref('')
const copied = ref('')

function canDelete(post) {
  return isLoggedIn.value && currentUser.value?.id === post.user_id
}

async function removePost(post) {
  error.value = ''

  try {
    await apiDelete('/delete_post.php', { id: post.id })
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
    const data = await apiPost('/like.php', { id: post.id })
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

async function openShare(post) {
  sharePost.value = post
  shareUrl.value = buildShareUrl(post)
  embedHtml.value = ''
  copied.value = ''

  try {
    const data = await apiGet(`/preview.php?id=${post.id}`)
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
    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <div v-if="props.posts.length === 0" class="empty">{{ emptyText }}</div>
    <div v-else class="timeline">
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

    <!-- 共有ダイアログ -->
    <div v-if="sharePost" class="modal-overlay" @click.self="closeShare">
      <div class="modal-window">
        <div class="modal-head">
          <span>🔗 共有</span>
          <button type="button" class="modal-close" @click="closeShare">
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
