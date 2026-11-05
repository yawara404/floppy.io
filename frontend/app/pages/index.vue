<script setup>
import Home from '~/views/Home.vue'

useHead({
  title: 'floppy.io — 1.44MB しか使えない静寂のレトロ SNS',
})
</script>

<template>
  <Home feed="timeline" />
</template>
