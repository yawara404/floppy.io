<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { drawPixelContained, FLOPPY_AVATAR } from '~/utils/pixel'
import { resolveMediaUrl } from '~/utils/api'

const props = defineProps({
  post: { type: Object, required: true },
})

const canvas = ref(null)

// API から total_bytes が欠けた場合でも表示が落ちないように数値化する
const totalBytes = computed(() => Number(props.post?.total_bytes) || 0)

// 共有ページでも画像 / YouTube のサムネイルを 1 枚だけ出す
const mediaSrc = computed(() => {
  if (props.post?.image_url) return resolveMediaUrl(props.post.image_url)
  if (props.post?.youtube_id) {
    return (
      props.post.youtube_thumbnail ||
      `https://i.ytimg.com/vi/${props.post.youtube_id}/hqdefault.jpg`
    )
  }
  return ''
})

function render() {
  if (!canvas.value) return

  const pixel = props.post?.pixel_data || ''

  // ドット絵が無い投稿（画像・YouTube・フロッピー添付のみ等）は
  // 空白のままになるため、フロッピーアイコンを表示する
  const blank = !/[1-9A-Fa-f]/.test(pixel)

  if (blank) {
    drawPixelContained(canvas.value, FLOPPY_AVATAR)
  } else {
    drawPixelContained(
      canvas.value,
      pixel,
      props.post?.pixel_width,
      props.post?.pixel_height,
    )
  }
}

onMounted(render)
watch(() => [props.post?.pixel_data, props.post?.id], render)
</script>

<template>
  <div class="floppy-card">
    <div class="floppy-card-visual">
      <canvas ref="canvas" class="pixel-preview" width="16" height="16"></canvas>
      <span class="floppy-card-diskno">
        #{{ String(post.id || 0).padStart(2, '0') }}
      </span>
    </div>

    <div class="floppy-card-body">
      <div class="floppy-card-brand">floppy.io / shared disk</div>
      <p v-if="post.text" class="floppy-card-text">{{ post.text }}</p>

      <img
        v-if="mediaSrc"
        class="floppy-card-media"
        :src="mediaSrc"
        alt=""
        loading="lazy"
      />

      <!-- 添付フロッピーファイル（音声はプレイヤー付き） -->
      <div v-if="post.floppy_url" class="floppy-card-file">
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

      <div class="floppy-card-meta">
        @{{ post.username }} · {{ totalBytes.toLocaleString('ja-JP') }} bytes
        <template v-if="post.disk"> · [D] {{ post.disk.name }}</template>
      </div>
    </div>
  </div>
</template>
