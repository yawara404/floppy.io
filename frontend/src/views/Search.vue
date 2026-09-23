<script setup>
import { ref, watch, onMounted } from 'vue'
import PostList from '../components/PostList.vue'
import { apiGet } from '../utils/api.js'
import { route, navigate } from '../utils/router.js'

const q = ref(route.value.query.get('q') || '')
const posts = ref([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')

async function runSearch(query) {
  if (!query) {
    posts.value = []
    searched.value = false
    error.value = ''
    return
  }

  loading.value = true
  error.value = ''

  try {
    const data = await apiGet('/posts.php?q=' + encodeURIComponent(query))
    posts.value = data.posts || []
    searched.value = true
  } catch (e) {
    error.value = e.message
    posts.value = []
  } finally {
    loading.value = false
  }
}

function submit() {
  const query = q.value.trim()
  const current = route.value.query.get('q') || ''

  if (route.value.path === '/search' && current === query) {
    // URL が変わらない場合は watch が発火しないので直接検索する
    runSearch(query)
  } else {
    navigate(query ? `/search?q=${encodeURIComponent(query)}` : '/search')
  }
}

// URL のクエリを唯一の情報源にして検索する
watch(
  () => route.value.query.get('q'),
  (value) => {
    const query = value || ''
    if (query !== q.value) q.value = query
    runSearch(query)
  },
)

onMounted(() => {
  if (q.value) runSearch(q.value)
})
</script>

<template>
  <div>
    <section class="panel">
      <h2 class="panel-title">投稿を検索</h2>

      <form class="search-form" @submit.prevent="submit">
        <input
          v-model="q"
          class="input"
          type="search"
          placeholder="キーワード（本文・ユーザー名）"
          aria-label="検索キーワード"
        />
        <button type="submit" class="btn btn-primary" :disabled="loading">
          {{ loading ? '検索中…' : '検索' }}
        </button>
      </form>

      <p class="panel-note">
        本文・ユーザー名・表示名を部分一致で検索します。
      </p>
    </section>

    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <section v-if="searched" class="timeline-wrap">
      <div class="timeline-head">
        <h2>「{{ route.query.get('q') }}」の検索結果</h2>
        <span class="timeline-count">{{ posts.length }} 件</span>
      </div>

      <PostList
        :posts="posts"
        :empty-text="'「' + (route.query.get('q') || '') + '」に一致する投稿はありませんでした。'"
        @changed="runSearch(route.query.get('q') || '')"
      />
    </section>
  </div>
</template>
