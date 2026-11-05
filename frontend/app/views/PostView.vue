<script setup>
import { ref, onMounted, watch } from 'vue'
import FloppyCard from '../components/FloppyCard.vue'
import { apiGet } from '~/utils/api'

const props = defineProps({
  id: { type: [String, Number], required: true },
})

const post = ref(null)
const error = ref('')
const loading = ref(false)

async function load() {
  error.value = ''
  post.value = null
  loading.value = true

  try {
    const data = await apiGet(`/preview?id=${encodeURIComponent(props.id)}`)
    // プレビュー API は author / author_name を返すため、
    // FloppyCard が期待する username / display_name へ寄せる
    post.value = {
      ...data,
      username: data.author || '',
      display_name: data.author_name || data.author || '',
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

onMounted(load)
watch(() => props.id, load)
</script>

<template>
  <div>
    <p v-if="loading" class="panel-note">読み込み中…</p>
    <p v-else-if="error" class="msg msg-error">{{ error }}</p>

    <section v-else-if="post" class="panel shared-post">
      <p class="section-kicker">SHARED FLOPPY / #{{ post.id }}</p>
      <h2 class="panel-title">共有された投稿</h2>

      <div class="shared-post-stage">
        <FloppyCard :post="post" />
      </div>

      <p class="panel-note">
        <a :href="'#/u/' + post.username">@{{ post.username }}</a> の投稿です。
      </p>
      <div class="panel-actions">
        <a class="btn" href="#/">タイムラインへ戻る</a>
        <a class="btn btn-primary" :href="'#/u/' + post.username">
          @{{ post.username }} を見る
        </a>
      </div>
    </section>
  </div>
</template>
