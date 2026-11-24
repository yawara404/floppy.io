<script setup>
import { ref, computed, onBeforeUnmount, nextTick } from 'vue'
import AAStampPicker from './AAStampPicker.vue'
import DiskGauge from './DiskGauge.vue'
import PixelEditor from './PixelEditor.vue'
import { apiPost, apiUpload } from '~/utils/api'
import { refreshUser } from '~/composables/useAuth'
import { blankPixel, pixelIsBlank } from '~/utils/pixel'
import { formatNumber } from '~/utils/format'

const props = defineProps({
  // 書き込み先のディスク (コミュニティ)。null ならホームへ投稿する。
  disk: { type: Object, default: null },
})

const emit = defineEmits(['posted'])

const DISK_LIMIT = 1474560
const DEFAULT_PIXEL_WIDTH = 32
const DEFAULT_PIXEL_HEIGHT = 32

const text = ref('')
const textareaRef = ref(null)
const pixelData = ref(blankPixel(DEFAULT_PIXEL_WIDTH, DEFAULT_PIXEL_HEIGHT))
const pixelWidth = ref(DEFAULT_PIXEL_WIDTH)
const pixelHeight = ref(DEFAULT_PIXEL_HEIGHT)

// 選択中のキャンバスサイズ（正方形 / Miiverse / クラシック）
const pixelBytes = computed(() => pixelWidth.value * pixelHeight.value)

function onPixelResize(size) {
  pixelWidth.value = size.width
  pixelHeight.value = size.height
}
const showEditor = ref(false)
const showAA = ref(false)

const loading = ref(false)
const error = ref('')

function openStampPicker(event) {
  event.currentTarget.focus({ preventScroll: true })
  showAA.value = true
}

function insertStamp(stamp) {
  const value = String(stamp || '')
  if (!value) return

  const textarea = textareaRef.value
  const start = textarea?.selectionStart ?? text.value.length
  const end = textarea?.selectionEnd ?? text.value.length
  const before = text.value.slice(0, start)
  const after = text.value.slice(end)

  // 1 行の顔文字は前後に半角スペース、複数行の AA は前後に改行を補う。
  const singleLine = !value.includes('\n')
  const prefix = singleLine
    ? before && !/\s$/.test(before)
      ? ' '
      : ''
    : before && !/\n$/.test(before)
      ? '\n'
      : ''
  const suffix = singleLine
    ? after && !/^\s/.test(after)
      ? ' '
      : ''
    : after && !/^\n/.test(after)
      ? '\n'
      : ''
  const inserted = prefix + value + suffix

  text.value = before + inserted + after
  showAA.value = false

  nextTick(() => {
    if (!textarea) return
    textarea.focus()
    const position = (before + inserted).length
    textarea.setSelectionRange(position, position)
  })
}

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
// メーターは、いま書いている投稿の消費バイト数（本文 + ドット絵 + 画像）を表示する。
const draftBytes = computed(
  () =>
    new TextEncoder().encode(text.value).length +
    pixelBytes.value +
    imageBytes.value +
    floppyBytes.value,
)
const overLimit = computed(() => draftBytes.value > DISK_LIMIT)

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
  if (loading.value) return
  error.value = ''

  if (
    !text.value.trim() &&
    pixelIsBlank(pixelData.value) &&
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
      form.append('pixel_width', String(pixelWidth.value))
      form.append('pixel_height', String(pixelHeight.value))
      if (props.disk?.id) form.append('disk_id', String(props.disk.id))
      if (imageFile.value) form.append('image', imageFile.value)
      if (floppyFile.value) form.append('floppy', floppyFile.value)
      data = await apiUpload('/posts', form)
    } else {
      data = await apiPost('/posts', {
        text: text.value,
        pixel_data: pixelData.value,
        pixel_width: pixelWidth.value,
        pixel_height: pixelHeight.value,
        ...(props.disk?.id ? { disk_id: props.disk.id } : {}),
      })
    }

    text.value = ''
    pixelData.value = blankPixel(pixelWidth.value, pixelHeight.value)
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
    <div class="composer-head">
      <div>
        <h2 class="composer-title">いま、なにを残す？</h2>
        <NuxtLink
          v-if="disk"
          class="composer-disk"
          :to="'/d/' + disk.slug"
        >
          <span class="composer-disk-key">[D]</span>
          {{ disk.name }} に書き込む
        </NuxtLink>
      </div>
      <span class="composer-led"><span class="pulse-dot"></span>REC</span>
    </div>

    <textarea
      id="post-text"
      ref="textareaRef"
      v-model="text"
      class="input"
      aria-label="投稿の本文"
      :aria-invalid="overLimit"
      rows="4"
      @keydown.meta.enter.prevent="submit"
      @keydown.ctrl.enter.prevent="submit"
      placeholder="1.44MB まで書けます。容量と相談しながら、残したい言葉を。"
    ></textarea>

    <!-- 容量メーター：いま書いている投稿の消費バイト数（1投稿 = 1.44MB） -->
    <DiskGauge
      :used="draftBytes"
      :limit="DISK_LIMIT"
      label="DISK (C:) / この投稿"
    />

    <p v-if="imageError" class="msg msg-error" role="alert" style="margin: 10px 0 0">
      {{ imageError }}
    </p>

    <p v-if="floppyError" class="msg msg-error" role="alert" style="margin: 10px 0 0">
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

    <p v-if="error" class="msg msg-error" role="alert" style="margin: 10px 0 0">
      {{ error }}
    </p>

    <div class="composer-row">
      <div class="composer-tools">
        <button
          type="button"
          class="link-btn"
          :class="{ active: showAA }"
          aria-haspopup="dialog"
          :aria-expanded="showAA"
          :aria-controls="showAA ? 'aa-panel' : undefined"
          @click="openStampPicker"
        >
          [AA] スタンプ
        </button>

        <button type="button" class="link-btn" :aria-expanded="showEditor" aria-controls="pixel-panel" @click="showEditor = !showEditor">
          {{ showEditor ? '▾ ドット絵を閉じる' : '▸ ドット絵を描く' }}
        </button>

        <button type="button" class="link-btn" @click="fileInput?.click()">[IMG] 画像</button>
        <button type="button" class="link-btn" @click="floppyInput?.click()">[FILE] ファイル</button>

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
          {{ formatNumber(imageBytes) }} bytes
        </span>
        <span v-if="floppyFile" class="image-meta">
          [F] {{ floppyFile.name }} · {{ formatNumber(floppyBytes) }} bytes
        </span>
        <button
          v-if="floppyFile"
          type="button"
          class="link-btn danger"
          @click="clearFloppy"
        >
          ✕ 外す
        </button>
      </div>

      <span class="spacer"></span>

      <button
        type="button"
        class="btn btn-primary publish-btn"
        :disabled="loading || overLimit"
        @click="submit"
      >
        {{ loading ? '書き込み中…' : '投稿する' }}
        <span aria-hidden="true">⏎</span>
      </button>
    </div>

    <AAStampPicker v-if="showAA" @select="insertStamp" @close="showAA = false" />

    <PixelEditor
      v-if="showEditor"
      id="pixel-panel"
      v-model="pixelData"
      :canvas-width="pixelWidth"
      :canvas-height="pixelHeight"
      @resize="onPixelResize"
    />
  </section>
</template>
