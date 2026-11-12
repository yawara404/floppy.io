// floppy.io — 投稿のアバター canvas
// 「投稿のドット絵があればそれを、無ければ初期アイコンを描く」を
// PostItem / PostDetail / ShareDialog で共通化する。

import { ref, watch, onMounted, nextTick } from 'vue'
import { drawDefaultAvatar, drawPixelContained } from '~/utils/pixel'
import { hasPixelArt } from '~/utils/post'

/**
 * @param {() => object | null} getPost
 * @returns {{ canvas: import('vue').Ref<HTMLCanvasElement|null>, draw: () => void }}
 */
export function useAvatarCanvas(getPost) {
  const canvas = ref(null)

  function draw() {
    const post = getPost()
    if (!canvas.value || !post) return
    if (hasPixelArt(post)) {
      drawPixelContained(
        canvas.value,
        post.pixel_data,
        post.pixel_width,
        post.pixel_height,
      )
    } else {
      drawDefaultAvatar(canvas.value)
    }
  }

  async function redraw() {
    await nextTick()
    draw()
  }

  onMounted(draw)
  watch(
    () => {
      const post = getPost() || {}
      return [post.id, post.pixel_data, post.pixel_width, post.pixel_height]
    },
    redraw,
  )

  return { canvas, draw }
}
