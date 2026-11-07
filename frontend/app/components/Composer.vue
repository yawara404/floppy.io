<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import DiskGauge from './DiskGauge.vue'
import PixelEditor from './PixelEditor.vue'
import { apiPost, apiUpload } from '~/utils/api'
import { refreshUser } from '~/composables/useAuth'
import { blankPixel, pixelIsBlank } from '~/utils/pixel'

const props = defineProps({
  // 書き込み先のディスク (コミュニティ)。null ならホームへ投稿する。
  disk: { type: Object, default: null },
})

const emit = defineEmits(['posted'])

const DISK_LIMIT = 1474560
const DEFAULT_PIXEL_WIDTH = 32
const DEFAULT_PIXEL_HEIGHT = 32

// --- アスキーアートスタンプ ------------------------------------------------
const AA_STORAGE_KEY = 'floppy_aa_stamps_v1'
const AA_RECENT_KEY = 'floppy_aa_recent_v1'
const AA_MAX_LENGTH = 300
const AA_MAX_STAMPS = 50
const AA_RECENT_MAX = 12

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
const aaGroup = ref('kao')
const customStamps = ref([])
const recentStamps = ref([])
const stampQuery = ref('')
const newStamp = ref('')
const aaError = ref('')
const aaNotice = ref('')
let aaNoticeTimer = null

const loading = ref(false)
const error = ref('')

// よく使う + プリセット + 自作のタブ（LINE のスタンプ一覧を参考）
const aaTabs = computed(() => [
  { id: 'recent', label: 'よく使う', count: recentStamps.value.length },
  ...AA_GROUPS.map((group) => ({
    id: group.id,
    label: group.label,
    count: group.items.length,
  })),
  { id: 'custom', label: '自作', count: customStamps.value.length },
])

const aaPresets = computed(() => {
  const query = stampQuery.value.trim().toLowerCase()

  let items = []
  if (aaGroup.value === 'recent') items = recentStamps.value
  else if (aaGroup.value === 'custom') items = customStamps.value
  else items = AA_GROUPS.find((group) => group.id === aaGroup.value)?.items || []

  if (!query) return items
  return items.filter((stamp) => stamp.toLowerCase().includes(query))
})

const aaEmptyMessage = computed(() => {
  if (stampQuery.value.trim()) return '該当するスタンプがありません。'
  if (aaGroup.value === 'recent') {
    return 'まだ使ったスタンプがありません。スタンプを挿入するとここに並びます。'
  }
  if (aaGroup.value === 'custom') {
    return 'まだ自作スタンプがありません。下の欄から保存できます。'
  }
  return 'スタンプがありません。'
})

function rememberStamp(stamp) {
  const value = String(stamp || '')
  if (!value) return

  recentStamps.value = [
    value,
    ...recentStamps.value.filter((used) => used !== value),
  ].slice(0, AA_RECENT_MAX)

  try {
    window.localStorage.setItem(AA_RECENT_KEY, JSON.stringify(recentStamps.value))
  } catch {
    // ローカル保存に失敗しても挿入自体は続行する
  }
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
  rememberStamp(value)

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

  // 最近使ったスタンプ（よく使うタブ）
  try {
    const raw = window.localStorage.getItem(AA_RECENT_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    if (Array.isArray(parsed)) {
      recentStamps.value = parsed
        .filter((stamp) => typeof stamp === 'string' && stamp.trim() !== '')
        .slice(0, AA_RECENT_MAX)
    }
  } catch {
    recentStamps.value = []
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
// メーターは、いま書いている投稿の消費バイト数（本文 + ドット絵 + 画像）を表示する。
const draftBytes = computed(
  () =>
    new TextEncoder().encode(text.value).length +
    pixelBytes.value +
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
          :aria-expanded="showAA"
          aria-controls="aa-panel"
          @click="showAA = !showAA"
        >
          {{ showAA ? '▾ AA スタンプ' : '▸ AA スタンプ' }}
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
    <div v-if="showAA" id="aa-panel" class="aa-panel">
      <div class="aa-head">
        <span class="aa-title">[AA] STAMP LIBRARY</span>
        <div class="aa-head-right">
          <span class="aa-local">LOCAL SAVE</span>
          <button type="button" class="link-btn" @click="showAA = false">
            閉じる ×
          </button>
        </div>
      </div>

      <div class="aa-search-row">
        <input
          v-model="stampQuery"
          class="input aa-search"
          type="search"
          placeholder="スタンプを検索（例: 猫, 枠, お祝い）"
          aria-label="スタンプを検索"
        />
        <button
          v-if="stampQuery"
          type="button"
          class="btn btn-sm"
          @click="stampQuery = ''"
        >
          クリア
        </button>
      </div>

      <div class="aa-tabs" role="group" aria-label="スタンプの種類">
        <button
          v-for="tab in aaTabs"
          :key="tab.id"
          type="button"
          class="aa-tab"
          :class="{ active: aaGroup === tab.id }"
          :aria-pressed="aaGroup === tab.id"
          @click="aaGroup = tab.id"
        >
          {{ tab.label }}
          <span class="aa-tab-count">{{ tab.count }}</span>
        </button>
      </div>

      <div
        v-if="recentStamps.length && aaGroup !== 'recent' && !stampQuery"
        class="aa-recent"
      >
        <span class="aa-recent-label">最近使った</span>
        <button
          v-for="stamp in recentStamps.slice(0, 6)"
          :key="'recent-' + stamp"
          type="button"
          class="aa-recent-item"
          :title="stamp"
          @click="insertStamp(stamp)"
        >
          {{ stamp }}
        </button>
      </div>

      <p v-if="aaPresets.length === 0" class="aa-empty">
        {{ aaEmptyMessage }}
      </p>

      <div v-else class="aa-grid">
        <div
          v-for="stamp in aaPresets"
          :key="stamp"
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
            v-if="aaGroup === 'custom'"
            type="button"
            class="aa-delete"
            aria-label="このスタンプを削除"
            @click="removeCustomStamp(customStamps.indexOf(stamp))"
          >
            ×
          </button>
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
        <div class="aa-actions" aria-live="polite">
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
