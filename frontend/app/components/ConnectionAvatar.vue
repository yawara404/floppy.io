<script setup>
import { ref, watch, onMounted } from 'vue'
import { drawAvatar } from '~/utils/pixel'
import { resolveMediaUrl } from '~/utils/api'

const props = defineProps({ user: { type: Object, required: true } })
const canvas = ref(null)
const failed = ref(false)
function render() { if (canvas.value) drawAvatar(canvas.value, props.user.icon_pixel) }
onMounted(render)
watch(() => [props.user.icon_pixel, failed.value], render, { flush: 'post' })
</script>

<template>
  <span class="connection-avatar" aria-hidden="true">
    <img v-if="!user.icon_pixel && user.avatar_url && !failed" :src="resolveMediaUrl(user.avatar_url)" alt="" loading="lazy" @error="failed = true" />
    <canvas v-else ref="canvas" width="32" height="32"></canvas>
  </span>
</template>
