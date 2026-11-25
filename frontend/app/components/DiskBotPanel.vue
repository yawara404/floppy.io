<script setup>
import { ref, useId, watch } from 'vue'
import { apiGet } from '~/utils/api'
import { currentUser } from '~/composables/useAuth'

const props = defineProps({
  slug: { type: String, required: true },
  openOnEntry: { type: Boolean, default: false },
})
const field = useId()
const summary = ref(null)
const username = ref('')
const result = ref(null)
const error = ref('')
const busy = ref(false)

watch([() => props.openOnEntry, summary], ([open, heading]) => {
  if (open) heading?.focus()
}, { flush: 'post' })

async function run(command) {
  if (busy.value) return
  busy.value = true
  result.value = null
  error.value = ''
  try {
    const endpoint = `/disks/${encodeURIComponent(props.slug)}/bot/${command}`
    if (command === 'latest') {
      const { posts } = await apiGet(endpoint)
      result.value = { posts }
    } else {
      const target = username.value.trim() || currentUser.value?.username
      const data = await apiGet(endpoint + '?username=' + encodeURIComponent(target))
      result.value = { username: target.replace(/^@/, ''), playing: data.playing }
    }
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <details class="panel disk-bot" :open="openOnEntry">
    <summary ref="summary">ディスク Bot</summary>
    <div class="disk-bot-body">
      <button type="button" class="btn" :disabled="busy" @click="run('latest')">
        新着5件を見る
      </button>

      <form class="disk-bot-playing" @submit.prevent="run('playing')">
        <div>
          <label :for="field" class="field-label">Steamナウプレを調べる</label>
          <input
            :id="field"
            v-model="username"
            class="input"
            maxlength="33"
            spellcheck="false"
            autocomplete="off"
            autocapitalize="none"
            placeholder="ユーザー名（空欄なら自分）"
          />
        </div>
        <button type="submit" class="btn" :disabled="busy">照会</button>
      </form>
      <NuxtLink class="link-btn" to="/settings">Steam連携を設定</NuxtLink>

      <p v-if="busy" class="panel-note" role="status">照会中…</p>
      <p v-else-if="error" class="msg msg-error" role="alert">{{ error }}</p>
      <div v-else-if="result" class="disk-bot-result" aria-live="polite">
        <template v-if="result.posts">
          <ul v-if="result.posts.length">
            <li v-for="post in result.posts" :key="post.id">
              <NuxtLink :to="'/p/' + post.id">No.{{ post.id }}</NuxtLink>
              <span>@{{ post.username }}　{{ post.excerpt || '添付・ドット絵の投稿' }}</span>
            </li>
          </ul>
          <p v-else class="panel-note">このディスクにはまだ投稿がありません。</p>
        </template>
        <p v-else-if="result.playing">@{{ result.username }} が Steam で <strong>{{ result.playing }}</strong> をプレイ中</p>
        <p v-else class="panel-note">表示できるプレイ中のゲームはありません。</p>
      </div>
    </div>
  </details>
</template>

<style scoped>
.disk-bot summary {
  color: var(--ink);
  cursor: pointer;
  font-weight: 700;
}
.disk-bot-body {
  margin-top: 1rem;
}
.disk-bot-playing {
  display: flex;
  align-items: end;
  gap: .5rem;
  margin-block: .8rem .4rem;
}
.disk-bot-playing div {
  width: min(100%, 22rem);
  min-width: 0;
}
.disk-bot-playing button {
  flex: none;
}
.disk-bot-result {
  margin-top: .8rem;
  padding: .65rem;
  border: 1px dotted currentColor;
  overflow-wrap: anywhere;
}
.disk-bot-result ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.disk-bot-result li + li {
  margin-top: .5rem;
}
.disk-bot-result a {
  margin-right: .5rem;
}
.disk-bot-result p {
  margin: 0;
}
</style>
