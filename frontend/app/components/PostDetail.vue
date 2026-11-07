<script setup>
// floppy.io — 個別ビューの大きな投稿カード
//   Miiverse の「ボード + 大きな投稿 + 共感」と、
//   旧 Twitter の「メディア + アクション行」を合わせた見た目。
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { drawPixelContained, FLOPPY_AVATAR } from '~/utils/pixel'
import { resolveMediaUrl } from '~/utils/api'

const props = defineProps({
  post: { type: Object, required: true },
  canDelete: { type: Boolean, default: false },
})

const emit = defineEmits(['like', 'share', 'reply', 'delete'])

const avatarCanvas = ref(null)
const avatarError = ref(false)
const avatarImage = computed(() => {
  if (avatarError.value) return ''
  return resolveMediaUrl(
    props.post.author_icon_url || props.post.author_avatar_url || '',
  )
})
const pixelCanvas = ref(null)
const playing = ref(false)
const confirming = ref(false)

const hasPixel = computed(() => /[1-9A-Fa-f]/.test(String(props.post.pixel_data || '')))
const totalBytes = computed(() => Number(props.post.total_bytes) || 0)
const likeCount = computed(() => Number(props.post.like_count) || 0)
const replyCount = computed(() => Number(props.post.reply_count) || 0)

const postKind = computed(() => {
  const post = props.post
  if (post.youtube_id) return 'YOUTUBE'
  if (post.image_url) return 'IMAGE'
  if (post.floppy_url) return post.floppy_kind === 'audio' ? 'AUDIO' : 'FILE'
  if (hasPixel.value) return 'PIXEL'
  return 'TEXT'
})

const youtubeThumb = computed(() => {
  if (props.post.youtube_thumbnail) return props.post.youtube_thumbnail
  return props.post.youtube_id
    ? `https://i.ytimg.com/vi/${props.post.youtube_id}/hqdefault.jpg`
    : ''
})

const youtubeWatchUrl = computed(() =>
  props.post.youtube_id
    ? `https://www.youtube.com/watch?v=${props.post.youtube_id}`
    : '',
)

const youtubeEmbedUrl = computed(() => {
  if (!props.post.youtube_id) return ''

  const params = new URLSearchParams({
    autoplay: '1',
    rel: '0',
    playsinline: '1',
  })

  if (typeof window !== 'undefined' && window.location.origin) {
    params.set('origin', window.location.origin)
  }

  return `https://www.youtube.com/embed/${props.post.youtube_id}?${params}`
})

const isIpHost = computed(
  () =>
    typeof window !== 'undefined' &&
    /^\d{1,3}(\.\d{1,3}){3}$/.test(window.location.hostname),
)

const localhostUrl = computed(() => {
  if (typeof window === 'undefined') return '#'
  const { protocol, port, pathname, search, hash } = window.location
  return `${protocol}//localhost${port ? ':' + port : ''}${pathname}${search}${hash}`
})

function fmtDate(value) {
  if (!value) return ''
  const date = new Date(String(value).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return String(value)
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}/${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function render() {
  if (avatarCanvas.value) {
    if (hasPixel.value) {
      drawPixelContained(
        avatarCanvas.value,
        props.post.pixel_data,
        props.post.pixel_width,
        props.post.pixel_height,
      )
    } else {
      drawPixelContained(avatarCanvas.value, FLOPPY_AVATAR)
    }
  }
  if (pixelCanvas.value && hasPixel.value) {
    drawPixelContained(
      pixelCanvas.value,
      props.post.pixel_data,
      props.post.pixel_width,
      props.post.pixel_height,
    )
  }
}

function onAvatarError() {
  avatarError.value = true
  nextTick(render)
}

onMounted(render)
watch(
  () => [
    props.post.id,
    props.post.pixel_data,
    hasPixel.value,
    props.post.author_icon_url,
    props.post.author_avatar_url,
  ],
  async () => {
    avatarError.value = false
    await nextTick()
    render()
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
    <div v-if="post.youtube_id" class="youtube-embed detail-youtube">
      <div class="youtube-frame">
        <iframe
          v-if="playing"
          :src="youtubeEmbedUrl"
          title="YouTube 動画プレーヤー"
          referrerpolicy="strict-origin-when-cross-origin"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
          allowfullscreen
        ></iframe>
        <button
          v-else
          type="button"
          class="youtube-thumb"
          aria-label="YouTube を再生"
          @click="playing = true"
        >
          <img :src="youtubeThumb" alt="" loading="lazy" />
          <span class="youtube-play" aria-hidden="true">▶</span>
        </button>
      </div>

      <div class="youtube-meta">
        <span class="youtube-title">
          ▶ {{ post.youtube_title || 'YouTube 動画' }}
        </span>
        <a
          class="youtube-open"
          :href="youtubeWatchUrl"
          target="_blank"
          rel="noopener noreferrer"
        >
          YouTube で見る ↗
        </a>
      </div>

      <p v-if="isIpHost" class="youtube-hint">
        このページは IP アドレスで開かれているため、YouTube を埋め込み再生できません。
        <a :href="localhostUrl">localhost で開き直す</a>
      </p>
    </div>

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
      <time>{{ fmtDate(post.created_at) }}</time>
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
