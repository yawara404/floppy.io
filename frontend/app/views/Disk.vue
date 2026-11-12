<script setup>
// floppy.io — ディスク (コミュニティ) 1 枚分のページ
import { ref, computed, onMounted, watch } from 'vue'
import Composer from '../components/Composer.vue'
import PostList from '../components/PostList.vue'
import { apiGet, apiPost } from '~/utils/api'
import { isLoggedIn } from '~/composables/useAuth'
import { formatDate } from '~/utils/format'

const props = defineProps({
  slug: { type: String, required: true },
})

const disk = ref(null)
const posts = ref([])
const loading = ref(true)
let loadSequence = 0
const error = ref('')
const joining = ref(false)

// 参加中なら書き込める
const canWrite = computed(
  () => isLoggedIn.value && disk.value?.is_member === true,
)

const lastPostLabel = computed(() => formatDate(disk.value?.last_post_at))

async function load() {
  const sequence = ++loadSequence
  error.value = ''
  disk.value = null
  posts.value = []
  loading.value = true

  try {
    const data = await apiGet(`/disks/${encodeURIComponent(props.slug)}`)
    if (sequence !== loadSequence) return
    disk.value = data.disk
    posts.value = data.posts || []
  } catch (e) {
    if (sequence === loadSequence) error.value = e.message
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

async function toggleJoin() {
  if (!disk.value || joining.value) return

  if (!isLoggedIn.value) {
    await navigateTo('/login')
    return
  }

  joining.value = true
  error.value = ''

  try {
    const data = await apiPost('/disks/join', { slug: disk.value.slug })
    disk.value.is_member = data.is_member
    disk.value.member_count = data.member_count
  } catch (e) {
    error.value = e.message
  } finally {
    joining.value = false
  }
}

function onPosted(post) {
  posts.value.unshift(post)
  if (disk.value) disk.value.post_count = (disk.value.post_count || 0) + 1
}

onMounted(load)
watch(() => props.slug, load)
</script>

<template>
  <div class="disk-page">
    <p v-if="loading" class="panel-note">読み込み中…</p>

    <RequestError v-else-if="error && !disk" :message="error" @retry="load" />

    <div v-else-if="!disk" class="empty" role="status">
      <span class="empty-mark" aria-hidden="true">[ DISK NOT FOUND ]</span>
      <p class="empty-text">{{ error || 'ディスクが見つかりません。' }}</p>
      <div class="panel-actions">
        <NuxtLink class="btn" to="/disks">ディスク一覧へ</NuxtLink>
      </div>
    </div>

    <template v-else>
      <section class="panel disk-hero">
        <p class="section-kicker">DISK / {{ disk.slug }}</p>

        <div class="disk-hero-head">
          <span class="disk-hero-icon" aria-hidden="true">[D]</span>
          <h1 class="disk-hero-title">{{ disk.name }}</h1>
          <span v-if="disk.is_member" class="disk-card-joined">JOINED</span>
        </div>

        <p class="disk-hero-desc">
          {{ disk.description || 'このディスクにはまだ説明がありません。' }}
        </p>

        <div class="disk-hero-stats">
          <span>{{ disk.post_count }} POSTS</span>
          <span>{{ disk.member_count }} MEMBERS</span>
          <span>OWNER @{{ disk.owner_username }}</span>
          <span v-if="lastPostLabel">LAST {{ lastPostLabel }}</span>
        </div>

        <div class="panel-actions">
          <button
            v-if="isLoggedIn"
            type="button"
            class="btn"
            :class="{ 'btn-primary': !disk.is_member }"
            :disabled="joining"
            @click="toggleJoin"
          >
            {{
              joining
                ? '処理中…'
                : disk.is_member
                  ? '参加中（退出する）'
                  : 'このディスクに参加'
            }}
          </button>
          <NuxtLink v-else class="btn btn-primary" to="/login">
            ログインして参加
          </NuxtLink>
          <NuxtLink class="btn" to="/disks">ディスク一覧</NuxtLink>
        </div>
      </section>

      <p v-if="error" class="msg msg-error" role="alert">{{ error }}</p>

      <!-- 書き込みフォーム（参加メンバーだけ） -->
      <template v-if="canWrite">
        <div class="section-head">
          <div>
            <p class="section-kicker">WRITE TO DISK / {{ disk.slug }}</p>
            <h2 class="section-title">このディスクに書き込む</h2>
          </div>
          <span class="timeline-count">DISK READY</span>
        </div>
        <Composer :disk="disk" @posted="onPosted" />
      </template>

      <div v-else-if="isLoggedIn" class="callout">
        <span>
          このディスクに書き込むには参加が必要です。
          （{{ disk.member_count }} 人が参加中）
        </span>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="joining"
          @click="toggleJoin"
        >
          {{ joining ? '処理中…' : '参加する' }}
        </button>
      </div>

      <div v-else class="callout">
        <span>このディスクに書き込むにはログインと参加が必要です。</span>
        <NuxtLink class="btn btn-primary" to="/login">ログイン</NuxtLink>
        <NuxtLink class="btn" to="/register">新規登録</NuxtLink>
      </div>

      <section class="timeline-wrap">
        <div class="section-head">
          <div>
            <p class="section-kicker">DISK FEED / CHRONOLOGICAL</p>
            <h2 class="section-title">書き込み</h2>
          </div>
          <span class="timeline-count">{{ posts.length }} POSTS</span>
        </div>

        <PostList
          :posts="posts"
          :empty-text="'このディスクはまだ空です。最初の 1 枚を書き込んでみましょう。'"
          @changed="load"
        />
      </section>
    </template>
  </div>
</template>
