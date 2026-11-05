<script setup>
import Profile from '~/views/Profile.vue'

const route = useRoute()
const username = computed(() =>
  decodeURIComponent(String(route.params.username || '')),
)

useHead({
  title: computed(() => `@${username.value} — floppy.io`),
})
</script>

<template>
  <Profile :username="username" />
</template>
