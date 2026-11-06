<script setup>
import { ref, watch, onMounted } from 'vue'
import PostList from '../components/PostList.vue'
import ProfileEditor from '../components/ProfileEditor.vue'
import { apiGet, apiPost } from '~/utils/api'
import { isLoggedIn, refreshUser } from '~/composables/useAuth'
import { drawPixel, FLOPPY_AVATAR } from '~/utils/pixel'

const props = defineProps({
  username: { type: String, required: true },
})

const user = ref(null)
const posts = ref([])
const error = ref('')
const loading = ref(false)
const followError = ref('')
const followBusy = ref(false)
const canvas = ref(null)
const editing = ref(false)

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
  followError.value = ''
  loading.value = true
  try {
    const data = await apiGet(
      '/user?username=' + encodeURIComponent(props.username),
    )
    user.value = data.user
    posts.value = data.posts || []
  } catch (e) {
    error.value = e.message
    user.value = null
    posts.value = []
  } finally {
    loading.value = false
  }
}

// フォローの付け外し（トグル）
async function toggleFollow() {
  if (!user.value || followBusy.value) return

  followError.value = ''
  followBusy.value = true

  try {
    const data = await apiPost('/follow', { username: user.value.username })
    user.value.following = data.following
    user.value.follower_count = data.follower_count
    // サイドバーに自分のフォロー数が出ているので更新しておく
    await refreshUser()
  } catch (e) {
    followError.value = e.message
  } finally {
    followBusy.value = false
  }
}

// アバターは 32×32 アイコン → プロフィール画像 → 最新投稿のドット絵 → フロッピー
watch(
  () => [user.value?.icon_pixel, user.value?.avatar_url, user.value?.avatar_pixel],
  () => {
    if (!canvas.value) return
    drawPixel(
      canvas.value,
      user.value?.icon_pixel ||
        user.value?.avatar_pixel ||
        FLOPPY_AVATAR,
    )
  },
  { flush: 'post' },
)

onMounted(load)
watch(() => props.username, () => {
  editing.value = false
  load()
})

// プロフィール編集を保存したら、表示中のユーザー情報を取り直す
async function onProfileSaved() {
  editing.value = false
  await load()
  await refreshUser()
}
</script>

<template>
  <div>
    <p v-if="error" class="msg msg-error">{{ error }}</p>

    <template v-if="user">
      <!-- プロフィールヘッダー -->
      <section class="profile-header">
        <div class="profile-cover" aria-hidden="true">
          <span class="profile-cover-code">USER / {{ user.username.toUpperCase() }}</span>
        </div>

        <div class="profile-header-main">
          <div class="profile-avatar-wrap">
            <img
              v-if="!user.icon_pixel && user.avatar_url"
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
            <span class="avatar-led" aria-hidden="true"></span>
          </div>

          <div class="profile-header-body">
            <h2 class="profile-header-name">{{ user.display_name }}</h2>
            <div class="profile-header-handle">@{{ user.username }}</div>

            <p v-if="user.bio" class="profile-header-bio">{{ user.bio }}</p>

            <p
              class="profile-header-replies"
              :class="{ on: user.allow_replies }"
            >
              <span aria-hidden="true">[↩]</span>
              {{ user.allow_replies ? '返信を受け付けています' : '返信は受け付けていません' }}
            </p>

            <p v-if="followError" class="msg msg-error">{{ followError }}</p>

            <div class="profile-header-stats">
              <div class="stat">
                <b>{{ fmt(user.post_count) }}</b>
                <span>投稿</span>
              </div>
              <div class="stat">
                <b>{{ fmt(user.following_count) }}</b>
                <span>フォロー</span>
              </div>
              <div class="stat">
                <b>{{ fmt(user.follower_count) }}</b>
                <span>フォロワー</span>
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

          <!-- 自分のプロフィール: プロフィール編集 -->
          <div v-if="user.is_self" class="profile-header-actions self-actions">
            <button
              type="button"
              class="btn btn-primary"
              :aria-expanded="editing ? 'true' : 'false'"
              @click="editing = !editing"
            >
              {{ editing ? '編集を閉じる' : 'プロフィールを編集' }}
            </button>
            <NuxtLink class="btn" to="/settings">設定</NuxtLink>
          </div>

          <!-- フォロー操作（自分自身のプロフィールには出さない） -->
          <div v-else class="profile-header-actions">
            <template v-if="isLoggedIn">
              <button
                type="button"
                class="btn btn-primary follow-btn"
                :class="{ following: user.following }"
                :disabled="followBusy"
                :title="user.following ? '@' + user.username + ' のフォローを外す' : '@' + user.username + ' をフォローする'"
                @click="toggleFollow"
              >
                {{ user.following ? 'フォロー中' : 'フォローする' }}
              </button>
            </template>
            <NuxtLink v-else class="btn btn-primary" to="/login">ログインしてフォロー</NuxtLink>
          </div>
        </div>
      </section>

      <!-- プロフィール画面からのインライン編集（本人のみ） -->
      <ProfileEditor
        v-if="user.is_self && editing"
        :user="user"
        @saved="onProfileSaved"
        @cancel="editing = false"
      />

      <section class="timeline-wrap">
        <div class="timeline-head">
          <h2>@{{ user.username }} の投稿</h2>
          <span class="timeline-count">{{ posts.length }} 件</span>
        </div>

        <PostList
          :posts="posts"
          :loading="loading"
          :empty-text="'@' + user.username + ' はまだ投稿していません'"
          @changed="load"
        />
      </section>
    </template>
  </div>
</template>
