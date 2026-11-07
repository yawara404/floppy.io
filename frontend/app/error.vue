<script setup>
const props = defineProps({ error: Object })
const missing = computed(() => props.error?.statusCode === 404)
useHead({ title: 'ページを表示できません — floppy.io' })
</script>

<template>
  <main class="error-page">
    <section class="panel error-panel">
      <p class="section-kicker">FLOPPY.IO / {{ error?.statusCode || 'ERROR' }}</p>
      <span class="error-disk" aria-hidden="true">[F]</span>
      <h1 class="section-title">{{ missing ? 'ディスクが見つかりません' : 'ページを表示できませんでした' }}</h1>
      <p class="panel-note">{{ missing ? 'URL が正しいか確認するか、ホームから探してみてください。' : 'しばらく待ってから、もう一度お試しください。' }}</p>
      <button class="btn btn-primary" type="button" @click="clearError({ redirect: '/' })">ホームへ戻る</button>
    </section>
  </main>
</template>
