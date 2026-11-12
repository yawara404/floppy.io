<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useAvatarCanvas } from '~/composables/useAvatarCanvas'
import { formatDateTime } from '~/utils/format'
import { hasPixelArt, postKindOf } from '~/utils/post'
import { useAvatarImage } from '~/composables/useAvatarImage'
import ReplyForm from './ReplyForm.vue'
import YouTubeEmbed from './YouTubeEmbed.vue'
import { isLoggedIn } from '~/composables/useAuth'
import { resolveMediaUrl } from '~/utils/api'

const props = defineProps({
  post: { type: Object, required: true },
  canDelete: { type: Boolean, default: false },
})

defineEmits(['delete', 'share', 'like'])

const router = useRouter()
const { canvas, draw: drawAvatar } = useAvatarCanvas(() => props.post)
const menuOpen = ref(false)
const confirming = ref(false)
const replying = ref(false)
const hasExcerpt = computed(() => {
  const text = String(props.post.text || '')
  return text.length > 220 || text.split('\n').length > 6
})
const excerpt = computed(() => {
  const text = String(props.post.text || '')
  return hasExcerpt.value ? `${text.slice(0, 220).split('\n').slice(0, 6).join('\n')}…` : text
})

// カード全体をクリックしたら個別ビュー（/p/:id）へ。
// ボタン・リンク・入力欄・メディア操作はそのまま動かす。
function openPost() {
  router.push(`/p/${props.post.id}`)
}

function onArticleClick(event) {
  if (event.defaultPrevented || event.button !== 0) return

  const target = event.target
  const interactive = target?.closest?.(
    'a, button, input, textarea, select, label, audio, video, iframe, form, ' +
      '.post-menu, .post-menu-backdrop',
  )
  if (interactive) return

  // テキスト選択中のクリックでは遷移しない
  const selection = typeof window !== 'undefined' ? window.getSelection?.() : null
  if (selection && String(selection).length > 0) return

  openPost()
}

// 返信を受け付けるか（投稿者の設定）。既定はオフ。
const repliesEnabled = computed(() => props.post.replies_enabled === true)

// total_bytes が欠けていても表示が落ちないように数値化する
const totalBytes = computed(() => Number(props.post.total_bytes) || 0)

function toggleReply() {
  if (!repliesEnabled.value) return
  replying.value = !replying.value
}

function onReplied() {
  props.post.reply_count = (props.post.reply_count || 0) + 1
  replying.value = false
}

// ドット絵が描かれていない投稿ではキャンバスを出さない
const hasPixel = computed(() => hasPixelArt(props.post))

// 投稿者のアイコン（プロフィール画像 / 32×32 アイコン / 最新の正方形ドット絵）。
// 読み込めない場合は投稿のドット絵 → 初期アイコン（フロッピー）の順に描く。
const {
  image: avatarImage,
  reset: resetAvatar,
  onError: markAvatarError,
} = useAvatarImage(() => props.post)

function onAvatarError() {
  markAvatarError()
  nextTick(drawAvatar)
}

// 投稿の種類ラベル（計器表示用）
const postKind = computed(() => postKindOf(props.post))

// 別の投稿に切り替わったとき / アイコンURLが変わったときは画像を再評価する
watch(
  () => [props.post.id, props.post.author_icon_url, props.post.author_avatar_url],
  async () => {
    resetAvatar()
    await nextTick()
  },
)
</script>

<template>
  <article class="post post-clickable" @click="onArticleClick">
    <div class="post-avatar">
      <img
        v-if="avatarImage"
        :src="avatarImage"
        class="post-avatar-image"
        alt=""
        loading="lazy"
        @error="onAvatarError"
      />
      <canvas
        v-else
        ref="canvas"
        class="post-pixel"
        width="16"
        height="16"
      ></canvas>
    </div>

    <div class="post-body">
      <div class="post-head">
        <NuxtLink class="post-user" :to="'/u/' + post.username">
          {{ post.display_name || post.username }}
        </NuxtLink>
        <span
          v-if="post.is_bot || ['hagumeta', 'heisei_vipper', 'adachi_rei'].includes(post.username)"
          class="bot-badge"
          title="自動コメント・自律Bot"
        >BOT</span>
        <span class="post-handle">@{{ post.username }}</span>
        <span class="post-bytes">[B] {{ totalBytes.toLocaleString('ja-JP') }} bytes</span>

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
        <NuxtLink
          class="post-no"
          :to="'/p/' + post.id"
          :aria-label="'投稿 No.' + post.id + ' を開く'"
        >No.{{ post.id }}</NuxtLink>
        <span class="post-dot">/</span>
        <span class="post-date">{{ formatDateTime(post.created_at) }}</span>
        <span class="post-dot">/</span>
        <span class="post-kind">{{ postKind }}</span>
        <template v-if="post.disk">
          <span class="post-dot">/</span>
          <NuxtLink class="post-disk" :to="'/d/' + post.disk.slug">
            [D] {{ post.disk.name }}
          </NuxtLink>
        </template>
        <template v-if="post.reply_to_id">
          <span class="post-dot">/</span>
          <NuxtLink class="post-reply-to" :to="'/p/' + post.reply_to_id">
            RE: #{{ post.reply_to_id }}
          </NuxtLink>
        </template>
      </div>

      <p v-if="post.text" class="post-text" :class="{ 'post-excerpt': hasExcerpt }">{{ excerpt }}</p>
      <NuxtLink v-if="hasExcerpt" class="post-read-more" :to="`/p/${post.id}`">続きを読む →</NuxtLink>

      <!-- YouTube 埋め込み（クリックするまで iframe を読み込まない） -->
      <YouTubeEmbed
        v-if="post.youtube_id"
        :video-id="post.youtube_id"
        :title="post.youtube_title"
        :thumbnail="post.youtube_thumbnail"
      />

      <a
        v-if="post.image_url"
        :href="resolveMediaUrl(post.image_url)"
        class="post-image-link"
        target="_blank"
        rel="noopener noreferrer"
      >
        <img
          :src="resolveMediaUrl(post.image_url)"
          class="post-image"
          loading="lazy"
          :alt="'@' + post.username + ' の画像'"
        />
      </a>

      <!-- 三点メニューのドロップダウン -->
      <div
        v-if="menuOpen"
        class="post-menu-backdrop"
        @click.stop="menuOpen = false"
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
              {{ (post.floppy_bytes || 0).toLocaleString('ja-JP') }} bytes をダウンロード
            </span>
          </span>
        </a>
      </div>

      <div v-if="confirming" class="post-actions post-confirm">
        <span class="confirm-text">
          この投稿を削除しますか？（{{ totalBytes.toLocaleString('ja-JP') }} bytes 解放）
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
