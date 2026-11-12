<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import PostList from '../components/PostList.vue'
import ProfileEditor from '../components/ProfileEditor.vue'
import { apiGet, apiPost, resolveMediaUrl } from '~/utils/api'
import { isLoggedIn, currentUser, authReady, refreshUser } from '~/composables/useAuth'
import { drawAvatar } from '~/utils/pixel'
import { formatMonth, formatNumber } from '~/utils/format'

const props = defineProps({
  username: { type: String, required: true },
  connectionsKind: { type: String, default: '' },
})

const route = useRoute()
const router = useRouter()
const profilePath = computed(() => '/u/' + encodeURIComponent(props.username))
const activeTab = computed(() => !props.connectionsKind && route.query.tab === 'likes' ? 'likes' : 'posts')
function tabLocation(tab) {
  const query = { ...route.query }
  delete query.connections
  if (tab === 'posts') delete query.tab
  else query.tab = tab
  return { path: profilePath.value, query }
}
function selectTab(tab) { router.push(tabLocation(tab)) }

// 以前の一覧リンクも専用ページへつなぐ。
watch(() => [props.connectionsKind, route.query.tab, route.query.connections], () => {
  if (props.connectionsKind) return
  const kind = ['following', 'followers'].includes(route.query.tab)
    ? route.query.tab : route.query.connections
  if (['following', 'followers'].includes(kind)) {
    router.replace(`${profilePath.value}/${kind}`)
  }
}, { immediate: true })

const user = ref(null)
const posts = ref([])
const error = ref('')
const loading = ref(true)
let loadSequence = 0
const followError = ref('')
const followBusy = ref(false)
const canvas = ref(null)
const editing = ref(false)

const isOwnProfile = computed(() => authReady.value && isLoggedIn.value && user.value
  && Number(user.value.id) === Number(currentUser.value?.id))
const likes = ref([])
const likesLoading = ref(false)
const likesError = ref('')
const likesNextOffset = ref(null)
let likesSequence = 0

async function loadLikes(append = false) {
  if (!isOwnProfile.value) return
  const request = ++likesSequence
  const offset = append ? likesNextOffset.value : 0
  likesLoading.value = true
  likesError.value = ''
  if (!append) { likes.value = []; likesNextOffset.value = null }
  try {
    const data = await apiGet(`/users/${encodeURIComponent(props.username)}/likes?offset=${offset}`)
    if (request !== likesSequence || !isOwnProfile.value) return
    const existing = new Set(likes.value.map((post) => post.id))
    likes.value = append ? [...likes.value, ...data.posts.filter((post) => !existing.has(post.id))] : data.posts
    likesNextOffset.value = data.next_offset
  } catch (e) {
    if (request === likesSequence) likesError.value = e.message
  } finally {
    if (request === likesSequence) likesLoading.value = false
  }
}

// タブ・プロフィール・認証が変わったら非公開データを直ちに破棄する。
watch(() => [props.username, activeTab.value, isOwnProfile.value], () => {
  likesSequence++
  likes.value = []
  likesNextOffset.value = null
  likesError.value = ''
  likesLoading.value = false
  if (activeTab.value === 'likes' && isOwnProfile.value) loadLikes()
}, { immediate: true, flush: 'sync' })

function onLikeChanged(post) {
  if (!post.liked) {
    likes.value = likes.value.filter((item) => item.id !== post.id)
    if (likesNextOffset.value !== null) likesNextOffset.value = Math.max(0, likesNextOffset.value - 1)
  }
}

async function load() {
  const sequence = ++loadSequence
  error.value = ''
  followError.value = ''
  loading.value = true
  try {
    const data = await apiGet(
      '/user?username=' + encodeURIComponent(props.username),
    )
    if (sequence !== loadSequence) return
    user.value = data.user
    posts.value = data.posts || []
  } catch (e) {
    if (sequence !== loadSequence) return
    error.value = e.message
    user.value = null
    posts.value = []
  } finally {
    if (sequence === loadSequence) loading.value = false
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
    drawAvatar(
      canvas.value,
      user.value?.icon_pixel || user.value?.avatar_pixel,
    )
  },
  { flush: 'post' },
)

watch(() => [props.username, authReady.value, currentUser.value?.id], () => {
  loadSequence++
  user.value = null
  posts.value = []
  editing.value = false
  if (authReady.value) load()
}, { immediate: true })
onBeforeUnmount(() => { loadSequence++; likesSequence++ })

// プロフィール編集を保存したら、表示中のユーザー情報を取り直す
async function onProfileSaved() {
  editing.value = false
  await load()
  await refreshUser()
}
</script>

<template>
  <div>
    <p v-if="loading && !user" class="panel-note" role="status">プロフィールを読み込み中…</p>
    <RequestError v-else-if="error" :message="error" @retry="load" />

    <template v-if="user">
      <section
        v-if="connectionsKind"
        class="profile-connections-page"
        :aria-label="connectionsKind === 'following' ? 'フォロー中のユーザー' : 'フォロワー'"
      >
        <!-- Twitter と同じく、フォロー中 / フォロワー は独立した画面。
             一覧の中にタブは置かず、プロフィールの件数から行き来する。 -->
        <header class="connections-page-header">
          <NuxtLink :to="profilePath" class="link-btn connections-back">← 投稿へ戻る</NuxtLink>
          <div class="connections-page-heading">
            <h1 class="connections-page-title">{{ connectionsKind === 'following' ? 'フォロー中' : 'フォロワー' }}</h1>
            <p class="connections-page-handle">@{{ user.username }}</p>
          </div>
        </header>
        <ConnectionsList :username="user.username" :kind="connectionsKind" @changed="load" />
      </section>

      <template v-else>
        <!-- プロフィールヘッダー -->
        <section class="profile-header">
          <div class="profile-cover" aria-hidden="true">
            <span class="profile-cover-code">USER / {{ user.username.toUpperCase() }}</span>
          </div>

          <div class="profile-header-main">
            <div class="profile-avatar-wrap">
              <img
                v-if="!user.icon_pixel && user.avatar_url"
                :src="resolveMediaUrl(user.avatar_url)"
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
              <h1 class="profile-header-name">{{ user.display_name }}</h1>
              <div class="profile-header-handle">@{{ user.username }}</div>

              <p v-if="user.bio" class="profile-header-bio">{{ user.bio }}</p>

              <!-- Twitter と同じく、フォロー中 / フォロワーは本文下のリンクとして独立表示 -->
              <div class="profile-follow-links">
                <NuxtLink :to="profilePath + '/following'"><b>{{ formatNumber(user.following_count) }}</b> フォロー中</NuxtLink>
                <NuxtLink :to="profilePath + '/followers'"><b>{{ formatNumber(user.follower_count) }}</b> フォロワー</NuxtLink>
              </div>

              <p
                class="profile-header-replies"
                :class="{ on: user.allow_replies }"
              >
                <span aria-hidden="true">[↩]</span>
                {{ user.allow_replies ? '返信を受け付けています' : '返信は受け付けていません' }}
              </p>

              <p v-if="followError" class="msg msg-error">{{ followError }}</p>

              <div class="profile-header-stats">
                <NuxtLink class="stat stat-link" :to="tabLocation('posts')" :aria-current="activeTab === 'posts' ? 'page' : undefined">
                  <b>{{ formatNumber(user.post_count) }}</b>
                  <span>投稿</span>
                </NuxtLink>
                <div class="stat">
                  <b>{{ formatNumber(user.total_bytes) }}</b>
                  <span>合計バイト</span>
                </div>
                <div class="stat">
                  <b>{{ formatNumber(user.largest_post_bytes) }}</b>
                  <span>最大</span>
                </div>
                <div class="stat">
                  <b>{{ formatMonth(user.created_at) }}</b>
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

        <section class="timeline-wrap profile-activity" aria-label="プロフィールの履歴">
          <nav class="profile-activity-tabs feed-tabs" aria-label="プロフィールの表示切り替え">
            <button type="button" class="feed-tab" :class="{ active: activeTab === 'posts' }" :aria-pressed="activeTab === 'posts'" @click="selectTab('posts')">投稿</button>
            <button v-if="isOwnProfile" type="button" class="feed-tab" :class="{ active: activeTab === 'likes' }" :aria-pressed="activeTab === 'likes'" @click="selectTab('likes')">いいね履歴 <span class="private-tab-label">非公開</span></button>
          </nav>

          <template v-if="activeTab === 'likes'">
            <div v-if="!isOwnProfile" class="empty" role="status">
              <p class="empty-text">いいね履歴は本人だけが閲覧できます。</p>
            </div>
            <template v-else>
              <p class="profile-private-note">この履歴はあなただけに表示されます。他のユーザーには一覧・件数ともに公開されません。</p>
              <RequestError v-if="likesError" :message="likesError" @retry="loadLikes(likes.length > 0)" />
              <PostList
                v-if="!likesError || likes.length"
                :posts="likes"
                :loading="likesLoading && !likes.length"
                empty-text="まだいいねした投稿はありません。気に入った投稿にいいねすると、ここに残ります。"
                @changed="loadLikes()"
                @like-changed="onLikeChanged"
              />
              <div v-if="likesNextOffset !== null && !likesError" class="profile-load-more">
                <button type="button" class="btn" :disabled="likesLoading" @click="loadLikes(true)">{{ likesLoading ? '読み込み中…' : 'さらに表示' }}</button>
              </div>
            </template>
          </template>
          <template v-else>
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
          </template>
        </section>
      </template>
    </template>
  </div>
</template>
