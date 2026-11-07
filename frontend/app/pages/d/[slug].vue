<script setup>
import Disk from '~/views/Disk.vue'

const route = useRoute()
const slug = computed(() => String(route.params.slug || ''))

useHead({
  title: computed(() => `/d/${slug.value} — ディスク — floppy.io`),
})
</script>

<template>
  <Disk :slug="slug" />
</template>
