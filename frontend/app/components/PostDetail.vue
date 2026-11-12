<script setup>
// floppy.io — 個別ビューの大きな投稿カード
//   Miiverse の「ボード + 大きな投稿 + 共感」と、
//   旧 Twitter の「メディア + アクション行」を合わせた見た目。
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { drawPixelContained } from '~/utils/pixel'
import { formatDateTime } from '~/utils/format'
import { hasPixelArt, postKindOf } from '~/utils/post'
import { useAvatarImage } from '~/composables/useAvatarImage'
import { useAvatarCanvas } from '~/composables/useAvatarCanvas'
import YouTubeEmbed from './YouTubeEmbed.vue'
import { resolveMediaUrl } from '~/utils/api'

const props = defineProps({
  post: { type: Object, required: true },
  canDelete: { type: Boolean, default: false },
})

const emit = defineEmits(['like', 'share', 'reply', 'delete'])

const { canvas: avatarCanvas, draw: drawAvatar } = useAvatarCanvas(
  () => props.post,
)
const {
  image: avatarImage,
  reset: resetAvatar,
  onError: markAvatarError,
} = useAvatarImage(() => props.post)
const pixelCanvas = ref(null)
const confirming = ref(false)

const hasPixel = computed(() => hasPixelArt(props.post))
const totalBytes = computed(() => Number(props.post.total_bytes) || 0)
const likeCount = computed(() => Number(props.post.like_count) || 0)
const replyCount = computed(() => Number(props.post.reply_count) || 0)

const postKind = computed(() => postKindOf(props.post))

function drawPixelCanvas() {
  if (!pixelCanvas.value || !hasPixel.value) return
  drawPixelContained(
    pixelCanvas.value,
    props.post.pixel_data,
    props.post.pixel_width,
    props.post.pixel_height,
  )
}

function onAvatarError() {
  markAvatarError()
  nextTick(drawAvatar)
}

onMounted(drawPixelCanvas)
watch(
  () => [
    props.post.id,
    props.post.pixel_data,
    hasPixel.value,
    props.post.author_icon_url,
    props.post.author_avatar_url,
  ],
  async () => {
    resetAvatar()
    await nextTick()
    drawPixelCanvas()
  },
)
</script>


<template>
  <article class="panel detail-post">
    <header class="detail-head">
      <NuxtLink
        class="detail-avatar"
        :to="'/u/' + post.username"
        :aria-label="(post.display_name || post.username) + ' のプロフィール'"
      >
        <img
          v-if="avatarImage"
          :src="avatarImage"
          class="detail-avatar-image"
          alt=""
          loading="lazy"
          @error="onAvatarError"
        />
        <canvas
          v-else
          ref="avatarCanvas"
          width="16"
          height="16"
          aria-hidden="true"
        ></canvas>
      </NuxtLink>

      <div class="detail-author">
        <NuxtLink class="detail-name" :to="'/u/' + post.username">
          {{ post.display_name || post.username }}
        </NuxtLink>
        <div class="detail-handle">@{{ post.username }}</div>
      </div>

      <span class="detail-kind">{{ postKind }}</span>
    </header>

    <p v-if="post.text" class="detail-text">{{ post.text }}</p>

    <!-- YouTube（クリックするまで iframe を読み込まない） -->
    <YouTubeEmbed
      v-if="post.youtube_id"
      class="detail-youtube"
      :video-id="post.youtube_id"
      :title="post.youtube_title"
      :thumbnail="post.youtube_thumbnail"
    />

    <!-- 添付画像 -->
    <a
      v-if="post.image_url"
      class="post-image-link detail-image-link"
      :href="resolveMediaUrl(post.image_url)"
      target="_blank"
      rel="noopener noreferrer"
    >
      <img
        :src="resolveMediaUrl(post.image_url)"
        class="post-image detail-image"
        loading="lazy"
        :alt="'@' + post.username + ' の画像'"
      />
    </a>

    <!-- ドット絵（動画・画像が無いときのメイン画像） -->
    <div v-if="hasPixel && !post.youtube_id && !post.image_url" class="detail-pixel-wrap">
      <canvas
        ref="pixelCanvas"
        class="detail-pixel"
        width="16"
        height="16"
        :aria-label="'@' + post.username + ' のドット絵'"
      ></canvas>
    </div>

    <!-- 添付フロッピー -->
    <div v-if="post.floppy_url" class="post-floppy-wrap detail-floppy-wrap">
      <audio
        v-if="post.floppy_kind === 'audio'"
        class="post-floppy-audio"
        controls
        preload="none"
        :src="resolveMediaUrl(post.floppy_url)"
      ></audio>
      <a
        class="post-floppy"
        :href="resolveMediaUrl(post.floppy_url)"
        :download="post.floppy_name || 'floppy.bin'"
      >
        <span class="post-floppy-icon" aria-hidden="true">
          {{ post.floppy_kind === 'audio' ? '[♪]' : '[F]' }}
        </span>
        <span>
          <span class="post-floppy-name">{{ post.floppy_name || 'floppy.bin' }}</span>
          <span class="post-floppy-meta">
            {{ (Number(post.floppy_bytes) || 0).toLocaleString('ja-JP') }} bytes をダウンロード
          </span>
        </span>
      </a>
    </div>


    <div class="detail-meta">
      <span>No.{{ post.id }}</span>
      <span aria-hidden="true">/</span>
      <time>{{ formatDateTime(post.created_at) }}</time>
      <template v-if="post.disk">
        <span aria-hidden="true">/</span>
        <NuxtLink :to="'/d/' + post.disk.slug">[D] {{ post.disk.name }}</NuxtLink>
      </template>
      <span aria-hidden="true">/</span>
      <span>{{ totalBytes.toLocaleString('ja-JP') }} bytes</span>
    </div>

    <div class="detail-actions">
      <button
        type="button"
        class="detail-action detail-like"
        :class="{ active: post.liked }"
        :aria-pressed="post.liked ? 'true' : 'false'"
        :title="post.liked ? 'いいねを取り消す' : 'いいね'"
        @click="emit('like', post)"
      >
        <span aria-hidden="true">{{ post.liked ? '♥' : '♡' }}</span>
        いいね <b>{{ likeCount }}</b>
      </button>

      <button
        v-if="post.replies_enabled"
        type="button"
        class="detail-action"
        @click="emit('reply')"
      >
        <span aria-hidden="true">↩</span>
        返信 <b>{{ replyCount }}</b>
      </button>

      <button type="button" class="detail-action" @click="emit('share', post)">
        <span aria-hidden="true">↗</span> 共有
      </button>

      <NuxtLink class="detail-action" :to="'/u/' + post.username">
        プロフィール
      </NuxtLink>

      <button
        v-if="canDelete"
        type="button"
        class="detail-action danger"
        @click="confirming = true"
      >
        削除
      </button>
    </div>

    <div v-if="confirming" class="detail-confirm">
      <span>
        この投稿を削除しますか？（{{ totalBytes.toLocaleString('ja-JP') }} bytes 解放）
      </span>
      <button type="button" class="link-btn danger" @click="emit('delete', post)">
        削除する
      </button>
      <button type="button" class="link-btn" @click="confirming = false">
        やめる
      </button>
    </div>
  </article>
</template>
