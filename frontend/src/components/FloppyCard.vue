<script setup>
import { ref, onMounted, watch } from 'vue'
import { drawPixel, FLOPPY_AVATAR } from '../utils/pixel.js'

const props = defineProps({
  post: { type: Object, required: true },
})

const canvas = ref(null)

function render() {
  if (!canvas.value) return

  const pixel = props.post?.pixel_data || ''

  // ドット絵が無い投稿（画像・YouTube・フロッピー添付のみ等）は
  // 空白のままになるため、フロッピーアイコンを表示する
  const blank = !/[1-9A-Fa-f]/.test(pixel)

  drawPixel(canvas.value, blank ? FLOPPY_AVATAR : pixel)
}

onMounted(render)
watch(() => [props.post?.pixel_data, props.post?.id], render)
</script>

<template>
  <div class="floppy-card">
    <canvas ref="canvas" class="pixel-preview" width="16" height="16"></canvas>
    <div>
      <div class="floppy-card-brand">floppy.io</div>
      <p v-if="post.text" class="floppy-card-text">{{ post.text }}</p>
      <!-- 添付フロッピーファイル（音声はプレイヤー付き） -->
      <div v-if="post.floppy_url" class="floppy-card-file">
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
            {{ post.floppy_kind === 'audio' ? '🎵' : '💾' }}
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
        @{{ post.username }} · {{ post.total_bytes.toLocaleString('ja-JP') }} bytes
      </div>
    </div>
  </div>
</template>
