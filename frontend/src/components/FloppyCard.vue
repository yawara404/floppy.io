<script setup>
import { ref, onMounted, watch } from 'vue'
import { drawPixel } from '../utils/pixel.js'

const props = defineProps({
  post: { type: Object, required: true },
})

const canvas = ref(null)

function render() {
  drawPixel(canvas.value, props.post?.pixel_data)
}

onMounted(render)
watch(() => props.post?.pixel_data, render)
</script>

<template>
  <div class="floppy-card">
    <canvas ref="canvas" class="pixel-preview" width="16" height="16"></canvas>
    <div>
      <div class="floppy-card-brand">floppy.io</div>
      <p v-if="post.text" class="floppy-card-text">{{ post.text }}</p>
      <div class="floppy-card-meta">
        @{{ post.username }} · {{ post.total_bytes.toLocaleString('ja-JP') }} bytes
      </div>
    </div>
  </div>
</template>
