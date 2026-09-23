<script setup>
import { ref, watch, onMounted } from 'vue'
import PostList from '../components/PostList.vue'
import { apiGet } from '../utils/api.js'
import { drawPixel, FLOPPY_AVATAR } from '../utils/pixel.js'

const props = defineProps({
  username: { type: String, required: true },
})

const user = ref(null)
const posts = ref([])
const error = ref('')
const canvas = ref(null)

function fmt(n) {
  return (n || 0).toLocaleString('ja-JP')
}

function fmtDate(s) {
  if (!s) return ''
  const d = new Date(String(s).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(s)
  return d.toLocaleDateString('ja-JP', { year: 'numeric', month: 'long' })
}

async function load() {
  error.value = ''
  try {
    const data = await apiGet(
      '/user.php?username=' + encodeURIComponent(props.username),
    )
    user.value = data.user
    posts.value = data.posts || []
  } catch (e) {
    error.value = e.message
    user.value = null
    posts.value = []
  }
}

// アバターはプロフィール画像 → 最新投稿のドット絵 → フロッピーの順に使う
watch(
  () => [user.value?.avatar_url, user.value?.avatar_pixel],
  () => {
    if (!canvas.value) return
    drawPixel(canvas.value, user.value?.avatar_pixel || FLOPPY_AVATAR)
  },
  { flush: 'post' },
)

onMounted(load)
watch(() => props.username, load)
</script>

<template>
  <div>
    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <template v-if="user">
      <!-- プロフィールヘッダー -->
      <section class="profile-header">
        <img
          v-if="user.avatar_url"
          :src="user.avatar_url"
          class="profile-header-avatar"
          :alt="user.display_name"
        />
        <canvas
          v-else
          ref="canvas"
          class="profile-header-avatar"
          width="16"
          height="16"
        ></canvas>

        <div class="profile-header-body">
          <h2 class="profile-header-name">{{ user.display_name }}</h2>
          <div class="profile-header-handle">@{{ user.username }}</div>

          <p v-if="user.bio" class="profile-header-bio">{{ user.bio }}</p>

          <div class="profile-header-stats">
            <div class="stat">
              <b>{{ fmt(user.post_count) }}</b>
              <span>投稿</span>
            </div>
            <div class="stat">
              <b>{{ fmt(user.total_bytes) }}</b>
              <span>合計バイト</span>
            </div>
            <div class="stat">
              <b>{{ fmt(user.largest_post_bytes) }}</b>
              <span>最大</span>
            </div>
            <div class="stat">
              <b>{{ fmtDate(user.created_at) }}</b>
              <span>登録</span>
            </div>
          </div>
        </div>
      </section>

      <section class="timeline-wrap">
        <div class="timeline-head">
          <h2>@{{ user.username }} の投稿</h2>
          <span class="timeline-count">{{ posts.length }} 件</span>
        </div>

        <PostList
          :posts="posts"
          :empty-text="'@' + user.username + ' はまだ投稿していません 💾'"
          @changed="load"
        />
      </section>
    </template>
  </div>
</template>
