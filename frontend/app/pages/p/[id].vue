<script setup>
import PostView from '~/views/PostView.vue'

const route = useRoute()
const id = computed(() => String(route.params.id || ''))

useHead({
  title: computed(() => `共有されたフロッピー #${id.value} — floppy.io`),
})
</script>

<template>
  <PostView :id="id" />
</template>
