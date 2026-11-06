<script setup>
import { ref, onMounted, watch } from 'vue'
import FloppyCard from '../components/FloppyCard.vue'
import PostList from '../components/PostList.vue'
import ReplyForm from '../components/ReplyForm.vue'
import { apiGet } from '~/utils/api'
import { isLoggedIn } from '~/composables/useAuth'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

const post = ref(null)
const replies = ref([])
const error = ref('')
const loading = ref(false)

async function load() {
  error.value = ''
  post.value = null
  replies.value = []
  loading.value = true

  try {
    const data = await apiGet(`/thread?id=${encodeURIComponent(props.id)}`)
    post.value = data.post
    replies.value = data.replies || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function onReplied(reply) {
  replies.value.push(reply)
  if (post.value) post.value.reply_count = replies.value.length
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div>
    <p v-if="loading" class="panel-note">読み込み中…</p>
    <p v-else-if="error" class="msg msg-error">{{ error }}</p>

    <template v-else-if="post">
      <section class="panel shared-post">
        <p class="section-kicker">SHARED FLOPPY / #{{ post.id }}</p>
        <h2 class="panel-title">共有された投稿</h2>

        <div class="shared-post-stage">
          <FloppyCard :post="post" />
        </div>

        <p class="panel-note">
          <NuxtLink :to="'/u/' + post.username">@{{ post.username }}</NuxtLink> の投稿です。
        </p>
        <div class="panel-actions">
          <NuxtLink class="btn" to="/">タイムラインへ戻る</NuxtLink>
          <NuxtLink class="btn btn-primary" :to="'/u/' + post.username">
            @{{ post.username }} を見る
          </NuxtLink>
        </div>
      </section>

      <!-- 返信 -->
      <section class="panel thread">
        <p class="section-kicker">REPLIES / {{ replies.length }}</p>
        <h2 class="panel-title">返信</h2>

        <p v-if="!post.replies_enabled" class="panel-note">
          この投稿は返信を受け付けていません。
        </p>
        <template v-else>
          <p class="panel-note">
            スレッドの投稿者（@{{ post.username }}）が返信を受け付けています。
            <template v-if="!isLoggedIn">返信するにはログインしてください。</template>
          </p>
          <ReplyForm :post="post" @replied="onReplied" />
        </template>

        <div class="thread-list">
          <PostList
            :posts="replies"
            :empty-text="'まだ返信はありません。'"
            @changed="load"
          />
        </div>
      </section>
    </template>
  </div>
</template>
