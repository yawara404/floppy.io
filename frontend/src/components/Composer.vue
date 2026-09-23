<script setup>
import { ref, computed, onBeforeUnmount } from 'vue'
import DiskGauge from './DiskGauge.vue'
import PixelEditor from './PixelEditor.vue'
import { apiPost, apiUpload } from '../utils/api.js'
import { refreshUser } from '../store/auth.js'

const emit = defineEmits(['posted'])

const DISK_LIMIT = 1474560
const PIXEL_BYTES = 256
const BLANK_PIXEL = '0'.repeat(256)

const text = ref('')
const pixelData = ref(BLANK_PIXEL)
const showEditor = ref(false)
const loading = ref(false)
const error = ref('')

// 添付画像（画像のバイト数も 1 投稿の容量に含める）
const fileInput = ref(null)
const imageFile = ref(null)
const imagePreview = ref('')
const imageBytes = ref(0)
const imageError = ref('')

// 添付フロッピーファイル（バイト数も容量に含める）
const floppyInput = ref(null)
const floppyFile = ref(null)
const floppyBytes = ref(0)
const floppyError = ref('')

// 容量制限は「1 投稿あたり 1.44MB」。
// メーターは、いま書いている投稿の消費バイト数（本文 + ドット絵 256 + 画像）を表示する。
const draftBytes = computed(
  () =>
    new TextEncoder().encode(text.value).length +
    PIXEL_BYTES +
    imageBytes.value +
    floppyBytes.value,
)
const overLimit = computed(() => draftBytes.value > DISK_LIMIT)

function fmt(n) {
  return n.toLocaleString('ja-JP')
}

function onFileChange(event) {
  const file = event.target.files?.[0]
  if (!file) return

  imageError.value = ''

  if (!file.type.startsWith('image/')) {
    imageError.value = '画像ファイルを選んでください。'
    return
  }

  if (file.size > DISK_LIMIT) {
    imageError.value = '画像が大きすぎます（1 枚で 1.44MB まで）。'
    return
  }

  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  imageFile.value = file
  imageBytes.value = file.size
  imagePreview.value = URL.createObjectURL(file)
}

function onFloppyChange(event) {
  const file = event.target.files?.[0]
  if (!file) return

  floppyError.value = ''

  if (file.size > DISK_LIMIT) {
    floppyError.value = 'フロッピーファイルは 1.44MB 以内にしてください。'
    return
  }

  floppyFile.value = file
  floppyBytes.value = file.size
  error.value = ''
}

function clearFloppy() {
  floppyFile.value = null
  floppyBytes.value = 0
  if (floppyInput.value) floppyInput.value.value = ''
}

function clearImage() {
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  imageFile.value = null
  imageBytes.value = 0
  imagePreview.value = ''
  if (fileInput.value) fileInput.value.value = ''
}

async function submit() {
  error.value = ''

  if (
    !text.value.trim() &&
    pixelData.value === BLANK_PIXEL &&
    !imageFile.value &&
    !floppyFile.value
  ) {
    error.value = '本文・ドット絵・画像・フロッピーファイルのいずれかを入力してください。'
    return
  }

  if (overLimit.value) {
    error.value = '1 投稿あたりの容量上限（1.44MB）を超えています。'
    return
  }

  loading.value = true
  try {
    let data

    if (imageFile.value || floppyFile.value) {
      const form = new FormData()
      form.append('text', text.value)
      form.append('pixel_data', pixelData.value)
      if (imageFile.value) form.append('image', imageFile.value)
      if (floppyFile.value) form.append('floppy', floppyFile.value)
      data = await apiUpload('/posts.php', form)
    } else {
      data = await apiPost('/posts.php', {
        text: text.value,
        pixel_data: pixelData.value,
      })
    }

    text.value = ''
    pixelData.value = BLANK_PIXEL
    showEditor.value = false
    clearImage()
    clearFloppy()
    await refreshUser()
    emit('posted', data.post)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onBeforeUnmount(() => {
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
})
</script>

<template>
  <section class="composer">
    <h2 class="composer-title">いまどうしてる？</h2>

    <textarea
      v-model="text"
      class="input"
      rows="3"
      placeholder="1.44MB まで書けます…（容量を消費します）"
    ></textarea>

    <!-- 容量メーター：いま書いている投稿の消費バイト数（1投稿 = 1.44MB） -->
    <DiskGauge
      :used="draftBytes"
      :limit="DISK_LIMIT"
      label="💾 DISK (C:) この投稿"
    />

    <p v-if="imageError" class="msg msg-error" style="margin: 10px 0 0">
      {{ imageError }}
    </p>

    <p v-if="floppyError" class="msg msg-error" style="margin: 10px 0 0">
      {{ floppyError }}
    </p>

    <div v-if="imagePreview" class="image-preview">
      <img :src="imagePreview" alt="添付画像のプレビュー" />
      <button
        type="button"
        class="image-remove"
        aria-label="画像を外す"
        @click="clearImage"
      >
        ×
      </button>
    </div>

    <p v-if="error" class="msg msg-error" style="margin: 10px 0 0">
      {{ error }}
    </p>

    <div class="composer-row">
      <button type="button" class="link-btn" @click="showEditor = !showEditor">
        {{ showEditor ? '▾ ドット絵を隠す' : '▸ ドット絵を描く' }}
      </button>

      <label class="link-btn" for="post-image">🖼 画像を添付</label>
      <label class="link-btn" for="post-floppy">💾 フロッピーを添付</label>
      <input
        id="post-floppy"
        ref="floppyInput"
        class="image-input"
        type="file"
        @change="onFloppyChange"
      />
      <input
        id="post-image"
        ref="fileInput"
        class="image-input"
        type="file"
        accept="image/*"
        @change="onFileChange"
      />
      <span v-if="imageBytes" class="image-meta">
        {{ fmt(imageBytes) }} bytes
      </span>
      <span v-if="floppyFile" class="image-meta">
        💾 {{ floppyFile.name }} · {{ fmt(floppyBytes) }} bytes
      </span>
      <button
        v-if="floppyFile"
        type="button"
        class="link-btn danger"
        @click="clearFloppy"
      >
        ✕ 外す
      </button>

      <span class="spacer"></span>
      <button
        type="button"
        class="btn btn-primary"
        :disabled="loading || overLimit"
        @click="submit"
      >
        {{ loading ? '書き込み中…' : '投稿する' }}
      </button>
    </div>

    <PixelEditor v-if="showEditor" v-model="pixelData" />
  </section>
</template>
