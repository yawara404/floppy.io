<script setup>
import { ref, computed, onBeforeUnmount, nextTick, useId, watch } from 'vue'
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
  messageBar: { type: Boolean, default: false },
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
const toolsOpen = ref(false)
const toolsId = useId()
const pixelId = useId()
const pixelPanel = ref(null)

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
const hasDraft = computed(() => Boolean(
  text.value.trim() || !pixelIsBlank(pixelData.value) || imageFile.value || floppyFile.value,
))

watch(showEditor, (open) => {
  if (open && props.messageBar) pixelPanel.value?.showModal()
}, { flush: 'post' })

function closeEditor() {
  pixelPanel.value?.close?.()
  showEditor.value = false
}

function onComposerKeydown(event) {
  if (event.key !== 'Enter' || event.isComposing || event.keyCode === 229) return
  const desktopEnter = props.messageBar && !event.shiftKey && !event.altKey
    && !window.matchMedia('(pointer: coarse)').matches
  if (!event.metaKey && !event.ctrlKey && !desktopEnter) return
  event.preventDefault()
  if (!props.messageBar || hasDraft.value) submit()
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
  if (loading.value) return
  error.value = ''

  if (!hasDraft.value) {
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
    toolsOpen.value = false
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
  <section class="composer" :class="{ 'composer-message-bar': messageBar }">
    <div v-if="!messageBar" class="composer-head">
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

    <div :class="{ 'composer-message-row': messageBar }">
      <button
        v-if="messageBar"
        type="button"
        class="btn composer-add-tools"
        aria-label="メッセージツール"
        :aria-expanded="toolsOpen"
        :aria-controls="toolsId"
        :disabled="loading"
        @click="toolsOpen = !toolsOpen"
      ><span aria-hidden="true">{{ toolsOpen ? '−' : '+' }}</span></button>
      <textarea
        id="post-text"
        ref="textareaRef"
        v-model="text"
        class="input"
        :aria-label="messageBar ? 'メッセージの本文' : '投稿の本文'"
        :aria-invalid="overLimit"
        :readonly="messageBar && loading"
        :rows="messageBar ? 1 : 4"
        @keydown="onComposerKeydown"
        :placeholder="messageBar ? 'メッセージを書く' : '1.44MB まで書けます。容量と相談しながら、残したい言葉を。'"
      ></textarea>
      <button
        v-if="messageBar"
        type="button"
        class="btn btn-primary publish-btn"
        :disabled="loading || overLimit || !hasDraft"
        @click="submit"
      >{{ loading ? '送信中…' : '送信' }}</button>
    </div>

    <DiskGauge
      v-if="!messageBar"
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

    <div v-show="!messageBar || toolsOpen" :id="toolsId" class="composer-row">
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

        <button type="button" class="link-btn" :aria-expanded="showEditor" :aria-controls="showEditor ? pixelId : undefined" @click="showEditor = !showEditor">
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
        <span v-if="floppyFile && !messageBar" class="image-meta">
          [F] {{ floppyFile.name }} · {{ formatNumber(floppyBytes) }} bytes
        </span>
        <button
          v-if="floppyFile && !messageBar"
          type="button"
          class="link-btn danger"
          @click="clearFloppy"
        >
          ✕ 外す
        </button>
      </div>

      <span v-if="!messageBar" class="spacer"></span>

      <button
        v-if="!messageBar"
        type="button"
        class="btn btn-primary publish-btn"
        :disabled="loading || overLimit"
        @click="submit"
      >
        {{ loading ? '書き込み中…' : '投稿する' }}
        <span aria-hidden="true">⏎</span>
      </button>
    </div>

    <div v-if="messageBar" class="composer-message-meta">
      <div v-if="floppyFile" class="composer-attached-file">
        <span>{{ floppyFile.name }}</span>
        <button type="button" class="link-btn" aria-label="添付ファイルを外す" @click="clearFloppy">外す</button>
      </div>
      <span v-if="!pixelIsBlank(pixelData)" class="composer-pixel-attached">ドット絵あり</span>
      <div class="composer-byte-count" :class="{ 'input-over-limit': overLimit }">
        <meter
          aria-label="このメッセージの使用容量"
          :value="Math.min(draftBytes, DISK_LIMIT)"
          :max="DISK_LIMIT"
          :high="DISK_LIMIT * .9"
        ></meter>
        <span>{{ formatNumber(draftBytes) }} / {{ formatNumber(DISK_LIMIT) }} bytes</span>
      </div>
      <p v-if="overLimit" class="composer-limit-error" role="status">1.44MBの上限を超えています。</p>
    </div>

    <AAStampPicker v-if="showAA" @select="insertStamp" @close="showAA = false" />

    <component
      :is="messageBar ? 'dialog' : 'div'"
      v-if="showEditor"
      :id="pixelId"
      ref="pixelPanel"
      :class="messageBar ? 'composer-pixel-dialog' : undefined"
      :aria-label="messageBar ? 'ドット絵エディタ' : undefined"
      @cancel.prevent="closeEditor"
    >
      <PixelEditor
        v-model="pixelData"
        :canvas-width="pixelWidth"
        :canvas-height="pixelHeight"
        @resize="onPixelResize"
      />
      <button v-if="messageBar" type="button" class="btn btn-primary" @click="closeEditor">完了</button>
    </component>
  </section>
</template>

<style scoped>
.composer.composer-message-bar {
  padding: .65rem .75rem .45rem;
  border: 1px solid var(--line-strong);
  border-radius: 0;
  background: var(--paper);
  box-shadow: 3px 3px 0 var(--shadow);
}

.composer-message-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: end;
  gap: .5rem;
}

.composer-message-row .btn {
  min-height: 44px;
  white-space: nowrap;
}

.composer-add-tools {
  min-width: 44px;
  color: var(--accent-deep);
  font-family: var(--font-mono);
  font-size: 1.3rem;
}

.composer-message-bar textarea.input {
  field-sizing: content;
  min-height: 44px;
  max-height: calc(var(--disk-visible-height, 100dvh) * .22);
  padding: .5rem .6rem;
  resize: none;
  background: var(--paper-2);
  font-size: 1rem;
  line-height: 1.6;
}

.composer-message-bar .composer-tools {
  width: 100%;
  flex-wrap: nowrap;
  gap: .3rem;
  margin: 0;
  overflow-x: auto;
}

.composer-message-bar .composer-tools button {
  flex-shrink: 0;
  white-space: nowrap;
}

.composer-message-bar .image-preview img {
  max-height: 64px;
  width: auto;
}

.composer-message-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: .3rem .6rem;
  padding-top: .35rem;
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: .75rem;
}

.composer-byte-count,
.composer-attached-file {
  display: flex;
  align-items: center;
  gap: .4rem;
  min-width: 0;
}

.composer-attached-file span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.composer-byte-count {
  margin-inline-start: auto;
  white-space: nowrap;
}

.composer-byte-count meter {
  width: 3.75rem;
  height: .5rem;
}

.composer-byte-count.input-over-limit,
.composer-limit-error {
  color: var(--danger);
}

.composer-limit-error {
  width: 100%;
  margin: 0;
  text-align: end;
}

.composer-pixel-dialog {
  width: min(640px, calc(100% - 24px));
  max-height: calc(100dvh - 24px);
  margin: auto;
  padding: .8rem;
  overflow: auto;
  border: 2px solid var(--ink);
  background: var(--paper);
  color: var(--ink);
}

.composer-pixel-dialog::backdrop {
  background: rgb(25 37 29 / 52%);
}

.composer-pixel-dialog .btn-primary {
  margin-top: .75rem;
}
</style>
