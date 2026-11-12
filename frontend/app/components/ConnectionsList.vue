<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { apiGet, apiPost } from '~/utils/api'
import { isLoggedIn, refreshUser } from '~/composables/useAuth'

const props = defineProps({
  username: { type: String, required: true },
  kind: { type: String, default: 'following' },
})
const emit = defineEmits(['changed'])
const users = ref([])
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const nextOffset = ref(null)
const busy = ref(new Set())
let sequence = 0

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
onBeforeUnmount(() => { sequence++ })
</script>

<template>
  <section class="connections-panel" :aria-label="kind === 'following' ? 'フォロー中のユーザー' : 'フォロワー'">
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
</template>
