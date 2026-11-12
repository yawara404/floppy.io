<script setup>
import Profile from '~/views/Profile.vue'

const route = useRoute()
const username = computed(() => String(route.params.username || ''))
useHead({ title: computed(() => `@${username.value} のフォロワー — floppy.io`) })
</script>

<template>
  <Profile :username="username" connections-kind="followers" />
</template>
