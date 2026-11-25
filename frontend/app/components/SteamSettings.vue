<script setup>
import { onMounted, ref } from 'vue'
import { apiGet, apiPost } from '~/utils/api'

const route = useRoute()
const router = useRouter()
const settings = ref(null)
const busy = ref(false)
const error = ref('')
const message = ref('')

async function run(task) {
  if (busy.value) return
  error.value = ''
  message.value = ''
  busy.value = true
  try {
    await task()
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

function load() {
  return run(async () => {
    settings.value = await apiGet('/steam')
    const state = /^#steam=([A-Za-z0-9_-]{43})$/.exec(route.hash)?.[1]
    if (state) {
      try {
        Object.assign(settings.value, await apiPost('/steam/complete', { state }))
        message.value = 'Steamと連携しました。プレイ中の表示は設定できます。'
      } finally {
        await router.replace({ path: route.path })
      }
    } else if (route.query.steam === 'cancelled') {
      message.value = 'Steamとの連携をキャンセルしました。'
      await router.replace({ path: route.path })
    }
  })
}

function start() {
  return run(async () => {
    const { url } = await apiPost('/steam/start')
    window.location.assign(url)
  })
}

function publish(event) {
  const checked = event.target.checked
  event.target.checked = settings.value.show_in_disks
  return run(async () => {
    settings.value = await apiPost('/steam/visibility', { show_in_disks: checked })
    message.value = checked ? '参加中のディスクでプレイ中のゲームを公開します。' : 'プレイ中のゲームを非公開にしました。'
  })
}

function disconnect() {
  return run(async () => {
    Object.assign(settings.value, await apiPost('/steam/disconnect'))
    message.value = 'Steamとの連携を解除しました。'
  })
}

onMounted(load)
</script>

<template>
  <section class="panel">
    <h2 class="panel-title">Steam連携</h2>
    <p class="panel-note">公開をオンにすると、同じディスクの参加者がディスク Botからプレイ中のゲームを確認できます。</p>
    <p v-if="error" class="msg msg-error" role="alert">{{ error }}</p>
    <p v-if="message" class="msg msg-info" role="status">{{ message }}</p>
    <button v-if="!settings && error" type="button" class="btn" :disabled="busy" @click="load">再試行</button>
    <p v-else-if="!settings" class="panel-note">読み込み中…</p>
    <template v-else-if="settings.linked">
      <label class="steam-visibility">
        <input type="checkbox" :checked="settings.show_in_disks" :disabled="busy || !settings.available" @change="publish" />
        参加中のディスクでプレイ中を公開する
      </label>
      <div class="panel-actions">
        <button type="button" class="btn" :disabled="busy" @click="disconnect">連携を解除</button>
      </div>
    </template>
    <p v-else-if="!settings.available" class="panel-note">Steam連携は準備中です。</p>
    <div v-else class="panel-actions">
      <button type="button" class="btn btn-primary" :disabled="busy" @click="start">Steamで連携する</button>
    </div>
  </section>
</template>

<style scoped>
.steam-visibility {
  display: flex;
  align-items: center;
  gap: .55rem;
  margin-block: .9rem;
}
</style>
