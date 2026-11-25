<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import Composer from '../components/Composer.vue'
import PostList from '../components/PostList.vue'
import DiskBotPanel from '../components/DiskBotPanel.vue'
import { apiGet, apiPost } from '~/utils/api'
import { authReady, currentUser, isLoggedIn } from '~/composables/useAuth'
import { formatNumber } from '~/utils/format'

const props = defineProps({
  slug: { type: String, required: true },
  openBot: { type: Boolean, default: false },
})

const disk = ref(null)
const posts = ref([])
const joinedDisks = ref([])
const loading = ref(true)
const refreshing = ref(false)
const joining = ref(false)
const error = ref('')
const history = ref(null)
const historyContent = ref(null)
const botDialog = ref(null)
const atLatest = ref(true)
let loadSequence = 0
let joinedSequence = 0
let postChanges = 0

const canWrite = computed(() => isLoggedIn.value && disk.value?.is_member === true)
const messages = computed(() => [...posts.value].reverse())

function scrollToLatest() {
  const log = history.value
  if (!log) return
  log.scrollTop = log.scrollHeight
  atLatest.value = true
}

function onHistoryScroll() {
  const log = history.value
  if (log) atLatest.value = log.scrollHeight - log.clientHeight - log.scrollTop <= 48
}

watch([history, historyContent], ([log, content], _, onCleanup) => {
  if (!log || !content) return
  scrollToLatest()
  const observer = new ResizeObserver(() => {
    if (atLatest.value) scrollToLatest()
  })
  observer.observe(log)
  observer.observe(content)
  onCleanup(() => observer.disconnect())
}, { flush: 'post' })

function openBotPanel() {
  if (botDialog.value && !botDialog.value.open) botDialog.value.showModal()
}

watch([botDialog, () => props.openBot], ([, open]) => {
  if (open) openBotPanel()
}, { flush: 'post' })

async function load(keepView = false) {
  const sequence = ++loadSequence
  const requestedSlug = props.slug
  const requestedPostChanges = postChanges
  error.value = ''
  loading.value = !keepView
  refreshing.value = keepView
  if (!keepView) {
    disk.value = null
    posts.value = []
  }

  try {
    const data = await apiGet(`/disks/${encodeURIComponent(requestedSlug)}`)
    if (sequence !== loadSequence || (keepView && requestedPostChanges !== postChanges)) return
    disk.value = data.disk
    posts.value = data.posts || []
  } catch (e) {
    if (sequence === loadSequence) error.value = e.message
  } finally {
    if (sequence === loadSequence) {
      loading.value = false
      refreshing.value = false
    }
  }
}

async function loadJoinedDisks() {
  const sequence = ++joinedSequence
  if (!isLoggedIn.value) {
    joinedDisks.value = []
    return
  }
  try {
    const data = await apiGet('/disks?filter=joined')
    if (sequence === joinedSequence) joinedDisks.value = data.disks || []
  } catch {
    // ディスク一覧へのリンクは通信できない場合も残す。
  }
}

async function toggleJoin() {
  if (!disk.value || joining.value) return
  joining.value = true
  error.value = ''
  const target = disk.value
  try {
    const data = await apiPost('/disks/join', { slug: target.slug })
    if (disk.value !== target) return
    disk.value.is_member = data.is_member
    disk.value.member_count = data.member_count
    loadJoinedDisks()
  } catch (e) {
    if (disk.value === target) error.value = e.message
  } finally {
    joining.value = false
  }
}

async function onPosted(post) {
  postChanges++
  posts.value.unshift(post)
  disk.value.post_count++
  await nextTick()
  scrollToLatest()
}

function onDeleted(post) {
  postChanges++
  posts.value = posts.value.filter((item) => item.id !== post.id)
  disk.value.post_count = Math.max(0, disk.value.post_count - 1)
}

onMounted(() => {
  if (authReady.value) load()
  loadJoinedDisks()
})
watch(() => [props.slug, authReady.value, currentUser.value?.id], () => {
  if (authReady.value) load()
})
watch(() => currentUser.value?.id, () => {
  joinedDisks.value = []
  loadJoinedDisks()
})
onBeforeUnmount(() => {
  loadSequence++
  joinedSequence++
})
</script>

<template>
  <div class="disk-workspace">
    <aside class="disk-rail" aria-label="ディスクの切り替え">
      <NuxtLink class="disk-library-link" to="/disks">
        <span class="disk-rail-icon" aria-hidden="true">[D]</span>
        ディスク一覧
      </NuxtLink>
      <nav v-if="joinedDisks.length" class="disk-joined-nav" aria-label="参加中のディスク">
        <h2>参加中</h2>
        <NuxtLink
          v-for="item in joinedDisks"
          :key="item.id"
          :to="'/d/' + item.slug"
          :aria-current="item.slug === slug ? 'page' : undefined"
          class="disk-rail-link"
        >{{ item.name }}</NuxtLink>
      </nav>
      <div v-if="disk" class="disk-rail-info">
        <span>{{ formatNumber(disk.member_count) }} 人が参加中</span>
        <NuxtLink :to="'/u/' + disk.owner_username">所有者 @{{ disk.owner_username }}</NuxtLink>
      </div>
    </aside>

    <div v-if="loading" class="disk-workspace-state">
      <p class="panel-note" role="status">読み込み中…</p>
    </div>
    <div v-else-if="error && !disk" class="disk-workspace-state">
      <RequestError :message="error" @retry="load()" />
    </div>

    <section v-else-if="disk" class="disk-thread" :aria-label="disk.name">
      <header class="disk-thread-head">
        <div class="disk-thread-title">
          <span class="disk-thread-mark" aria-hidden="true">[D]</span>
          <div>
            <h1>{{ disk.name }}</h1>
            <p :title="disk.description">{{ disk.description || `${formatNumber(disk.member_count)} 人が参加中` }}</p>
          </div>
        </div>
        <div class="disk-thread-actions">
          <button
            v-if="canWrite"
            type="button"
            class="btn btn-sm"
            @click="openBotPanel"
          >ディスク Bot</button>
          <button
            type="button"
            class="btn btn-sm disk-refresh"
            :disabled="refreshing || joining"
            :aria-label="refreshing ? '書き込みを更新中' : '書き込みを更新'"
            title="書き込みを更新"
            @click="load(true)"
          ><span aria-hidden="true">↻</span></button>
          <button
            v-if="canWrite"
            type="button"
            class="btn btn-sm disk-leave"
            :disabled="joining || refreshing"
            @click="toggleJoin"
          >退出</button>
        </div>
      </header>

      <div class="disk-thread-body">
        <div ref="history" class="disk-history" role="region" aria-label="書き込み履歴" tabindex="0" @scroll.passive="onHistoryScroll">
          <div ref="historyContent" class="disk-history-content">
            <div v-if="!messages.length" class="disk-history-empty">
              <h2>まだ書き込みがありません</h2>
              <p v-if="canWrite">いちばん下の入力欄から、最初のメッセージを送れます。</p>
            </div>
            <PostList v-else :posts="messages" message-log @deleted="onDeleted" />
          </div>
        </div>

        <button
          v-if="!atLatest"
          type="button"
          class="btn btn-sm disk-to-latest"
          @click="scrollToLatest"
        >最新の書き込みへ</button>
      </div>

      <div class="disk-composer-dock">
        <p v-if="error" class="msg msg-error" role="alert">{{ error }}</p>
        <Composer v-if="canWrite" :key="`${disk.id}:${currentUser.id}`" :disk="disk" message-bar @posted="onPosted" />
        <div v-else class="disk-join-bar">
          <span>参加するとメッセージを書き込めます。</span>
          <button v-if="isLoggedIn" type="button" class="btn btn-primary" :disabled="joining || refreshing" @click="toggleJoin">
            {{ joining ? '処理中…' : '参加する' }}
          </button>
          <NuxtLink v-else class="btn btn-primary" to="/login">ログイン</NuxtLink>
        </div>
      </div>

      <Teleport to="body">
        <dialog v-if="canWrite" ref="botDialog" class="disk-tools-dialog" :aria-label="`${disk.name}のディスク Bot`">
          <div class="disk-tools-close">
            <button type="button" class="btn btn-sm" autofocus @click="botDialog?.close()">閉じる</button>
          </div>
          <DiskBotPanel :key="`${disk.id}:${currentUser.id}`" :slug="disk.slug" open-on-entry />
        </dialog>
      </Teleport>
    </section>
  </div>
</template>

<style scoped>
.disk-workspace {
  display: grid;
  grid-template-columns: clamp(10.5rem, 18vw, 14rem) minmax(0, 1fr);
  height: 100%;
  min-height: 0;
  border-inline: 1px solid var(--line-strong);
  background: var(--paper);
}

.disk-workspace > * {
  margin: 0;
}

.disk-rail {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
  padding: 1.25rem 1rem;
  overflow: auto;
  border-inline-end: 1px solid var(--line-strong);
  background: var(--paper-2);
}

.disk-library-link {
  display: flex;
  align-items: center;
  gap: .5rem;
  padding: 0 .4rem;
  color: var(--ink);
  font-weight: 700;
}

.disk-rail-icon,
.disk-thread-mark {
  color: var(--accent-deep);
  font-family: var(--font-mono);
}

.disk-joined-nav {
  display: grid;
  gap: .3rem;
}

.disk-joined-nav h2 {
  margin: 0 .4rem .2rem;
  color: var(--ink-2);
  font-size: .8rem;
}

.disk-rail-link {
  padding: .45rem .6rem;
  overflow: hidden;
  border-inline-start: 3px solid var(--line);
  color: var(--ink);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.disk-rail-link[aria-current='page'] {
  border-inline-start-color: var(--accent-deep);
  background: var(--accent-soft);
  color: var(--accent-deep);
  font-weight: 700;
}

.disk-rail-info {
  display: grid;
  gap: .3rem;
  margin-top: auto;
  padding: .65rem .4rem 0;
  border-top: 1px dashed var(--line);
  color: var(--ink-2);
  font-size: .8rem;
}

.disk-workspace-state {
  padding: 1rem;
  overflow: auto;
}

.disk-thread {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr) auto;
  min-width: 0;
  min-height: 0;
}

.disk-thread-head,
.disk-thread-title,
.disk-thread-actions {
  display: flex;
  align-items: center;
}

.disk-thread-head {
  justify-content: space-between;
  gap: 1rem;
  padding: .8rem 1.2rem;
  border-bottom: 1px solid var(--line-strong);
  background: var(--paper);
}

.disk-thread-title {
  gap: .65rem;
  min-width: 0;
}

.disk-thread-title > div {
  min-width: 0;
}

.disk-thread-title h1 {
  margin: 0;
  overflow: hidden;
  font-family: var(--font-display);
  font-size: clamp(1.2rem, 2.2vw, 1.55rem);
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.disk-thread-title p {
  margin: .2rem 0 0;
  overflow: hidden;
  color: var(--ink-2);
  font-size: .82rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.disk-thread-actions {
  flex-shrink: 0;
  gap: .35rem;
}

.disk-thread-actions .btn {
  min-height: 36px;
  white-space: nowrap;
}

.disk-refresh {
  min-width: 36px;
  font-size: 1.05rem;
}

.disk-thread-body {
  position: relative;
  min-height: 0;
  min-width: 0;
}

.disk-history {
  height: 100%;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.disk-history-content {
  display: flex;
  flex-direction: column;
  justify-content: end;
  min-height: 100%;
  padding: 0 clamp(.35rem, 2vw, 1.2rem) .65rem;
}

.disk-history-empty {
  margin: auto 0;
  padding: 1.2rem;
  text-align: center;
}

.disk-history-empty h2 {
  margin: 0;
  font-family: var(--font-display);
  font-size: clamp(1.1rem, 3vw, 1.4rem);
}

.disk-history-empty p {
  margin: .35rem 0 0;
  color: var(--ink-2);
}

.disk-to-latest {
  position: absolute;
  z-index: 2;
  inset-inline-end: 1rem;
  inset-block-end: .5rem;
  box-shadow: 2px 2px 0 var(--shadow);
}

.disk-composer-dock {
  position: relative;
  z-index: 3;
  min-width: 0;
  padding: .45rem clamp(.65rem, 2vw, 1.2rem) max(.7rem, env(safe-area-inset-bottom));
  background: var(--paper);
}

.disk-composer-dock > .msg {
  margin: 0 0 .35rem;
}

.disk-join-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: .5rem;
  padding: .55rem .65rem;
  border: 1px solid var(--line-strong);
  background: var(--paper-2);
  color: var(--ink-2);
}

.disk-join-bar .btn {
  min-height: 40px;
  white-space: nowrap;
}

.disk-tools-dialog {
  width: min(600px, calc(100% - 24px));
  max-height: calc(100dvh - 24px);
  margin: auto;
  padding: .8rem;
  overflow: auto;
  border: 2px solid var(--ink);
  background: var(--paper);
  color: var(--ink);
}

.disk-tools-dialog::backdrop {
  background: rgb(25 37 29 / 52%);
}

.disk-tools-close {
  display: flex;
  justify-content: flex-end;
  margin-bottom: .5rem;
}

@media (max-width: 700px) {
  .disk-workspace {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
    border-inline: 0;
  }

  .disk-rail {
    flex-direction: row;
    align-items: center;
    gap: .55rem;
    padding: .35rem .65rem;
    border-inline-end: 0;
    border-bottom: 1px solid var(--line);
  }

  .disk-library-link {
    flex-shrink: 0;
    padding: .25rem 0;
    font-size: .85rem;
  }

  .disk-joined-nav {
    display: flex;
    min-width: 0;
    overflow-x: auto;
  }

  .disk-joined-nav h2 {
    display: none;
  }

  .disk-rail-info {
    display: none;
  }

  .disk-rail-link {
    flex-shrink: 0;
    max-width: 10rem;
    padding: .3rem .45rem;
    font-size: .85rem;
  }

  .disk-thread-head {
    gap: .35rem;
    padding: .45rem .65rem;
  }

  .disk-thread-title {
    gap: .35rem;
  }

  .disk-thread-mark {
    display: none;
  }

  .disk-thread-actions .btn {
    padding-inline: .45rem;
  }

  .disk-history {
    scrollbar-gutter: auto;
  }
}
</style>
