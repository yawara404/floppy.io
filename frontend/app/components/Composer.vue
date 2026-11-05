<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import DiskGauge from './DiskGauge.vue'
import PixelEditor from './PixelEditor.vue'
import { apiPost, apiUpload } from '~/utils/api'
import { refreshUser } from '~/composables/useAuth'

const emit = defineEmits(['posted'])

const DISK_LIMIT = 1474560
const PIXEL_BYTES = 256
const BLANK_PIXEL = '0'.repeat(256)

// --- アスキーアートスタンプ ------------------------------------------------
const AA_STORAGE_KEY = 'floppy_aa_stamps_v1'
const AA_MAX_LENGTH = 300
const AA_MAX_STAMPS = 50

const AA_GROUPS = [
  {
    id: 'kao',
    label: '顔文字',
    items: [
      '(´・ω・｀)',
      '( ˘ω˘ )',
      '(・∀・)',
      '(ﾟ∀ﾟ)',
      '＼(^o^)／',
      '＿|￣|○',
      '(´；ω；｀)',
      '┌(┌^o^)┐',
      '( ｀ω´ )',
      '(´∀｀*)',
    ],
  },
  {
    id: 'bbs',
    label: 'BBS',
    items: [
      'ｷﾀ━━━━(ﾟ∀ﾟ)━━━━!!',
      'お(^ω^)',
      '乙',
      '>>1',
      '【速報】',
      'それな',
      'ワロタ',
      '（´∀｀）',
      '∧＿∧\n( ｀・ω・)',
    ],
  },
  {
    id: 'frame',
    label: 'フレーム',
    items: [
      '┌─────────┐\n│ floppy  │\n└─────────┘',
      '┏━━━━━━━━┓\n┃ 1.44MB ┃\n┗━━━━━━━━┛',
      '+----------+\n| floppy.io |\n+----------+',
      '／￣￣￣￣￣＼\n|  floppy.io  |\n＼＿＿＿＿＿／',
    ],
  },
  {
    id: 'pixel',
    label: 'ドット',
    items: ['■□■□■', '▄▀▄▀▄', '░▒▓█', '[■■■□□]', '██████', '▀▄▀▄▀', '●○●○●'],
  },
]

const text = ref('')
const textareaRef = ref(null)
const pixelData = ref(BLANK_PIXEL)
const showEditor = ref(false)
const showAA = ref(false)
const aaGroup = ref('kao')
const customStamps = ref([])
const newStamp = ref('')
const aaError = ref('')
const aaNotice = ref('')
let aaNoticeTimer = null

const loading = ref(false)
const error = ref('')

const aaPresets = computed(
  () => AA_GROUPS.find((group) => group.id === aaGroup.value)?.items || [],
)

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

  nextTick(() => {
    if (!textarea) return
    textarea.focus()
    const position = (before + inserted).length
    textarea.setSelectionRange(position, position)
  })
}

function loadCustomStamps() {
  if (typeof window === 'undefined') return
  try {
    const raw = window.localStorage.getItem(AA_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    if (Array.isArray(parsed)) {
      customStamps.value = parsed
        .filter((stamp) => typeof stamp === 'string' && stamp.trim() !== '')
        .map((stamp) => [...stamp].slice(0, AA_MAX_LENGTH).join(''))
        .slice(0, AA_MAX_STAMPS)
    }
  } catch {
    customStamps.value = []
  }
}

function persistCustomStamps() {
  try {
    window.localStorage.setItem(
      AA_STORAGE_KEY,
      JSON.stringify(customStamps.value),
    )
    return true
  } catch {
    return false
  }
}

function flashNotice(message, isError = false) {
  if (isError) {
    aaError.value = message
    aaNotice.value = ''
  } else {
    aaNotice.value = message
    aaError.value = ''
  }
  if (aaNoticeTimer) clearTimeout(aaNoticeTimer)
  aaNoticeTimer = setTimeout(() => {
    aaNotice.value = ''
    aaError.value = ''
  }, 2600)
}

function addCustomStamp() {
  // 先頭の空白は AA の位置合わせに必要なので保持し、末尾だけ整える
  const value = newStamp.value.replace(/\s+$/, '')
  if (!value.trim()) {
    flashNotice('スタンプを入力してください。', true)
    return
  }

  if ([...value].length > AA_MAX_LENGTH) {
    flashNotice(`スタンプは ${AA_MAX_LENGTH} 文字以内にしてください。`, true)
    return
  }

  const existing = new Set([
    ...customStamps.value,
    ...AA_GROUPS.flatMap((group) => group.items),
  ])
  if (existing.has(value)) {
    flashNotice('同じスタンプが既にあります。', true)
    return
  }

  customStamps.value = [value, ...customStamps.value].slice(0, AA_MAX_STAMPS)
  if (!persistCustomStamps()) {
    flashNotice('ローカル保存に失敗しました（容量不足など）。', true)
    return
  }

  newStamp.value = ''
  aaGroup.value = 'custom'
  flashNotice('この端末に保存しました。')
}

function removeCustomStamp(index) {
  customStamps.value.splice(index, 1)
  if (!persistCustomStamps()) {
    flashNotice('ローカル保存に失敗しました。', true)
    return
  }
  flashNotice('スタンプを削除しました。')
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
      data = await apiUpload('/posts', form)
    } else {
      data = await apiPost('/posts', {
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

onMounted(loadCustomStamps)

onBeforeUnmount(() => {
  if (imagePreview.value) URL.revokeObjectURL(imagePreview.value)
  if (aaNoticeTimer) clearTimeout(aaNoticeTimer)
})
</script>

<template>
  <section class="composer">
    <div class="composer-head">
      <div>
        <p class="section-kicker">WRITE TO DISK</p>
        <h2 class="composer-title">いま、なにを残す？</h2>
      </div>
      <span class="composer-led"><span class="pulse-dot"></span>REC</span>
    </div>

    <textarea
      ref="textareaRef"
      v-model="text"
      class="input"
      rows="4"
      placeholder="1.44MB まで書けます。容量と相談しながら、残したい言葉を。"
    ></textarea>

    <!-- 容量メーター：いま書いている投稿の消費バイト数（1投稿 = 1.44MB） -->
    <DiskGauge
      :used="draftBytes"
      :limit="DISK_LIMIT"
      label="DISK (C:) / この投稿"
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
      <div class="composer-tools">
        <button
          type="button"
          class="link-btn"
          :class="{ active: showAA }"
          @click="showAA = !showAA"
        >
          {{ showAA ? '▾ AA スタンプ' : '▸ AA スタンプ' }}
        </button>

        <button type="button" class="link-btn" @click="showEditor = !showEditor">
          {{ showEditor ? '▾ ドット絵を閉じる' : '▸ ドット絵を描く' }}
        </button>

        <label class="link-btn" for="post-image">[IMG] 画像</label>
        <label class="link-btn" for="post-floppy">[FILE] ファイル</label>

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
          [F] {{ floppyFile.name }} · {{ fmt(floppyBytes) }} bytes
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

    <!-- アスキーアートスタンプ (自作は localStorage に保存) -->
    <div v-if="showAA" class="aa-panel">
      <div class="aa-head">
        <span class="aa-title">[AA] ASCII ART STAMPS</span>
        <span class="aa-local">LOCAL SAVE</span>
      </div>

      <div class="aa-tabs" role="tablist" aria-label="スタンプの種類">
        <button
          v-for="group in AA_GROUPS"
          :key="group.id"
          type="button"
          class="aa-tab"
          :class="{ active: aaGroup === group.id }"
          role="tab"
          :aria-selected="aaGroup === group.id ? 'true' : 'false'"
          @click="aaGroup = group.id"
        >
          {{ group.label }}
        </button>
        <button
          type="button"
          class="aa-tab"
          :class="{ active: aaGroup === 'custom' }"
          role="tab"
          :aria-selected="aaGroup === 'custom' ? 'true' : 'false'"
          @click="aaGroup = 'custom'"
        >
          自作 ({{ customStamps.length }})
        </button>
      </div>

      <div v-if="aaGroup !== 'custom'" class="aa-grid">
        <button
          v-for="stamp in aaPresets"
          :key="stamp"
          type="button"
          class="aa-stamp"
          :title="stamp"
          @click="insertStamp(stamp)"
        >
          <pre>{{ stamp }}</pre>
        </button>
      </div>

      <div v-else class="aa-custom">
        <p v-if="customStamps.length === 0" class="aa-empty">
          まだ自作スタンプがありません。下の欄から保存できます。
        </p>
        <div v-else class="aa-grid">
          <div
            v-for="(stamp, index) in customStamps"
            :key="stamp + index"
            class="aa-stamp-wrap"
          >
            <button
              type="button"
              class="aa-stamp"
              :title="stamp"
              @click="insertStamp(stamp)"
            >
              <pre>{{ stamp }}</pre>
            </button>
            <button
              type="button"
              class="aa-delete"
              aria-label="このスタンプを削除"
              @click="removeCustomStamp(index)"
            >
              ×
            </button>
          </div>
        </div>
      </div>

      <div class="aa-editor">
        <label class="field-label" for="aa-new">
          自作スタンプ（{{ AA_MAX_LENGTH }} 文字まで・この端末に保存）
        </label>
        <textarea
          id="aa-new"
          v-model="newStamp"
          class="input aa-input"
          rows="2"
          :maxlength="AA_MAX_LENGTH"
          placeholder="(´・ω・｀) や ┌────┐ │ AA │ └────┘"
        ></textarea>
        <div class="aa-actions">
          <button type="button" class="btn btn-sm btn-primary" @click="addCustomStamp">
            ローカルに保存
          </button>
          <span v-if="aaNotice" class="aa-notice">{{ aaNotice }}</span>
          <span v-if="aaError" class="aa-notice error">{{ aaError }}</span>
        </div>
        <p class="aa-hint">
          スタンプはこのブラウザにのみ保存されます（サーバーには送信されません）。
        </p>
      </div>
    </div>

    <PixelEditor v-if="showEditor" v-model="pixelData" />
  </section>
</template>
