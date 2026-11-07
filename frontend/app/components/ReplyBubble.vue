<script setup>
// floppy.io — 個別ビューの返信（Miiverse / mixi 風の吹き出しコメント）
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { drawPixelContained, FLOPPY_AVATAR } from '~/utils/pixel'
import { resolveMediaUrl } from '~/utils/api'

const props = defineProps({
  reply: { type: Object, required: true },
  canDelete: { type: Boolean, default: false },
})

defineEmits(['like', 'delete'])

const avatar = ref(null)
const avatarError = ref(false)

const avatarImage = computed(() => {
  if (avatarError.value) return ''
  return resolveMediaUrl(
    props.reply.author_icon_url || props.reply.author_avatar_url || '',
  )
})

function drawAvatar() {
  if (avatar.value) drawPixelContained(avatar.value, FLOPPY_AVATAR)
}

function onAvatarError() {
  avatarError.value = true
  nextTick(drawAvatar)
}

function fmtDate(value) {
  if (!value) return ''
  const date = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return String(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

onMounted(drawAvatar)

watch(
  () => [props.reply.id, props.reply.author_icon_url, props.reply.author_avatar_url],
  async () => {
    avatarError.value = false
    await nextTick()
    drawAvatar()
  },
)
</script>

<template>
  <article class="reply-bubble">
    <NuxtLink
      class="reply-bubble-avatar"
      :to="'/u/' + reply.username"
      :aria-label="(reply.display_name || reply.username) + ' のプロフィール'"
    >
      <img
        v-if="avatarImage"
        :src="avatarImage"
        class="reply-bubble-avatar-image"
        alt=""
        loading="lazy"
        @error="onAvatarError"
      />
      <canvas
        v-else
        ref="avatar"
        width="16"
        height="16"
        aria-hidden="true"
      ></canvas>
    </NuxtLink>

    <div class="reply-bubble-main">
      <div class="reply-bubble-head">
        <NuxtLink class="reply-bubble-name" :to="'/u/' + reply.username">
          {{ reply.display_name || reply.username }}
        </NuxtLink>
        <span class="reply-bubble-handle">@{{ reply.username }}</span>
        <time class="reply-bubble-date">{{ fmtDate(reply.created_at) }}</time>
      </div>

      <p class="reply-bubble-text">{{ reply.text }}</p>

      <div class="reply-bubble-actions">
        <button
          type="button"
          class="link-btn"
          :class="{ liked: reply.liked }"
          :aria-pressed="reply.liked ? 'true' : 'false'"
          @click="$emit('like', reply)"
        >
          {{ reply.liked ? '♥' : '♡' }} 共感
          <span class="reply-bubble-count">{{ reply.like_count || 0 }}</span>
        </button>

        <NuxtLink class="link-btn" :to="'/p/' + reply.id">スレッド</NuxtLink>

        <button
          v-if="canDelete"
          type="button"
          class="link-btn danger"
          @click="$emit('delete', reply)"
        >
          削除
        </button>
      </div>
    </div>
  </article>
</template>
