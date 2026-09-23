<script setup>
import { ref, onMounted } from 'vue'
import Composer from '../components/Composer.vue'
import PostList from '../components/PostList.vue'
import { apiGet } from '../utils/api.js'
import { isLoggedIn } from '../store/auth.js'

const posts = ref([])
const error = ref('')

async function load() {
  error.value = ''
  try {
    const data = await apiGet('/posts.php')
    posts.value = data.posts || []
  } catch (e) {
    error.value = e.message
  }
}

function onPosted(post) {
  posts.value.unshift(post)
}

onMounted(load)
</script>

<template>
  <div>
    <Composer v-if="isLoggedIn" @posted="onPosted" />

    <div v-else class="callout">
      <span>投稿するにはアカウントが必要です。</span>
      <a class="btn btn-primary" href="#/register">新規登録</a>
      <a class="btn" href="#/login">ログイン</a>
    </div>

    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <section class="timeline-wrap">
      <div class="timeline-head">
        <h2>タイムライン</h2>
        <span class="timeline-count">{{ posts.length }} 件</span>
      </div>

      <PostList :posts="posts" @changed="load" />
    </section>
  </div>
</template>
