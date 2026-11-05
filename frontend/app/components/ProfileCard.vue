<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { drawPixel, FLOPPY_AVATAR } from '~/utils/pixel'

const props = defineProps({
  user: { type: Object, required: true },
})

const canvas = ref(null)

const DISK_LIMIT = 1474560

// 最大の投稿が 1 枚のフロッピーに対してどれくらいか
const capacityPercent = computed(() => {
  const bytes = Number(props.user?.largest_post_bytes || 0)
  return Math.max(1, Math.min(100, (bytes / DISK_LIMIT) * 100))
})

// 画像が設定されていればそれを、無ければ最新投稿のドット絵を描く
function render() {
  if (!canvas.value) return
  drawPixel(canvas.value, props.user?.avatar_pixel || FLOPPY_AVATAR)
}

function fmt(n) {
  return (n || 0).toLocaleString('ja-JP')
}

onMounted(render)
watch(() => [props.user?.avatar_url, props.user?.avatar_pixel], render, {
  flush: 'post',
})
</script>

<template>
  <div class="profile-card">
    <div class="profile-card-top">
      <span>CURRENT USER</span>
      <span class="profile-online"><span class="pulse-dot"></span>ONLINE</span>
    </div>

    <a :href="'#/u/' + user.username" class="profile-avatar-link">
      <img
        v-if="user.avatar_url"
        :src="user.avatar_url"
        class="profile-avatar"
        :alt="user.display_name"
      />
      <canvas
        v-else
        ref="canvas"
        class="profile-avatar"
        width="16"
        height="16"
      ></canvas>
    </a>

    <div class="profile-meta">
      <div class="profile-name">
        <a :href="'#/u/' + user.username">{{ user.display_name }}</a>
      </div>
      <div class="profile-handle">@{{ user.username }}</div>
    </div>

    <p v-if="user.bio" class="profile-bio">{{ user.bio }}</p>

    <div class="profile-stats">
      <div class="stat">
        <b>{{ fmt(user.post_count) }}</b>
        <span>投稿</span>
      </div>
      <div class="stat">
        <b>{{ fmt(user.following_count) }}</b>
        <span>フォロー</span>
      </div>
      <div class="stat">
        <b>{{ fmt(user.follower_count) }}</b>
        <span>フォロワー</span>
      </div>
      <div class="stat">
        <b>{{ fmt(user.total_bytes) }}</b>
        <span>合計バイト</span>
      </div>
      <div class="stat">
        <b>{{ fmt(user.largest_post_bytes) }}</b>
        <span>最大</span>
      </div>
    </div>

    <div class="profile-disk">
      <div class="profile-disk-head">
        <span>LARGEST WRITE</span>
        <b>{{ fmt(user.largest_post_bytes) }} B / 1.44 MB</b>
      </div>
      <div class="mini-track">
        <span :style="{ width: capacityPercent + '%' }"></span>
      </div>
    </div>
  </div>
</template>
