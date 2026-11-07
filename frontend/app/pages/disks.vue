<script setup>
import Disks from '~/views/Disks.vue'

useHead({
  title: 'ディスク — floppy.io',
  meta: [
    {
      name: 'description',
      content:
        '1 枚のフロッピーが 1 つのコミュニティ。レトロPC・ドット絵・8bit音楽などのディスクを開いて書き込めます。',
    },
  ],
})
</script>

<template>
  <Disks />
</template>
