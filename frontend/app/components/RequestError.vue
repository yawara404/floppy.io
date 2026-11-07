<script setup>
defineProps({ message: { type: String, required: true } })
defineEmits(['retry'])
</script>

<template>
  <div class="request-error" role="alert">
    <div>
      <strong>読み込めませんでした</strong>
      <p>{{ message }}</p>
    </div>
    <button type="button" class="btn btn-sm" @click="$emit('retry')">再試行</button>
  </div>
</template>
