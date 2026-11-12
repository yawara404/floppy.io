<script setup>
// floppy.io — 共有ダイアログ
//
// X (Twitter) の共有カードと同じ流れで「カードのプレビュー → 共有先を選ぶ」
// という構成にしている。共有 URL と埋め込み HTML はこの 1 か所で管理する。
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { drawPixelContained } from '~/utils/pixel'
import { formatDateParts } from '~/utils/format'
import { hasPixelArt, postKindOf, youtubeThumbnail } from '~/utils/post'
import { useAvatarImage } from '~/composables/useAvatarImage'
import { useAvatarCanvas } from '~/composables/useAvatarCanvas'
import { useDialog } from '~/composables/useDialog'
import { apiGet, resolveMediaUrl } from '~/utils/api'
import { usePostShare } from '~/composables/usePostShare'

const props = defineProps({
  post: { type: Object, required: true },
})

const emit = defineEmits(['close'])

const {
  canNativeShare,
  postUrl,
  xShareUrl,
  lineShareUrl,
  copyText,
  shareNative,
} = usePostShare()

const canvas = ref(null)
const { canvas: avatarCanvas, draw: drawAvatar } = useAvatarCanvas(
  () => props.post,
)
const {
  image: avatarImage,
  reset: resetAvatar,
  onError: markAvatarError,
} = useAvatarImage(() => props.post)

const copied = ref('')
const embedHtml = ref('')
const previewState = ref('idle') // idle | loading | ready | error
let copiedTimer = null

const author = computed(
  () => props.post.display_name || props.post.username || '名無し',
)
const shareUrl = computed(() => postUrl(props.post))
const xUrl = computed(() => xShareUrl(props.post))
const lineUrl = computed(() => lineShareUrl(props.post))

const hasPixel = computed(() => hasPixelArt(props.post))

const youtubeThumb = computed(() => youtubeThumbnail(props.post))

// サイトの投稿カードと同じく「動画 > 画像 > ドット絵」の優先順で 1 枚だけ出す
const media = computed(() => {
  if (youtubeThumb.value) {
    return { type: 'youtube', src: youtubeThumb.value }
  }
  if (props.post.image_url) {
    return { type: 'image', src: resolveMediaUrl(props.post.image_url) }
  }
  if (hasPixel.value) {
    return { type: 'pixel' }
  }
  return null
})

const totalBytes = computed(() => Number(props.post.total_bytes) || 0)

const postKind = computed(() => postKindOf(props.post))

const likeCount = computed(() => Number(props.post.like_count) || 0)
const replyCount = computed(() => Number(props.post.reply_count) || 0)

// 本文中の URL をサイトのリンク色で表示する（カード全体がリンクなので <a> は使わない）
const textParts = computed(() => {
  const raw = String(props.post.text || '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
  const parts = raw.split(/(https?:\/\/[^\s<]+)/g)

  return parts.map((part, index) => {
    if (index % 2) {
      let label = part.replace(/^https?:\/\//, '')
      if (label.length > 36) label = `${label.slice(0, 36)}…`
      return { type: 'link', text: label }
    }
    return { type: 'text', text: part }
  })
})

const dateTime = computed(() => formatDateParts(props.post.created_at))
const timeLabel = computed(() => dateTime.value.time)
const dateLabel = computed(() => dateTime.value.date)

function renderPixel() {
  if (!canvas.value || media.value?.type !== 'pixel') return
  drawPixelContained(
    canvas.value,
    props.post.pixel_data,
    props.post.pixel_width,
    props.post.pixel_height,
  )
}

function onAvatarError() {
  markAvatarError()
  nextTick(drawAvatar)
}

// 埋め込み HTML は /api/preview が組み立てる自己完結スニペット
async function loadPreview() {
  if (previewState.value === 'loading') return
  previewState.value = 'loading'
  embedHtml.value = ''

  try {
    const data = await apiGet(`/preview?id=${encodeURIComponent(props.post.id)}`)
    embedHtml.value = data?.html || ''
    previewState.value = embedHtml.value ? 'ready' : 'error'
  } catch (e) {
    previewState.value = 'error'
  }
}

function onEmbedToggle(event) {
  if (event.target.open && previewState.value === 'idle') loadPreview()
}

async function copy(value, label) {
  if (!value) return

  const ok = await copyText(value)
  copied.value = ok ? label : 'error'

  if (copiedTimer) clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => {
    copied.value = ''
  }, 2200)
}

async function useNativeShare() {
  const ok = await shareNative(props.post)
  if (ok) emit('close')
}

const statusMessage = computed(() => {
  if (copied.value === 'error') return 'コピーできませんでした。手動で選択してください。'
  if (copied.value === 'link') return '共有リンクをコピーしました。'
  if (copied.value === 'embed') return '埋め込み HTML をコピーしました。'
  return ''
})

// ---------------------------------------------------------------------------
// モーダルの開閉（フォーカス / 背景スクロール）は composable に任せる
// ---------------------------------------------------------------------------
const { dialogEl, closeEl } = useDialog()

onMounted(async () => {
  renderPixel()
  drawAvatar()
})

onBeforeUnmount(() => {
  if (copiedTimer) clearTimeout(copiedTimer)
})

watch(media, async () => {
  await nextTick()
  renderPixel()
})

watch(
  [
    () => props.post.id,
    hasPixel,
    () => props.post.author_icon_url,
    () => props.post.author_avatar_url,
  ],
  async () => {
    resetAvatar()
    await nextTick()
    drawAvatar()
  },
)
</script>

<template>
  <Teleport to="body">
    <dialog
      ref="dialogEl"
      class="share-dialog"
      aria-labelledby="share-title"
      @cancel.prevent="emit('close')"
      @click.self="emit('close')"
    >
      <div class="modal-window share-window">
        <div class="modal-head">
          <span id="share-title">[LINK] この投稿を共有</span>
          <button
            ref="closeEl"
            type="button"
            class="modal-close"
            aria-label="閉じる"
            @click="emit('close')"
          >
            ×
          </button>
        </div>

        <div class="modal-body">
          <p class="modal-note share-note">共有カード（プレビュー）</p>

          <!-- サイトの投稿カードと同じ配色・構成のプレビュー -->
          <NuxtLink
            class="share-card"
            :to="`/p/${post.id}`"
            target="_blank"
            rel="noopener"
            :aria-label="`${author} の投稿 #${post.id} を開く`"
          >
            <span class="share-card-top">
              <span>FLOPPY.IO / SHARED POST</span>
              <span>No.{{ post.id }}</span>
            </span>

            <span class="share-card-body">
              <span class="share-card-head">
                <span class="share-card-avatar">
                  <img v-if="avatarImage" :src="avatarImage" alt="" @error="onAvatarError" />
                  <canvas
                    v-else
                    ref="avatarCanvas"
                    width="16"
                    height="16"
                    aria-hidden="true"
                  ></canvas>
                </span>

                <span class="share-card-who">
                  <span class="share-card-name">{{ author }}</span>
                  <span class="share-card-handle">
                    @{{ post.username }}<template v-if="post.disk">
                      · [D] {{ post.disk.name }}</template>
                  </span>
                  <span class="share-card-sub">
                    {{ dateLabel }} {{ timeLabel }} /
                    {{ totalBytes.toLocaleString('ja-JP') }} bytes
                  </span>
                </span>

                <span class="share-card-kind">{{ postKind }}</span>
              </span>

              <span v-if="post.text" class="share-card-text">
                <template v-for="(part, i) in textParts" :key="i">
                  <span v-if="part.type === 'link'" class="share-card-link">{{ part.text }}</span>
                  <template v-else>{{ part.text }}</template>
                </template>
              </span>

              <span v-if="media" class="share-card-media">
                <span class="share-card-media-frame">
                  <img
                    v-if="media.type !== 'pixel'"
                    :src="media.src"
                    alt=""
                    loading="lazy"
                  />
                  <canvas
                    v-else
                    ref="canvas"
                    class="share-card-canvas"
                    width="16"
                    height="16"
                    aria-hidden="true"
                  ></canvas>
                  <span
                    v-if="media.type === 'youtube'"
                    class="share-card-play"
                    aria-hidden="true"
                  >
                    ▶
                  </span>
                </span>

                <span v-if="media.type === 'youtube'" class="share-card-youtube-meta">
                  ▶ {{ post.youtube_title || 'YouTube 動画' }}
                  <span class="share-card-youtube-open">YouTube で見る ↗</span>
                </span>
              </span>

              <span v-if="post.floppy_url" class="share-card-file">
                {{ post.floppy_kind === 'audio' ? '[♪]' : '[F]' }}
                {{ post.floppy_name || 'floppy.bin' }} ·
                {{ (Number(post.floppy_bytes) || 0).toLocaleString('ja-JP') }} bytes
              </span>

              <span class="share-card-actions" aria-hidden="true">
                <span class="share-card-like">
                  {{ post.liked ? '♥' : '♡' }} {{ likeCount }}
                </span>
                <span>↩ {{ replyCount }}</span>
                <span>{{ totalBytes.toLocaleString('ja-JP') }} bytes</span>
                <span class="share-card-open">↗ 投稿を開く</span>
              </span>
            </span>
          </NuxtLink>


          <!-- 共有先（X / LINE / リンク / 端末の共有シート） -->
          <div class="share-quick">
            <a
              class="share-action share-action-x"
              :href="xUrl"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span class="share-action-mark" aria-hidden="true">X</span>
              <span>X でポスト</span>
            </a>

            <a
              class="share-action share-action-line"
              :href="lineUrl"
              target="_blank"
              rel="noopener noreferrer"
            >
              <span class="share-action-mark" aria-hidden="true">L</span>
              <span>LINE で送る</span>
            </a>

            <button
              type="button"
              class="share-action"
              @click="copy(shareUrl, 'link')"
            >
              <span class="share-action-mark" aria-hidden="true">[→]</span>
              <span>{{ copied === 'link' ? 'コピー済み' : 'リンクをコピー' }}</span>
            </button>

            <button
              v-if="canNativeShare"
              type="button"
              class="share-action"
              @click="useNativeShare"
            >
              <span class="share-action-mark" aria-hidden="true">[↗]</span>
              <span>共有メニュー</span>
            </button>
          </div>

          <p class="share-status" role="status" aria-live="polite">
            {{ statusMessage }}
          </p>

          <p class="modal-note">共有リンク</p>
          <div class="share-link-row">
            <input
              class="input share-link"
              type="text"
              readonly
              :value="shareUrl"
              aria-label="共有リンク"
              @focus="$event.target.select()"
            />
            <button
              type="button"
              class="btn btn-sm"
              @click="copy(shareUrl, 'link')"
            >
              {{ copied === 'link' ? 'コピー済み' : 'コピー' }}
            </button>
          </div>

          <!-- 外部サイトへ貼り付ける HTML（失敗時は再試行できる） -->
          <details class="share-embed" @toggle="onEmbedToggle">
            <summary>埋め込み HTML（外部サイト用）</summary>

            <div class="share-embed-body">
              <p v-if="previewState === 'loading'" class="panel-note">
                読み込み中…
              </p>

              <template v-else-if="previewState === 'error'">
                <p class="panel-note">埋め込み HTML を取得できませんでした。</p>
                <button type="button" class="btn btn-sm" @click="loadPreview">
                  再試行
                </button>
              </template>

              <template v-else>
                <textarea
                  class="input embed-code allow-copy"
                  readonly
                  :value="embedHtml"
                  aria-label="埋め込み HTML"
                ></textarea>
                <div class="share-actions">
                  <button
                    type="button"
                    class="btn btn-sm"
                    @click="copy(embedHtml, 'embed')"
                  >
                    {{ copied === 'embed' ? 'コピー済み' : 'HTML をコピー' }}
                  </button>
                </div>
              </template>
            </div>
          </details>
        </div>
      </div>
    </dialog>
  </Teleport>
</template>
