<script setup>
// floppy.io — 個別ビューの返信（Miiverse / mixi 風の吹き出しコメント）
import { ref, onMounted, watch, nextTick } from 'vue'
import { drawDefaultAvatar } from '~/utils/pixel'
import { formatDateTime } from '~/utils/format'
import { useAvatarImage } from '~/composables/useAvatarImage'

const props = defineProps({
  reply: { type: Object, required: true },
  canDelete: { type: Boolean, default: false },
})

defineEmits(['like', 'delete'])

const avatar = ref(null)
const {
  image: avatarImage,
  reset: resetAvatar,
  onError: markAvatarError,
} = useAvatarImage(() => props.reply)

function drawAvatar() {
  if (avatar.value) drawDefaultAvatar(avatar.value)
}

function onAvatarError() {
  markAvatarError()
  nextTick(drawAvatar)
}

onMounted(drawAvatar)

watch(
  () => [props.reply.id, props.reply.author_icon_url, props.reply.author_avatar_url],
  async () => {
    resetAvatar()
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
        <time class="reply-bubble-date">{{ formatDateTime(reply.created_at) }}</time>
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
