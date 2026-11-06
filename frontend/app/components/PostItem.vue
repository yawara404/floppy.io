<script setup>
import { ref, computed, onMounted } from 'vue'
import { drawPixelContained } from '~/utils/pixel'
import ReplyForm from './ReplyForm.vue'
import { isLoggedIn } from '~/composables/useAuth'

const props = defineProps({
  post: { type: Object, required: true },
  canDelete: { type: Boolean, default: false },
})

defineEmits(['delete', 'share'])

const canvas = ref(null)
const playing = ref(false)
const menuOpen = ref(false)
const confirming = ref(false)
const replying = ref(false)

// 返信を受け付けるか（投稿者の設定）。既定はオフ。
const repliesEnabled = computed(() => props.post.replies_enabled === true)

function toggleReply() {
  if (!repliesEnabled.value) return
  replying.value = !replying.value
}

function onReplied() {
  props.post.reply_count = (props.post.reply_count || 0) + 1
  replying.value = false
}

// ドット絵が描かれていない投稿ではキャンバスを出さない
const hasPixel = computed(() => /[1-9A-Fa-f]/.test(props.post.pixel_data || ''))

// 投稿の種類ラベル（計器表示用）
const postKind = computed(() => {
  const post = props.post
  if (post.youtube_id) return 'YOUTUBE'
  if (post.image_url) return 'IMAGE'
  if (post.floppy_url) return post.floppy_kind === 'audio' ? 'AUDIO' : 'FILE'
  if (hasPixel.value) return 'PIXEL'
  return 'TEXT'
})

// YouTube 埋め込み
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
    // iOS Safari で全画面に飛ばさずインライン再生させる
    playsinline: '1',
  })

  // Referer が無いと YouTube がエラー 153 (プレーヤー設定エラー) を返すため、
  // 埋め込み元のオリジンを明示する
  if (typeof window !== 'undefined' && window.location.origin) {
    params.set('origin', window.location.origin)
  }

  return `https://www.youtube.com/embed/${props.post.youtube_id}?${params}`
})

// YouTube は IP アドレス (127.0.0.1 など) からの埋め込みを拒否するため、
// その場合は localhost で開き直す案内を出す
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

onMounted(() => {
  if (hasPixel.value) {
    drawPixelContained(
      canvas.value,
      props.post.pixel_data,
      props.post.pixel_width,
      props.post.pixel_height,
    )
  }
})

function fmtDate(s) {
  if (!s) return ''
  // MySQL の "YYYY-MM-DD HH:MM:SS" を Date に変換
  const d = new Date(String(s).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(s)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}/${pad(d.getMonth() + 1)}/${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<template>
  <article class="post">
    <div class="post-avatar">
      <canvas
        v-if="hasPixel"
        ref="canvas"
        class="post-pixel"
        width="16"
        height="16"
      ></canvas>
      <span v-else class="post-avatar-fallback" aria-hidden="true">[F]</span>
    </div>

    <div class="post-body">
      <div class="post-head">
        <NuxtLink class="post-user" :to="'/u/' + post.username">
          {{ post.display_name || post.username }}
        </NuxtLink>
        <span class="post-handle">@{{ post.username }}</span>
        <span class="post-bytes">[B] {{ post.total_bytes.toLocaleString('ja-JP') }} bytes</span>

        <!-- 三点メニュー（自分の投稿のみ） -->
        <button
          v-if="canDelete"
          type="button"
          class="post-menu-btn"
          :aria-expanded="menuOpen ? 'true' : 'false'"
          aria-label="投稿メニュー"
          @click="menuOpen = !menuOpen"
        >
          ⋯
        </button>
      </div>

      <div class="post-subline">
        <span class="post-no">No.{{ post.id }}</span>
        <span class="post-dot">/</span>
        <span class="post-date">{{ fmtDate(post.created_at) }}</span>
        <span class="post-dot">/</span>
        <span class="post-kind">{{ postKind }}</span>
        <template v-if="post.reply_to_id">
          <span class="post-dot">/</span>
          <NuxtLink class="post-reply-to" :to="'/p/' + post.reply_to_id">
            RE: #{{ post.reply_to_id }}
          </NuxtLink>
        </template>
      </div>

      <p v-if="post.text" class="post-text">{{ post.text }}</p>

      <!-- YouTube 埋め込み（クリックするまで iframe を読み込まない） -->
      <div v-if="post.youtube_id" class="youtube-embed">
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

      <a
        v-if="post.image_url"
        :href="post.image_url"
        class="post-image-link"
        target="_blank"
        rel="noopener noreferrer"
      >
        <img
          :src="post.image_url"
          class="post-image"
          loading="lazy"
          :alt="'@' + post.username + ' の画像'"
        />
      </a>

      <!-- 三点メニューのドロップダウン -->
      <div
        v-if="menuOpen"
        class="post-menu-backdrop"
        @click="menuOpen = false"
      ></div>
      <div v-if="menuOpen" class="post-menu">
        <button
          type="button"
          class="post-menu-item danger"
          @click="menuOpen = false; confirming = true"
        >
          削除（フォーマット）
        </button>
      </div>

      <!-- 添付フロッピーファイル（音声はプレイヤー付き） -->
      <div v-if="post.floppy_url" class="post-floppy-wrap">
        <audio
          v-if="post.floppy_kind === 'audio'"
          class="post-floppy-audio"
          controls
          preload="none"
          :src="post.floppy_url"
        ></audio>

        <a
          class="post-floppy"
          :href="post.floppy_url"
          :download="post.floppy_name || 'floppy.bin'"
        >
          <span class="post-floppy-icon" aria-hidden="true">
            {{ post.floppy_kind === 'audio' ? '[♪]' : '[F]' }}
          </span>
          <span>
            <span class="post-floppy-name">{{ post.floppy_name || 'floppy.bin' }}</span>
            <span class="post-floppy-meta">
              {{ (post.floppy_bytes || 0).toLocaleString('ja-JP') }} bytes をダウンロード
            </span>
          </span>
        </a>
      </div>

      <div v-if="confirming" class="post-actions post-confirm">
        <span class="confirm-text">
          この投稿を削除しますか？（{{ post.total_bytes.toLocaleString('ja-JP') }} bytes 解放）
        </span>
        <button
          type="button"
          class="link-btn danger"
          @click="$emit('delete', post)"
        >
          削除する
        </button>
        <button type="button" class="link-btn" @click="confirming = false">
          やめる
        </button>
      </div>

      <div v-else class="post-actions">
        <button
          type="button"
          class="link-btn action-btn reply-btn"
          :disabled="!repliesEnabled"
          :title="
            !repliesEnabled
              ? 'この投稿は返信を受け付けていません'
              : isLoggedIn
                ? 'この投稿に返信'
                : 'ログインして返信'
          "
          :aria-expanded="replying ? 'true' : 'false'"
          @click="toggleReply"
        >
          <span aria-hidden="true">↩</span> 返信
          <span class="reply-count">
            {{ String(post.reply_count || 0).padStart(2, '0') }}
          </span>
        </button>
        <button
          type="button"
          class="link-btn action-btn like-btn"
          :class="{ liked: post.liked }"
          :title="post.liked ? 'いいねを取り消す' : 'いいね'"
          :aria-label="post.liked ? 'いいねを取り消す' : 'いいね'"
          :aria-pressed="post.liked ? 'true' : 'false'"
          @click="$emit('like', post)"
        >
          <span aria-hidden="true">{{ post.liked ? '♥' : '♡' }}</span> いいね
          <span class="like-count">{{ String(post.like_count || 0).padStart(2, '0') }}</span>
        </button>
        <button
          type="button"
          class="link-btn action-btn"
          aria-label="投稿を共有"
          @click="$emit('share', post)"
        >
          <span aria-hidden="true">↗</span> 共有
        </button>
      </div>

      <!-- 返信（インライン） -->
      <ReplyForm
        v-if="replying"
        :post="post"
        @replied="onReplied"
        @cancel="replying = false"
      />
    </div>
  </article>
</template>
