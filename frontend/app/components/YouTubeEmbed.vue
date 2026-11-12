<script setup>
// floppy.io — YouTube 埋め込み（PostItem / PostDetail で共用）
// クリックするまで iframe を読み込まない。IP アドレスからの閲覧時は案内を出す。
import { ref, computed } from 'vue'
import { isIpHost, localhostUrl } from '~/utils/env'

const props = defineProps({
  videoId: { type: String, required: true },
  title: { type: String, default: '' },
  thumbnail: { type: String, default: '' },
})

const playing = ref(false)

const thumb = computed(
  () => props.thumbnail || `https://i.ytimg.com/vi/${props.videoId}/hqdefault.jpg`,
)

const watchUrl = computed(
  () => `https://www.youtube.com/watch?v=${props.videoId}`,
)

const embedUrl = computed(() => {
  const params = new URLSearchParams({
    autoplay: '1',
    rel: '0',
    // iOS Safari で全画面に飛ばさずインライン再生させる
    playsinline: '1',
  })

  // Referer が無いと YouTube がエラー 153 を返すため、埋め込み元を明示する
  if (typeof window !== 'undefined' && window.location.origin) {
    params.set('origin', window.location.origin)
  }

  return `https://www.youtube.com/embed/${props.videoId}?${params}`
})

const ipHost = computed(() => isIpHost())
const localhost = computed(() => localhostUrl())
</script>

<template>
  <div class="youtube-embed">
    <div class="youtube-frame">
      <iframe
        v-if="playing"
        :src="embedUrl"
        title="YouTube 動画プレーヤー"
        referrerpolicy="strict-origin-when-cross-origin"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen
      ></iframe>
      <button
        v-else
        type="button"
        class="youtube-thumb"
        aria-label="YouTube を再生"
        @click="playing = true"
      >
        <img :src="thumb" alt="" loading="lazy" />
        <span class="youtube-play" aria-hidden="true">▶</span>
      </button>
    </div>

    <div class="youtube-meta">
      <span class="youtube-title">▶ {{ title || 'YouTube 動画' }}</span>
      <a class="youtube-open" :href="watchUrl" target="_blank" rel="noopener noreferrer">
        YouTube で見る ↗
      </a>
    </div>

    <p v-if="ipHost" class="youtube-hint">
      このページは IP アドレスで開かれているため、YouTube を埋め込み再生できません。
      <a :href="localhost">localhost で開き直す</a>
    </p>
  </div>
</template>
