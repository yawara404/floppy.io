<script setup>
import { computed } from 'vue'

const props = defineProps({
  used: { type: Number, default: 0 },
  limit: { type: Number, default: 1474560 },
  label: { type: String, default: '💾 DISK (C:)' },
})

// 残量は表示せず、使用量・上限・使用率という統計だけを見せる
const ratio = computed(() => (props.limit > 0 ? props.used / props.limit : 0))
const barPercent = computed(() => Math.min(100, ratio.value * 100))
const percentLabel = computed(() => (ratio.value * 100).toFixed(2))
const over = computed(() => props.used > props.limit)

function fmt(n) {
  return n.toLocaleString('ja-JP')
}
</script>

<template>
  <div class="gauge">
    <div class="gauge-label">
      <span>{{ label }}</span>
      <span>{{ fmt(used) }} / {{ fmt(limit) }} bytes</span>
    </div>

    <div class="gauge-track">
      <div
        class="gauge-fill"
        :class="{ warn: barPercent > 90, over }"
        :style="{ width: barPercent + '%' }"
      ></div>
    </div>

    <div class="gauge-stats" :class="{ 'gauge-over': over }">
      <span>使用率 {{ percentLabel }}%</span>
      <span v-if="over">
        ⚠ 1投稿あたりの上限を {{ fmt(used - limit) }} bytes 超えています
      </span>
    </div>
  </div>
</template>
