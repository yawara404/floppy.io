<script setup>
// floppy.io — ディスク一覧 (コミュニティ)
//
// 1 枚のフロッピー = 1 コミュニティ。興味のあるディスクを開いて書き込む。
// 「フォロー中」タイムラインの代わりに、参加中のディスクをここで管理する。
import { ref, computed, watch, onMounted } from 'vue'
import { apiGet, apiPost } from '~/utils/api'
import { isLoggedIn, authReady } from '~/composables/useAuth'

const disks = ref([])
const loading = ref(true)
let loadSequence = 0
const error = ref('')

const tab = ref('all') // all | joined
const query = ref('')

const creating = ref(false)
const createError = ref('')
const name = ref('')
const slug = ref('')
const description = ref('')
const slugTouched = ref(false)

const LIMIT = 40
const DESC_LIMIT = 300

const visibleDisks = computed(() => {
  const keyword = query.value.trim().toLowerCase()
  if (!keyword) return disks.value

  return disks.value.filter((disk) =>
    [disk.name, disk.slug, disk.description]
      .join(' ')
      .toLowerCase()
      .includes(keyword),
  )
})

// 英字のディスク名からは ID を自動で作る（日本語名は手入力）
watch(name, (value) => {
  if (slugTouched.value) return
  slug.value = String(value)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 32)
})

function onSlugInput() {
  slugTouched.value = true
}

function fmtDate(value) {
  if (!value) return ''
  const date = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())}`
}

async function load() {
  const sequence = ++loadSequence
  error.value = ''

  if (tab.value === 'joined' && !isLoggedIn.value) {
    disks.value = []
    loading.value = false
    return
  }

  loading.value = true
  try {
    const suffix = tab.value === 'joined' ? '?filter=joined' : ''
    const data = await apiGet(`/disks${suffix}`)
    if (sequence === loadSequence) disks.value = data.disks || []
  } catch (e) {
    if (sequence === loadSequence) error.value = e.message
  } finally {
    if (sequence === loadSequence) loading.value = false
  }
}

function selectTab(next) {
  if (tab.value === next) return
  tab.value = next
  load()
}

async function createDisk() {
  createError.value = ''

  if (!name.value.trim()) {
    createError.value = 'ディスク名を入力してください。'
    return
  }
  if (!slug.value.trim()) {
    createError.value = 'ディスク ID を入力してください。'
    return
  }

  creating.value = true
  try {
    const data = await apiPost('/disks', {
      name: name.value,
      slug: slug.value,
      description: description.value,
    })

    disks.value = [data.disk, ...disks.value]
    name.value = ''
    slug.value = ''
    description.value = ''
    slugTouched.value = false
  } catch (e) {
    createError.value = e.message
  } finally {
    creating.value = false
  }
}

// ログイン状態が確定してから「参加中」タブを読み込む
watch(
  () => [isLoggedIn.value, authReady.value],
  () => {
    if (isLoggedIn.value && tab.value === 'joined') load()
  },
)

onMounted(load)
</script>

<template>
  <div class="disks">
    <section class="disks-hero">
      <p class="section-kicker">DISK LIBRARY / COMMUNITY</p>
      <h1 class="disks-title">ディスク</h1>
      <p class="disks-lead">
        1 枚のフロッピーが 1 つのコミュニティ。
        興味のあるディスクを開いて、最初の 1 枚を書き込んでください。
      </p>
    </section>

    <div class="timeline-head disks-toolbar">
      <nav class="feed-tabs" aria-label="ディスクの絞り込み">
        <button
          type="button"
          class="feed-tab"
          :class="{ active: tab === 'all' }"
          :aria-pressed="tab === 'all' ? 'true' : 'false'"
          @click="selectTab('all')"
        >
          すべて
        </button>
        <button
          v-if="isLoggedIn"
          type="button"
          class="feed-tab"
          :class="{ active: tab === 'joined' }"
          :aria-pressed="tab === 'joined' ? 'true' : 'false'"
          @click="selectTab('joined')"
        >
          参加中
        </button>
      </nav>

      <input
        v-model="query"
        class="input disk-search"
        type="search"
        placeholder="ディスクを検索"
        aria-label="ディスクを検索"
      />
    </div>

    <RequestError v-if="error" :message="error" @retry="load" />
    <p v-else-if="loading" class="panel-note">読み込み中…</p>

    <div v-else-if="visibleDisks.length === 0" class="empty" role="status">
      <span class="empty-mark" aria-hidden="true">[ NO DISKS ]</span>
      <p class="empty-text">
        {{
          query.trim()
            ? '「' + query.trim() + '」に一致するディスクはありません。別の言葉で検索してください。'
            : tab === 'joined'
            ? '参加中のディスクはまだありません。気になるディスクを探してみましょう。'
            : 'まだディスクがありません。最初の 1 枚をフォーマットしてみましょう。'
        }}
      </p>
      <button v-if="query.trim()" type="button" class="btn btn-sm" @click="query = ''">検索をクリア</button>
      <button v-else-if="tab === 'joined'" type="button" class="btn btn-sm" @click="selectTab('all')">すべてのディスクを見る</button>
    </div>

    <div v-else class="disk-grid">
      <NuxtLink
        v-for="disk in visibleDisks"
        :key="disk.id"
        class="disk-card"
        :to="'/d/' + disk.slug"
      >
        <span class="disk-card-head">
          <span class="disk-card-icon" aria-hidden="true">[D]</span>
          <span class="disk-card-name">{{ disk.name }}</span>
          <span v-if="disk.is_member" class="disk-card-joined">JOINED</span>
        </span>
        <span class="disk-card-slug">/d/{{ disk.slug }}</span>
        <span class="disk-card-desc">
          {{ disk.description || '説明はまだありません。' }}
        </span>
        <span class="disk-card-foot">
          <span>{{ disk.post_count }} POSTS</span>
          <span>{{ disk.member_count }} MEMBERS</span>
          <span v-if="disk.last_post_at">{{ fmtDate(disk.last_post_at) }}</span>
          <span v-else>EMPTY</span>
        </span>
      </NuxtLink>
    </div>

    <!-- ディスク作成 -->
    <section v-if="isLoggedIn" class="panel disk-create">
      <p class="section-kicker">FORMAT NEW DISK</p>
      <h2 class="panel-title">ディスクを作成</h2>
      <p class="panel-note">
        名前と ID（URL）を決めて、新しいコミュニティをフォーマットします。
      </p>

      <div class="disk-form">
        <div class="field">
          <label class="field-label" for="disk-name">
            ディスク名（{{ LIMIT }} 文字まで）
          </label>
          <input
            id="disk-name"
            v-model="name"
            class="input"
            type="text"
            :maxlength="LIMIT"
            placeholder="例: レトロPC"
          />
        </div>

        <div class="field">
          <label class="field-label" for="disk-slug">
            ディスク ID（URL: /d/…）
          </label>
          <input
            id="disk-slug"
            v-model="slug"
            class="input"
            type="text"
            maxlength="32"
            placeholder="例: retro-pc"
            pattern="[a-z0-9][a-z0-9-]*"
            @input="onSlugInput"
          />
          <p class="disk-hint">半角英数字とハイフン（2〜32 文字）。</p>
        </div>

        <div class="field">
          <label class="field-label" for="disk-description">
            説明（{{ DESC_LIMIT }} 文字まで）
          </label>
          <textarea
            id="disk-description"
            v-model="description"
            class="input"
            rows="3"
            :maxlength="DESC_LIMIT"
            placeholder="どんな書き込みを集めるディスクか、簡単に説明してください。"
          ></textarea>
        </div>
      </div>

      <p v-if="createError" class="msg msg-error" role="alert">
        {{ createError }}
      </p>

      <div class="panel-actions">
        <button
          type="button"
          class="btn btn-primary"
          :disabled="creating"
          @click="createDisk"
        >
          {{ creating ? 'フォーマット中…' : 'ディスクを作成' }}
        </button>
      </div>
    </section>

    <div v-else class="callout">
      <span>ディスクを作成するにはログインが必要です。</span>
      <NuxtLink class="btn btn-primary" to="/login">ログイン</NuxtLink>
      <NuxtLink class="btn" to="/register">新規登録</NuxtLink>
    </div>
  </div>
</template>
