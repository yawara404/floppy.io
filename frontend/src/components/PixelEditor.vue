<script setup>
import { ref, watch, onMounted } from 'vue'
import { PALETTE, GRID_SIZE, parsePixelData, toPixelData } from '../utils/pixel.js'

const props = defineProps({
  modelValue: { type: String, default: () => '0'.repeat(GRID_SIZE * GRID_SIZE) },
})

const emit = defineEmits(['update:modelValue'])

const canvas = ref(null)
const selected = ref(3) // デフォルトは黒
const drawing = ref(false)

const grid = ref(parsePixelData(props.modelValue))

watch(
  () => props.modelValue,
  (v) => {
    grid.value = parsePixelData(v)
    draw()
  }
)

function draw() {
  const el = canvas.value
  const ctx = el?.getContext('2d')
  if (!ctx) return
  const cell = el.width / GRID_SIZE
  for (let i = 0; i < grid.value.length; i++) {
    const x = (i % GRID_SIZE) * cell
    const y = Math.floor(i / GRID_SIZE) * cell
    ctx.fillStyle = PALETTE[grid.value[i]]
    ctx.fillRect(x, y, cell, cell)
  }
}

function indexFromEvent(e) {
  const rect = canvas.value.getBoundingClientRect()
  const x = Math.floor(((e.clientX - rect.left) / rect.width) * GRID_SIZE)
  const y = Math.floor(((e.clientY - rect.top) / rect.height) * GRID_SIZE)
  if (x < 0 || y < 0 || x >= GRID_SIZE || y >= GRID_SIZE) return -1
  return y * GRID_SIZE + x
}

function paint(e) {
  const i = indexFromEvent(e)
  if (i < 0) return
  if (grid.value[i] === selected.value) return
  grid.value[i] = selected.value
  emit('update:modelValue', toPixelData(grid.value))
  draw()
}

function onPointerDown(e) {
  drawing.value = true
  canvas.value?.setPointerCapture?.(e.pointerId)
  paint(e)
}

function onPointerMove(e) {
  if (drawing.value) paint(e)
}

function stopDrawing() {
  drawing.value = false
}

function clearAll() {
  grid.value = grid.value.map(() => 0)
  emit('update:modelValue', toPixelData(grid.value))
  draw()
}

onMounted(draw)
</script>

<template>
  <div class="pixel-editor">
    <canvas
      ref="canvas"
      class="pixel-editor-canvas"
      :width="GRID_SIZE * 16"
      :height="GRID_SIZE * 16"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="stopDrawing"
      @pointerleave="stopDrawing"
      @pointercancel="stopDrawing"
    ></canvas>

    <div class="pixel-editor-palette">
      <button
        v-for="(color, i) in PALETTE"
        :key="i"
        type="button"
        class="swatch"
        :class="{ active: selected === i }"
        :style="{ background: color }"
        :title="color"
        @click="selected = i"
      ></button>
    </div>

    <div class="pixel-editor-tools">
      <button type="button" class="btn btn-sm" @click="clearAll">全消去</button>
      <span class="pixel-editor-hint">ドラッグで描画 · 256 バイトで保存されます</span>
    </div>
  </div>
</template>
