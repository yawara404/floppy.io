<script setup>
import { ref, watch, onMounted } from 'vue'
import PostList from '~/components/PostList.vue'
import { apiGet } from '~/utils/api'

const route = useRoute()
const router = useRouter()

const q = ref(String(route.query.q || ''))
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
    const data = await apiGet('/posts?q=' + encodeURIComponent(query))
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

  // 同じクエリのまま再検索した場合は、URL が変わらず watch が発火しない
  if (route.path === '/search' && String(route.query.q || '') === query) {
    runSearch(query)
    return
  }

  router.push({ path: '/search', query: query ? { q: query } : {} })
}

// URL のクエリを唯一の情報源にして検索する
watch(
  () => route.query.q,
  (value) => {
    const query = String(value || '')
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
      <p class="section-kicker">SEARCH / ARCHIVE</p>
      <h2 class="panel-title">投稿を検索</h2>

      <form class="search-form" @submit.prevent="submit">
        <div class="search-box">
          <span class="search-icon" aria-hidden="true">⌕</span>
          <input
            v-model="q"
            class="input"
            type="search"
            placeholder="キーワード（本文・ユーザー名）"
            aria-label="検索キーワード"
          />
        </div>
        <button type="submit" class="btn btn-primary" :disabled="loading">
          {{ loading ? '検索中…' : '検索' }}
        </button>
      </form>

      <div class="search-suggest">
        <span>QUICK:</span>
        <NuxtLink :to="{ path: '/search', query: { q: '8bit' } }">8bit</NuxtLink>
        <NuxtLink :to="{ path: '/search', query: { q: 'ドット絵' } }">ドット絵</NuxtLink>
        <NuxtLink :to="{ path: '/search', query: { q: 'floppy' } }">floppy</NuxtLink>
        <NuxtLink :to="{ path: '/search', query: { q: 'youtube' } }">YouTube</NuxtLink>
      </div>

      <p class="panel-note" style="margin-top: 14px">
        本文・ユーザー名・表示名を部分一致で検索します。
      </p>
    </section>

    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <section v-if="searched" class="timeline-wrap">
      <div class="section-head">
        <div>
          <p class="section-kicker">SEARCH RESULTS</p>
          <h2 class="section-title">「{{ route.query.q }}」の検索結果</h2>
        </div>
        <span class="timeline-count">{{ posts.length }} POSTS</span>
      </div>

      <PostList
        :posts="posts"
        :empty-text="'「' + (route.query.q || '') + '」に一致する投稿はありませんでした。'"
        @changed="runSearch(route.query.q || '')"
      />
    </section>
  </div>
</template>
