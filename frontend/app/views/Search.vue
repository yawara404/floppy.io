<script setup>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import PostList from '~/components/PostList.vue'
import { apiGet, resolveMediaUrl } from '~/utils/api'

const route = useRoute()
const router = useRouter()

const q = ref(String(route.query.q || ''))
const posts = ref([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')

// --- 検索サジェスト --------------------------------------------------------
const suggestOpen = ref(false)
const suggestLoading = ref(false)
const suggestions = ref({ users: [], disks: [], posts: [] })
const activeIndex = ref(-1)
const inputRef = ref(null)

const SUGGEST_DEBOUNCE_MS = 180
let debounceTimer = null
let blurTimer = null
let requestSeq = 0
let searchSequence = 0

function emptySuggestions() {
  return { users: [], disks: [], posts: [] }
}

// キーボード操作用のフラットな候補リスト（先頭は「この言葉で検索」）
const suggestionItems = computed(() => {
  const keyword = q.value.trim()
  const items = []

  if (keyword) {
    items.push({ key: 'keyword', type: 'keyword', keyword })
  }
  for (const user of suggestions.value.users) {
    items.push({ key: `user-${user.id}`, type: 'user', user })
  }
  for (const disk of suggestions.value.disks) {
    items.push({ key: `disk-${disk.id}`, type: 'disk', disk })
  }
  for (const post of suggestions.value.posts) {
    items.push({ key: `post-${post.id}`, type: 'post', post })
  }

  return items
})

const activeDescendant = computed(() =>
  suggestOpen.value && activeIndex.value >= 0
    ? `suggest-${activeIndex.value}`
    : undefined,
)

/** 一致部分を <mark> で強調するための分割 */
function highlightParts(text, keyword) {
  const source = String(text || '')
  const needle = String(keyword || '').trim().toLowerCase()

  if (!needle) return [{ text: source, match: false }]

  const lower = source.toLowerCase()
  if (!lower.includes(needle)) return [{ text: source, match: false }]

  const parts = []
  let index = 0

  while (index < source.length) {
    const found = lower.indexOf(needle, index)
    if (found < 0) {
      parts.push({ text: source.slice(index), match: false })
      break
    }
    if (found > index) {
      parts.push({ text: source.slice(index, found), match: false })
    }
    parts.push({ text: source.slice(found, found + needle.length), match: true })
    index = found + needle.length
  }

  return parts
}

function postExcerpt(text) {
  const value = String(text || '').replace(/\s+/g, ' ').trim()
  if (!value) return '（本文なし）'
  return value.length > 72 ? `${value.slice(0, 72)}…` : value
}

function onInput(event) {
  q.value = event.target.value
  scheduleSuggest()
}

function scheduleSuggest() {
  requestSeq++
  if (debounceTimer) clearTimeout(debounceTimer)
  if (blurTimer) clearTimeout(blurTimer)
  activeIndex.value = -1

  const keyword = q.value.trim()

  if (!keyword) {
    suggestions.value = emptySuggestions()
    suggestOpen.value = false
    suggestLoading.value = false
    return
  }

  suggestOpen.value = true
  suggestLoading.value = true
  debounceTimer = setTimeout(() => loadSuggestions(keyword), SUGGEST_DEBOUNCE_MS)
}

async function loadSuggestions(keyword) {
  const seq = ++requestSeq

  try {
    const data = await apiGet('/search/suggest?q=' + encodeURIComponent(keyword))
    if (seq !== requestSeq) return

    suggestions.value = {
      users: data.users || [],
      disks: data.disks || [],
      posts: data.posts || [],
    }
  } catch (e) {
    if (seq !== requestSeq) return
    suggestions.value = emptySuggestions()
  } finally {
    if (seq === requestSeq) suggestLoading.value = false
  }
}

function closeSuggest() {
  suggestOpen.value = false
  activeIndex.value = -1
  if (blurTimer) {
    clearTimeout(blurTimer)
    blurTimer = null
  }
}

function onFocus() {
  if (!q.value.trim()) return
  suggestOpen.value = true

  // 候補がまだ無ければ取り直す
  if (
    !suggestions.value.users.length &&
    !suggestions.value.disks.length &&
    !suggestions.value.posts.length &&
    !suggestLoading.value
  ) {
    suggestLoading.value = true
    loadSuggestions(q.value.trim())
  }
}

function onBlur() {
  if (blurTimer) clearTimeout(blurTimer)
  blurTimer = setTimeout(closeSuggest, 140)
}

function scrollActiveIntoView() {
  nextTick(() => {
    document
      .getElementById(`suggest-${activeIndex.value}`)
      ?.scrollIntoView({ block: 'nearest' })
  })
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    if (suggestOpen.value) {
      event.preventDefault()
      closeSuggest()
    }
    return
  }

  if (event.key === 'ArrowDown') {
    if (!suggestOpen.value) {
      if (!q.value.trim()) return
      suggestOpen.value = true
      if (!suggestionItems.value.length && !suggestLoading.value) {
        suggestLoading.value = true
        loadSuggestions(q.value.trim())
      }
      return
    }

    const length = suggestionItems.value.length
    if (!length) return

    event.preventDefault()
    activeIndex.value =
      activeIndex.value < 0 ? 0 : (activeIndex.value + 1) % length
    scrollActiveIntoView()
    return
  }

  if (event.key === 'ArrowUp') {
    if (!suggestOpen.value) return

    const length = suggestionItems.value.length
    if (!length) return

    event.preventDefault()
    activeIndex.value =
      activeIndex.value <= 0 ? length - 1 : activeIndex.value - 1
    scrollActiveIntoView()
    return
  }

  if (event.key === 'Enter' && suggestOpen.value && activeIndex.value >= 0) {
    event.preventDefault()
    choose(suggestionItems.value[activeIndex.value])
  }
}

function choose(item) {
  if (!item) return

  closeSuggest()

  if (item.type === 'keyword') {
    submit()
    return
  }
  if (item.type === 'user') {
    router.push('/u/' + item.user.username)
    return
  }
  if (item.type === 'disk') {
    router.push('/d/' + item.disk.slug)
    return
  }
  if (item.type === 'post') {
    router.push('/p/' + item.post.id)
  }
}

async function runSearch(query) {
  const sequence = ++searchSequence
  if (!query) {
    posts.value = []
    searched.value = false
    error.value = ''
    loading.value = false
    return
  }

  searched.value = true
  loading.value = true
  error.value = ''

  try {
    const data = await apiGet('/posts?q=' + encodeURIComponent(query))
    if (sequence !== searchSequence) return
    posts.value = data.posts || []
  } catch (e) {
    if (sequence !== searchSequence) return
    error.value = e.message
    posts.value = []
  } finally {
    if (sequence === searchSequence) loading.value = false
  }
}

function submit() {
  closeSuggest()
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
    closeSuggest()
    runSearch(query)
  },
)

onMounted(() => {
  if (q.value) runSearch(q.value)
})

onBeforeUnmount(() => {
  requestSeq++
  searchSequence++
  if (debounceTimer) clearTimeout(debounceTimer)
  if (blurTimer) clearTimeout(blurTimer)
})
</script>

<template>
  <div>
    <section class="panel">
      <p class="section-kicker">SEARCH / ARCHIVE</p>
      <h2 class="panel-title">投稿を検索</h2>

      <form class="search-form" @submit.prevent="submit">
        <div class="search-field">
          <div class="search-box">
            <span class="search-icon" aria-hidden="true">⌕</span>
            <input
              ref="inputRef"
              :value="q"
              class="input"
              type="search"
              placeholder="キーワード・ユーザー・ディスク"
              role="combobox"
              aria-label="検索キーワード"
              aria-autocomplete="list"
              aria-controls="search-suggest-list"
              :aria-expanded="suggestOpen ? 'true' : 'false'"
              :aria-activedescendant="activeDescendant"
              autocomplete="off"
              @input="onInput"
              @focus="onFocus"
              @blur="onBlur"
              @keydown="onKeydown"
            />
          </div>

          <!-- 入力中のサジェスト (ユーザー / ディスク / 投稿) -->
          <div
            v-if="suggestOpen"
            id="search-suggest-list"
            class="suggest-panel"
            role="listbox"
            aria-label="検索候補"
          >
            <p
              v-if="suggestLoading && suggestionItems.length <= 1"
              class="suggest-state"
            >
              候補を検索中…
            </p>

            <template v-else>
              <div
                v-for="(item, index) in suggestionItems"
                :id="'suggest-' + index"
                :key="item.key"
                class="suggest-item"
                :class="{ active: index === activeIndex }"
                role="option"
                :aria-selected="index === activeIndex ? 'true' : 'false'"
                @mousedown.prevent="choose(item)"
                @mouseenter="activeIndex = index"
              >
                <!-- このキーワードで検索 -->
                <template v-if="item.type === 'keyword'">
                  <span class="suggest-mark" aria-hidden="true">⌕</span>
                  <span class="suggest-main">
                    <span class="suggest-title">
                      「<template
                        v-for="(part, i) in highlightParts(item.keyword, q)"
                        :key="i"
                      ><mark v-if="part.match">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template>」で検索
                    </span>
                    <span class="suggest-sub">本文・ユーザー名をまとめて検索</span>
                  </span>
                  <span class="suggest-key" aria-hidden="true">ENTER</span>
                </template>

                <!-- ユーザー -->
                <template v-else-if="item.type === 'user'">
                  <span class="suggest-avatar" aria-hidden="true">
                    <img
                      v-if="item.user.avatar_url"
                      :src="resolveMediaUrl(item.user.avatar_url)"
                      alt=""
                    />
                    <span v-else>[U]</span>
                  </span>
                  <span class="suggest-main">
                    <span class="suggest-title">
                      <template
                        v-for="(part, i) in highlightParts(item.user.display_name, q)"
                        :key="i"
                      ><mark v-if="part.match">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template>
                    </span>
                    <span class="suggest-sub">@{{ item.user.username }} · プロフィールを開く</span>
                  </span>
                  <span class="suggest-badge">USER</span>
                </template>

                <!-- ディスク -->
                <template v-else-if="item.type === 'disk'">
                  <span class="suggest-mark" aria-hidden="true">[D]</span>
                  <span class="suggest-main">
                    <span class="suggest-title">
                      <template
                        v-for="(part, i) in highlightParts(item.disk.name, q)"
                        :key="i"
                      ><mark v-if="part.match">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template>
                    </span>
                    <span class="suggest-sub">
                      /d/{{ item.disk.slug }} · {{ item.disk.post_count }} POSTS
                    </span>
                  </span>
                  <span class="suggest-badge">DISK</span>
                </template>

                <!-- 投稿 -->
                <template v-else>
                  <span class="suggest-mark" aria-hidden="true">[T]</span>
                  <span class="suggest-main">
                    <span class="suggest-title">
                      <template
                        v-for="(part, i) in highlightParts(postExcerpt(item.post.text), q)"
                        :key="i"
                      ><mark v-if="part.match">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template>
                    </span>
                    <span class="suggest-sub">@{{ item.post.username }} · 投稿を開く</span>
                  </span>
                  <span class="suggest-badge">
                    {{ item.post.kind === 'youtube' ? 'VIDEO' : item.post.kind === 'image' ? 'IMAGE' : 'POST' }}
                  </span>
                </template>
              </div>

              <p class="suggest-hint" aria-hidden="true">
                ↑↓ 選択 / Enter 決定 / Esc 閉じる
              </p>
            </template>
          </div>
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

    <RequestError v-if="error" :message="error" @retry="runSearch(String(route.query.q || ''))" />

    <section v-if="searched && !error" class="timeline-wrap" aria-live="polite">
      <div class="section-head">
        <div>
          <p class="section-kicker">SEARCH RESULTS</p>
          <h2 class="section-title">「{{ route.query.q }}」の検索結果</h2>
        </div>
        <span class="timeline-count">{{ posts.length }} POSTS</span>
      </div>

      <PostList
        :posts="posts"
        :loading="loading"
        :empty-text="'「' + (route.query.q || '') + '」に一致する投稿はありませんでした。'"
        @changed="runSearch(route.query.q || '')"
      />
    </section>
  </div>
</template>
