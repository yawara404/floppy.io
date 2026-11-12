// floppy.io — 投稿データの小さな判定ヘルパー
// PostItem / PostDetail / ShareDialog / FloppyCard で同じ判定を使う。

/** ドット絵が描かれているか（全透明は false） */
export function hasPixelArt(post) {
  return /[1-9A-Fa-f]/.test(String(post?.pixel_data || ''))
}

/** 投稿の種類ラベル（計器表示用） */
export function postKindOf(post) {
  if (!post) return 'TEXT'
  if (post.youtube_id) return 'YOUTUBE'
  if (post.image_url) return 'IMAGE'
  if (post.floppy_url) return post.floppy_kind === 'audio' ? 'AUDIO' : 'FILE'
  if (hasPixelArt(post)) return 'PIXEL'
  return 'TEXT'
}

/** YouTube サムネイル URL（保存済みが無ければ hqdefault） */
export function youtubeThumbnail(post) {
  if (!post?.youtube_id) return ''
  return post.youtube_thumbnail || `https://i.ytimg.com/vi/${post.youtube_id}/hqdefault.jpg`
}
