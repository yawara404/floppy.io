<script setup>
import { ref } from 'vue'
import PostItem from './PostItem.vue'
import FloppyCard from './FloppyCard.vue'
import { apiGet, apiDelete } from '../utils/api.js'
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
const previewPost = ref(null)
const embedHtml = ref('')

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

async function openPreview(post) {
  previewPost.value = post
  embedHtml.value = ''
  try {
    const data = await apiGet(`/preview.php?id=${post.id}`)
    embedHtml.value = data.html || ''
  } catch (e) {
    embedHtml.value = '（プレビューの取得に失敗しました）'
  }
}

function closePreview() {
  previewPost.value = null
  embedHtml.value = ''
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
        @preview="openPreview"
      />
    </div>

    <!-- 埋め込みプレビュー モーダル -->
    <div v-if="previewPost" class="modal-overlay" @click.self="closePreview">
      <div class="modal-window">
        <div class="modal-head">
          <span>🔗 埋め込みプレビュー</span>
          <button type="button" class="modal-close" @click="closePreview">
            ×
          </button>
        </div>
        <div class="modal-body">
          <FloppyCard :post="previewPost" />
          <p class="modal-note">
            外部サイトに貼り付ける HTML（プレビュー API が返すスニペット）:
          </p>
          <textarea class="input embed-code" readonly :value="embedHtml"></textarea>
        </div>
      </div>
    </div>
  </div>
</template>
