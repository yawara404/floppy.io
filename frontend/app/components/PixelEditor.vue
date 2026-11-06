<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import {
  PALETTE,
  GRID_SIZE,
  ICON_GRID_SIZE,
  CANVAS_PRESETS,
  parsePixelData,
  toPixelData,
} from '~/utils/pixel'

const props = defineProps({
  modelValue: { type: String, default: '' },
  canvasWidth: { type: Number, default: ICON_GRID_SIZE },
  canvasHeight: { type: Number, default: ICON_GRID_SIZE },
  // 投稿ではキャンバス切替を出す / アイコンは 32×32 固定
  allowResize: { type: Boolean, default: true },
  maxHistory: { type: Number, default: 60 },
})

const emit = defineEmits(['update:modelValue', 'resize'])

const SCALE = 16 // 1 ドット = 16 internal px

const width = ref(props.canvasWidth || GRID_SIZE)
const height = ref(props.canvasHeight || GRID_SIZE)
const grid = ref(parsePixelData(props.modelValue, width.value, height.value))
const selected = ref(3) // デフォルトは黒
const tool = ref('pen') // 'pen' | 'eraser'
const showGrid = ref(false)
const drawing = ref(false)
const canvas = ref(null)
let strokeDirty = false

// 履歴は「キャンバスサイズ + マス」のスナップショットで持つ（サイズ変更も undo 可能）
const history = ref([
  { width: width.value, height: height.value, cells: grid.value.slice() },
])
const cursor = ref(0)

const canUndo = computed(() => cursor.value > 0)
const canRedo = computed(() => cursor.value < history.value.length - 1)
const dotCount = computed(() => width.value * height.value)
const activePreset = computed(
  () =>
    CANVAS_PRESETS.find(
      (preset) =>
        preset.width === width.value && preset.height === height.value,
    )?.id || '',
)

function draw() {
  const el = canvas.value
  const ctx = el?.getContext('2d')
  if (!ctx) return

  el.width = width.value * SCALE
  el.height = height.value * SCALE

  for (let i = 0; i < grid.value.length; i++) {
    const x = (i % width.value) * SCALE
    const y = Math.floor(i / width.value) * SCALE
    ctx.fillStyle = PALETTE[grid.value[i]] || PALETTE[0]
    ctx.fillRect(x, y, SCALE, SCALE)
  }

  if (showGrid.value) {
    ctx.strokeStyle = 'rgba(35, 38, 43, 0.16)'
    ctx.lineWidth = 1
    for (let x = 0; x <= width.value; x++) {
      const px = x * SCALE + 0.5
      ctx.beginPath()
      ctx.moveTo(px, 0)
      ctx.lineTo(px, el.height)
      ctx.stroke()
    }
    for (let y = 0; y <= height.value; y++) {
      const py = y * SCALE + 0.5
      ctx.beginPath()
      ctx.moveTo(0, py)
      ctx.lineTo(el.width, py)
      ctx.stroke()
    }
  }
}

function emitValue() {
  emit('update:modelValue', toPixelData(grid.value))
}

function emitSize() {
  emit('resize', { width: width.value, height: height.value })
}

function pushHistory() {
  const cells = grid.value.slice()
  const current = history.value[cursor.value]

  if (
    current &&
    current.width === width.value &&
    current.height === height.value &&
    current.cells.every((value, i) => value === cells[i])
  ) {
    return
  }

  history.value = history.value.slice(0, cursor.value + 1)
  history.value.push({ width: width.value, height: height.value, cells })

  // 古い履歴を捨てる
  if (history.value.length > props.maxHistory + 1) history.value.shift()
  cursor.value = history.value.length - 1
}

function restore(entry) {
  width.value = entry.width
  height.value = entry.height
  grid.value = entry.cells.slice()
  emitSize()
  emitValue()
  draw()
}

function undo() {
  if (!canUndo.value) return
  cursor.value -= 1
  restore(history.value[cursor.value])
}

function redo() {
  if (!canRedo.value) return
  cursor.value += 1
  restore(history.value[cursor.value])
}

function resetHistory() {
  history.value = [
    { width: width.value, height: height.value, cells: grid.value.slice() },
  ]
  cursor.value = 0
}

function indexFromEvent(event) {
  const el = canvas.value
  if (!el) return -1

  const rect = el.getBoundingClientRect()
  const x = Math.floor(((event.clientX - rect.left) / rect.width) * width.value)
  const y = Math.floor(((event.clientY - rect.top) / rect.height) * height.value)

  if (x < 0 || y < 0 || x >= width.value || y >= height.value) return -1
  return y * width.value + x
}

function paint(event) {
  const index = indexFromEvent(event)
  if (index < 0) return

  const erasing =
    tool.value === 'eraser' || event.button === 2 || event.buttons === 2 || event.altKey
  const value = erasing ? 0 : selected.value

  if (grid.value[index] === value) return

  grid.value[index] = value
  strokeDirty = true
  emitValue()
  draw()
}

function onPointerDown(event) {
  if (event.button === 2) event.preventDefault()
  drawing.value = true
  strokeDirty = false
  canvas.value?.setPointerCapture?.(event.pointerId)
  paint(event)
}

function onPointerMove(event) {
  if (drawing.value) paint(event)
}

function onPointerUp() {
  if (!drawing.value) return
  drawing.value = false
  if (strokeDirty) {
    pushHistory()
    strokeDirty = false
  }
}

function clearAll() {
  grid.value = new Array(dotCount.value).fill(0)
  emitValue()
  draw()
  pushHistory()
}

// 正方形 / Miiverse / クラシックの切り替え。
// 既存の絵は中央を基準にコピーし、はみ出た部分だけ切り取る。
function resizeTo(nextWidth, nextHeight) {
  if (
    !props.allowResize ||
    (nextWidth === width.value && nextHeight === height.value)
  ) {
    return
  }

  const next = new Array(nextWidth * nextHeight).fill(0)
  const offsetX = Math.floor((nextWidth - width.value) / 2)
  const offsetY = Math.floor((nextHeight - height.value) / 2)

  for (let y = 0; y < height.value; y++) {
    const ny = y + offsetY
    if (ny < 0 || ny >= nextHeight) continue

    for (let x = 0; x < width.value; x++) {
      const nx = x + offsetX
      if (nx < 0 || nx >= nextWidth) continue
      next[ny * nextWidth + nx] = grid.value[y * width.value + x]
    }
  }

  width.value = nextWidth
  height.value = nextHeight
  grid.value = next

  emitSize()
  emitValue()
  draw()
  pushHistory()
}

function onKeydown(event) {
  const target = event.target
  const tag = target?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || target?.isContentEditable) return
  if (!(event.metaKey || event.ctrlKey)) return

  const key = String(event.key).toLowerCase()
  if (key === 'z') {
    event.preventDefault()
    if (event.shiftKey) redo()
    else undo()
  } else if (key === 'y') {
    event.preventDefault()
    redo()
  }
}

watch(
  () => props.modelValue,
  (value) => {
    // 自分が emit した値をそのまま受け取った場合は何もしない
    if (value === toPixelData(grid.value)) return
    grid.value = parsePixelData(value, width.value, height.value)
    draw()
    resetHistory()
  },
)

watch(
  () => [props.canvasWidth, props.canvasHeight],
  ([nextWidth, nextHeight]) => {
    if (nextWidth === width.value && nextHeight === height.value) return
    resizeTo(nextWidth, nextHeight)
  },
)

onMounted(() => {
  draw()
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="pixel-editor">
    <div class="pixel-editor-head">
      <div
        v-if="allowResize"
        class="pixel-editor-sizes"
        role="group"
        aria-label="キャンバスの種類"
      >
        <button
          v-for="preset in CANVAS_PRESETS"
          :key="preset.id"
          type="button"
          class="pixel-size-btn"
          :class="{ active: activePreset === preset.id }"
          :aria-pressed="activePreset === preset.id ? 'true' : 'false'"
          @click="resizeTo(preset.width, preset.height)"
        >
          {{ preset.label }}
          <span class="pixel-size-dots">{{ preset.width }}×{{ preset.height }}</span>
        </button>
      </div>

      <span class="pixel-editor-count">
        {{ width }}×{{ height }} · {{ dotCount.toLocaleString('ja-JP') }} ドット
      </span>
    </div>

    <div class="pixel-editor-stage">
      <canvas
        ref="canvas"
        class="pixel-editor-canvas"
        :class="{ erasing: tool === 'eraser' }"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointerleave="onPointerUp"
        @pointercancel="onPointerUp"
        @contextmenu.prevent
      ></canvas>
    </div>

    <div class="pixel-editor-toolbar">
      <div class="pixel-editor-history">
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!canUndo"
          @click="undo"
        >
          ← もどる
        </button>
        <button
          type="button"
          class="btn btn-sm"
          :disabled="!canRedo"
          @click="redo"
        >
          すすむ →
        </button>
      </div>

      <div class="pixel-editor-tools">
        <button
          type="button"
          class="pixel-tool"
          :class="{ active: tool === 'pen' }"
          :aria-pressed="tool === 'pen' ? 'true' : 'false'"
          @click="tool = 'pen'"
        >
          ✎ ペン
        </button>
        <button
          type="button"
          class="pixel-tool"
          :class="{ active: tool === 'eraser' }"
          :aria-pressed="tool === 'eraser' ? 'true' : 'false'"
          @click="tool = 'eraser'"
        >
          ▢ 消しゴム
        </button>
        <button
          type="button"
          class="pixel-tool"
          :class="{ active: showGrid }"
          :aria-pressed="showGrid ? 'true' : 'false'"
          @click="showGrid = !showGrid"
        >
          # グリッド
        </button>
        <button type="button" class="pixel-tool danger" @click="clearAll">
          全消去
        </button>
      </div>
    </div>

    <div class="pixel-editor-colors">
      <span class="pixel-editor-label">
        COLOR
        <span class="pixel-current" :style="{ background: PALETTE[selected] }"></span>
      </span>

      <div class="pixel-editor-palette">
        <button
          v-for="(color, i) in PALETTE"
          :key="i"
          type="button"
          class="swatch"
          :class="{ active: selected === i && tool === 'pen' }"
          :style="{ background: color }"
          :title="color"
          :aria-label="'色 ' + color"
          @click="selected = i; tool = 'pen'"
        ></button>
      </div>
    </div>

    <p class="pixel-editor-hint">
      ドラッグで描画 · 右クリック / Alt で消しゴム · ⌘/Ctrl + Z でもどる
    </p>
  </div>
</template>
