<script setup>
import { ref, computed, onMounted } from 'vue'
import { drawPixel } from '../utils/pixel.js'

const props = defineProps({
  post: { type: Object, required: true },
  canDelete: { type: Boolean, default: false },
})

defineEmits(['delete', 'preview'])

const canvas = ref(null)
const playing = ref(false)

// ドット絵が描かれていない投稿ではキャンバスを出さない
const hasPixel = computed(() => /[1-9A-Fa-f]/.test(props.post.pixel_data || ''))

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
  if (hasPixel.value) drawPixel(canvas.value, props.post.pixel_data)
})

function fmtDate(s) {
  if (!s) return ''
  // MySQL の "YYYY-MM-DD HH:MM:SS" を Date に変換
  const d = new Date(String(s).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return String(s)
  return d.toLocaleString('ja-JP', { hour12: false })
}
</script>

<template>
  <article class="post">
    <canvas
      v-if="hasPixel"
      ref="canvas"
      class="post-pixel"
      width="16"
      height="16"
    ></canvas>

    <div class="post-body">
      <div class="post-head">
        <a class="post-user" :href="'#/u/' + post.username">
          {{ post.display_name || post.username }}
        </a>
        <span class="post-handle">@{{ post.username }}</span>
        <span class="post-dot">·</span>
        <span class="post-date">{{ fmtDate(post.created_at) }}</span>
        <span class="post-bytes">🖴 {{ post.total_bytes.toLocaleString('ja-JP') }} bytes</span>
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

      <div class="post-actions">
        <button type="button" class="link-btn" @click="$emit('preview', post)">
          埋め込み
        </button>
        <button
          v-if="canDelete"
          type="button"
          class="link-btn danger"
          @click="$emit('delete', post)"
        >
          🗑 フォーマット
        </button>
      </div>
    </div>
  </article>
</template>
