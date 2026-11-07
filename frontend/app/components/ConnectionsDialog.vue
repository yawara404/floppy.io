<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import { apiGet, apiPost } from '~/utils/api'
import { isLoggedIn, refreshUser } from '~/composables/useAuth'

const props = defineProps({
  username: { type: String, required: true },
  kind: { type: String, default: 'following' },
})
const emit = defineEmits(['close', 'select', 'changed'])
const dialog = ref(null)
const closeButton = ref(null)
const users = ref([])
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const nextOffset = ref(null)
const busy = ref(new Set())
let sequence = 0
let returnFocus = null
let hadScrollLock = false
const title = computed(() => props.kind === 'following' ? 'フォロー中' : 'フォロワー')

async function load(append = false) {
  const request = ++sequence
  const offset = append ? nextOffset.value : 0
  loading.value = true
  error.value = ''
  if (!append) {
    users.value = []
    nextOffset.value = null
    actionError.value = ''
  }
  try {
    const data = await apiGet(`/users/${encodeURIComponent(props.username)}/connections/${props.kind}?offset=${offset}`)
    if (request !== sequence) return
    const existing = new Set(users.value.map((user) => user.id))
    users.value = append ? [...users.value, ...data.users.filter((user) => !existing.has(user.id))] : data.users
    nextOffset.value = data.next_offset
  } catch (e) {
    if (request === sequence) error.value = e.message
  } finally {
    if (request === sequence) loading.value = false
  }
}

async function toggleFollow(user) {
  if (busy.value.has(user.id)) return
  busy.value.add(user.id)
  actionError.value = ''
  try {
    const data = await apiPost('/follow', { username: user.username })
    user.following = data.following
    await refreshUser()
    emit('changed')
  } catch (e) {
    actionError.value = e.message
  } finally {
    busy.value.delete(user.id)
  }
}

watch(() => [props.username, props.kind], () => load(), { immediate: true })
onMounted(() => {
  returnFocus = document.activeElement
  hadScrollLock = document.body.classList.contains('is-modal-open')
  document.body.classList.add('is-modal-open')
  dialog.value.showModal()
  closeButton.value?.focus()
})
onBeforeUnmount(() => {
  sequence++
  dialog.value?.close()
  if (!hadScrollLock) document.body.classList.remove('is-modal-open')
  returnFocus?.focus?.({ preventScroll: true })
})
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="share-dialog" aria-labelledby="connections-title" @cancel.prevent="emit('close')" @click.self="emit('close')">
      <section class="modal-window connections-window">
        <header class="modal-head">
          <div>
            <h2 id="connections-title" class="connections-title">{{ title }}</h2>
            <span class="connections-handle">@{{ username }}</span>
          </div>
          <button ref="closeButton" type="button" class="modal-close" aria-label="一覧を閉じる" @click="emit('close')">×</button>
        </header>
        <nav class="connections-tabs feed-tabs" aria-label="フォロー関係の一覧">
          <button v-for="tab in [{ id: 'following', label: 'フォロー中' }, { id: 'followers', label: 'フォロワー' }]" :key="tab.id" type="button" class="feed-tab" :class="{ active: kind === tab.id }" :aria-pressed="kind === tab.id" @click="emit('select', tab.id)">{{ tab.label }}</button>
        </nav>
        <p v-if="actionError" class="msg msg-error" role="alert">{{ actionError }}</p>
        <ul v-if="users.length" class="connections-list">
          <li v-for="person in users" :key="person.id" class="connection-row">
            <NuxtLink :to="'/u/' + person.username" class="connection-person">
              <ConnectionAvatar :user="person" />
              <span class="connection-info">
                <strong>{{ person.display_name }}</strong>
                <span class="connection-handle">@{{ person.username }}</span>
                <span v-if="person.bio" class="connection-bio">{{ person.bio }}</span>
              </span>
            </NuxtLink>
            <button v-if="isLoggedIn && !person.is_self" type="button" class="btn btn-sm connection-follow" :class="{ 'btn-primary': !person.following }" :disabled="busy.has(person.id)" :aria-label="`${person.display_name} を${person.following ? 'フォロー解除' : 'フォロー'}`" @click="toggleFollow(person)">{{ busy.has(person.id) ? '更新中…' : person.following ? 'フォロー中' : 'フォローする' }}</button>
          </li>
        </ul>
        <div class="connections-state" :aria-busy="loading">
          <p v-if="loading" role="status">読み込み中…</p>
          <RequestError v-else-if="error" :message="error" @retry="load(users.length > 0)" />
          <p v-else-if="!users.length" role="status">{{ kind === 'following' ? 'まだ誰もフォローしていません。' : 'まだフォロワーがいません。' }}</p>
          <button v-else-if="nextOffset !== null" type="button" class="btn" @click="load(true)">さらに表示</button>
        </div>
      </section>
    </dialog>
  </Teleport>
</template>
