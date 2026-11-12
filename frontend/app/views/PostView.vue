<script setup>
// floppy.io — 投稿の個別ビュー
//
// mixi のコメント欄、旧 Twitter のスレッド / アクション行、Miiverse の
// 「ボード + 共感 + 吹き出しコメント」を合わせた 1 ページ。
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import PostDetail from '../components/PostDetail.vue'
import ReplyBubble from '../components/ReplyBubble.vue'
import ReplyForm from '../components/ReplyForm.vue'
import ShareDialog from '../components/ShareDialog.vue'
import { apiGet, apiPost, apiDelete } from '~/utils/api'
import { isLoggedIn, currentUser } from '~/composables/useAuth'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

const post = ref(null)
const replies = ref([])
const error = ref('')
const actionError = ref('')
const loading = ref(true)
let loadSequence = 0
const shareOpen = ref(false)
const replySection = ref(null)

const canDeleteMain = computed(
  () =>
    isLoggedIn.value &&
    post.value &&
    Number(currentUser.value?.id) === Number(post.value.user_id),
)

function canDeleteReply(reply) {
  return (
    isLoggedIn.value &&
    Number(currentUser.value?.id) === Number(reply.user_id)
  )
}

async function load() {
  const sequence = ++loadSequence
  error.value = ''
  actionError.value = ''
  post.value = null
  replies.value = []
  loading.value = true

  try {
    const data = await apiGet(`/thread?id=${encodeURIComponent(props.id)}`)
    if (sequence !== loadSequence) return
    post.value = data.post
    replies.value = data.replies || []
  } catch (e) {
    if (sequence === loadSequence) error.value = e.message
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

async function toggleLike(target) {
  if (!target) return
  actionError.value = ''

  if (!isLoggedIn.value) {
    actionError.value = '共感するにはログインが必要です。'
    return
  }

  try {
    const data = await apiPost('/like', { id: target.id })
    target.liked = data.liked
    target.like_count = data.like_count
  } catch (e) {
    actionError.value = e.message
  }
}

async function toggleRepost(target) {
  if (!target) return
  actionError.value = ''

  if (!isLoggedIn.value) {
    actionError.value = 'リポストするにはログインが必要です。'
    return
  }

  try {
    const data = await apiPost('/repost', { id: target.id })
    target.reposted = data.reposted
    target.repost_count = data.repost_count
  } catch (e) {
    actionError.value = e.message
  }
}

function openShare() {
  shareOpen.value = true
}

function closeShare() {
  shareOpen.value = false
}

function onReplied(reply) {
  replies.value.push(reply)
  if (post.value) post.value.reply_count = replies.value.length
}

async function focusReply() {
  await nextTick()
  replySection.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })

  // スクロール後に返信欄へフォーカスする
  setTimeout(() => {
    replySection.value?.querySelector('textarea')?.focus()
  }, 260)
}

async function deletePost(target) {
  if (!target) return
  actionError.value = ''

  try {
    await apiDelete('/delete_post', { id: target.id })
    await navigateTo('/')
  } catch (e) {
    actionError.value = e.message
  }
}

async function deleteReply(reply) {
  actionError.value = ''

  try {
    await apiDelete('/delete_post', { id: reply.id })
    replies.value = replies.value.filter((item) => item.id !== reply.id)
    if (post.value) {
      post.value.reply_count = Math.max(
        0,
        Number(post.value.reply_count || 0) - 1,
      )
    }
  } catch (e) {
    actionError.value = e.message
  }
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div class="detail-page">
    <p v-if="loading" class="panel-note">読み込み中…</p>
    <RequestError v-else-if="error" :message="error" @retry="load" />

    <template v-else-if="post">
      <nav class="detail-breadcrumb" aria-label="パンくず">
        <NuxtLink to="/">タイムライン</NuxtLink>
        <span aria-hidden="true">/</span>
        <span>No.{{ post.id }}</span>
      </nav>

      <PostDetail
        :post="post"
        :can-delete="canDeleteMain"
        @like="toggleLike"
        @repost="toggleRepost"
        @share="openShare"
        @reply="focusReply"
        @delete="deletePost"
      />

      <p v-if="actionError" class="msg msg-error" role="alert">{{ actionError }}</p>

      <section v-if="post.replies_enabled" ref="replySection" class="panel detail-thread">
        <div class="detail-thread-head">
          <div>
            <p class="section-kicker">REPLIES / {{ replies.length }}</p>
            <h2 class="panel-title">返信</h2>
          </div>
          <span class="detail-thread-count">
            {{ String(post.reply_count || replies.length).padStart(2, '0') }} COMMENTS
          </span>
        </div>

        <ReplyForm :post="post" @replied="onReplied" />

        <div v-if="replies.length" class="reply-bubbles">
          <ReplyBubble
            v-for="reply in replies"
            :key="reply.id"
            :reply="reply"
            :can-delete="canDeleteReply(reply)"
            @like="toggleLike"
            @delete="deleteReply"
          />
        </div>

        <div v-else class="detail-thread-empty">
          <span class="empty-mark" aria-hidden="true">[ NO REPLIES ]</span>
          <p>まだ返信はありません。最初のコメントを書いてみましょう。</p>
        </div>
      </section>

      <ShareDialog v-if="shareOpen" :post="post" @close="closeShare" />
    </template>
  </div>
</template>
