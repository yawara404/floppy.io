<script setup>
import Home from '~/views/Home.vue'

useHead({ title: 'フォロー中 — floppy.io' })
</script>

<template>
  <Home feed="following" />
</template>
