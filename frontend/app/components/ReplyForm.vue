<script setup>
import { computed, ref } from 'vue'
import { apiPost } from '~/utils/api'
import { isLoggedIn } from '~/composables/useAuth'

const props = defineProps({
  post: { type: Object, required: true },
})

const emit = defineEmits(['replied', 'cancel'])

// 返信はテキストのみ。ドット絵 256 バイトは常に消費されるため、
// 本文に使えるのは 1 投稿の上限から 256 バイトを引いた分。
const DISK_LIMIT = 1474560
const PIXEL_BYTES = 256

const text = ref('')
const error = ref('')
const busy = ref(false)

const fieldId = computed(() => `reply-text-${props.post.id}`)
const bytes = computed(() => new TextEncoder().encode(text.value).length)
const overLimit = computed(() => bytes.value + PIXEL_BYTES > DISK_LIMIT)
const canSubmit = computed(
  () => Boolean(text.value.trim()) && !overLimit.value && !busy.value,
)

async function submit() {
  if (!canSubmit.value) return

  error.value = ''
  busy.value = true

  try {
    const data = await apiPost('/posts', {
      text: text.value,
      reply_to_id: props.post.id,
    })
    text.value = ''
    emit('replied', data.post)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form v-if="isLoggedIn" class="reply-form" @submit.prevent="submit">
    <label class="field-label" :for="fieldId">
      @{{ post.username }} に返信（テキストのみ）
    </label>

    <textarea
      :id="fieldId"
      v-model="text"
      class="input reply-input"
      rows="2"
      :placeholder="'@' + post.username + ' への返信を書く'"
    ></textarea>

    <p class="reply-hint" :class="{ danger: overLimit }">
      {{ bytes.toLocaleString('ja-JP') }} / {{ (DISK_LIMIT - PIXEL_BYTES).toLocaleString('ja-JP') }} bytes
    </p>

    <p v-if="error" class="msg msg-error" role="alert">{{ error }}</p>

    <div class="reply-actions">
      <button type="submit" class="btn btn-primary btn-sm" :disabled="!canSubmit">
        {{ busy ? '送信中…' : '返信する' }}
      </button>
      <button type="button" class="btn btn-sm" @click="$emit('cancel')">
        やめる
      </button>
    </div>
  </form>

  <div v-else class="reply-form reply-form-guest">
    <p class="panel-note">返信するにはログインが必要です。</p>
    <div class="reply-actions">
      <NuxtLink class="btn btn-primary btn-sm" to="/login">ログイン</NuxtLink>
      <NuxtLink class="btn btn-sm" to="/register">新規登録</NuxtLink>
    </div>
  </div>
</template>
