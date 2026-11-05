// floppy.io — ドット絵ユーティリティ
// 16×16 グリッドの 1 マスを 1 桁の 16 進文字 (0-9A-F) で表し、
// 256 文字 (= 256 バイト) の文字列として扱う。

export const GRID_SIZE = 16

// 16 色パレット (インデックス 0〜15)。バックエンドの PIXEL_PALETTE と一致。
export const PALETTE = [
  '#ffffff', // 0 白
  '#c0c0c0', // 1 ライトグレー
  '#808080', // 2 グレー
  '#000000', // 3 黒
  '#ff0000', // 4 赤
  '#800000', // 5 暗赤
  '#ffff00', // 6 黄
  '#808000', // 7 オリーブ
  '#00ff00', // 8 緑
  '#008000', // 9 暗緑
  '#00ffff', // A シアン
  '#008080', // B ティール
  '#0000ff', // C 青
  '#000080', // D 紺
  '#ff00ff', // E マゼンタ
  '#800080', // F 紫
]

/** pixel_data 文字列 (256 文字) をインデックス配列 (256 要素) に変換 */
export function parsePixelData(str) {
  const out = new Array(GRID_SIZE * GRID_SIZE).fill(0)
  if (!str) return out
  const s = String(str).toUpperCase()
  for (let i = 0; i < out.length; i++) {
    const c = s.charCodeAt(i)
    if (c >= 48 && c <= 57) out[i] = c - 48 // '0'-'9'
    else if (c >= 65 && c <= 70) out[i] = c - 65 + 10 // 'A'-'F'
    else out[i] = 0
  }
  return out
}

/** インデックス配列 (256 要素) を pixel_data 文字列に変換 */
export function toPixelData(grid) {
  return grid.map((i) => i.toString(16).toUpperCase()).join('')
}

// プロフィールアイコン用のフロッピーディスク・ドット絵 (16×16 = 256 文字)
// 3=黒(本体) / 2=グレー(シャッター枠) / 1=ライトグレー(金属シャッター) / 0=白(ラベル)
export const FLOPPY_AVATAR = [
  '3333333333333333',
  '3222222222222223',
  '3211111111111123',
  '3211111111111123',
  '3211000000001123',
  '3211000000001123',
  '3211111111111123',
  '3222222222222223',
  '3222222222222223',
  '3000000000000003',
  '3000000000000003',
  '3000000000000003',
  '3000000000000003',
  '3000000000000003',
  '3000000000000003',
  '3333333333333333',
].join('')

/**
 * 指定した canvas に pixel_data を描画する。
 * canvas は 16×16 ピクセル (cell=1) で描画し、CSS 側で拡大表示する。
 */
export function drawPixel(canvas, data) {
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const grid = parsePixelData(data)
  canvas.width = GRID_SIZE
  canvas.height = GRID_SIZE
  for (let i = 0; i < grid.length; i++) {
    const x = i % GRID_SIZE
    const y = Math.floor(i / GRID_SIZE)
    ctx.fillStyle = PALETTE[grid[i]]
    ctx.fillRect(x, y, 1, 1)
  }
}
