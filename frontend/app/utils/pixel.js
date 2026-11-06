// floppy.io — ドット絵ユーティリティ
// 1 マス = 1 桁の 16 進文字 (0-9A-F) で表し、幅 × 高さ の文字列として扱う。
//   16×16 = 256 文字（クラシック）
//   32×32 = 1024 文字（正方形）
//   32×24 = 768 文字（Miiverse 風）
// プロフィールアイコンは 32×32 (1024 文字)。

export const GRID_SIZE = 16
export const ICON_GRID_SIZE = 32

// 投稿のドット絵で選べるキャンバス
export const CANVAS_PRESETS = [
  { id: 'square', label: '正方形', width: 32, height: 32 },
  { id: 'miiverse', label: 'Miiverse', width: 32, height: 24 },
  { id: 'classic', label: 'クラシック', width: 16, height: 16 },
]

/** キャンバスサイズを決定する（指定が無ければ文字数から推定） */
export function pixelSize(data, width, height) {
  const w = Number(width)
  const h = Number(height)
  if (w > 0 && h > 0) return { width: w, height: h }

  const len = String(data || '').length
  if (len === 1024) return { width: 32, height: 32 }
  if (len === 768) return { width: 32, height: 24 }
  return { width: GRID_SIZE, height: GRID_SIZE }
}

/** 全透明（＝未描画）かどうか */
export function pixelIsBlank(data) {
  return !/[1-9A-Fa-f]/.test(String(data || ''))
}

/** 指定サイズの全透明ドット絵を作る */
export function blankPixel(width = GRID_SIZE, height = GRID_SIZE) {
  return '0'.repeat(width * height)
}

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

/** pixel_data 文字列をインデックス配列に変換 */
export function parsePixelData(str, width = GRID_SIZE, height = GRID_SIZE) {
  const w = Number(width) || GRID_SIZE
  const h = Number(height) || GRID_SIZE
  const out = new Array(w * h).fill(0)
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

/** インデックス配列を pixel_data 文字列に変換 */
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
 * 幅・高さを指定しない場合は文字数から自動判定する。
 * canvas は 1 マス = 1 ピクセルで描画し、CSS 側で拡大表示する。
 */
export function drawPixel(canvas, data, width, height) {
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const size = pixelSize(data, width, height)
  const grid = parsePixelData(data, size.width, size.height)
  canvas.width = size.width
  canvas.height = size.height
  for (let i = 0; i < grid.length; i++) {
    const x = i % size.width
    const y = Math.floor(i / size.width)
    ctx.fillStyle = PALETTE[grid[i]]
    ctx.fillRect(x, y, 1, 1)
  }
}

/**
 * 正方形の枠（アイコンなど）に、縦横比を保ったまま描画する。
 * 32×24 のような横長キャンバスは上下に白い余白が入る。
 */
export function drawPixelContained(canvas, data, width, height) {
  if (!canvas) return

  const size = pixelSize(data, width, height)
  if (size.width === size.height) {
    drawPixel(canvas, data, size.width, size.height)
    return
  }

  const ctx = canvas.getContext('2d')
  const grid = parsePixelData(data, size.width, size.height)
  const side = Math.max(size.width, size.height)
  const offsetX = Math.floor((side - size.width) / 2)
  const offsetY = Math.floor((side - size.height) / 2)

  canvas.width = side
  canvas.height = side

  ctx.fillStyle = PALETTE[0]
  ctx.fillRect(0, 0, side, side)

  for (let i = 0; i < grid.length; i++) {
    ctx.fillStyle = PALETTE[grid[i]]
    ctx.fillRect(
      offsetX + (i % size.width),
      offsetY + Math.floor(i / size.width),
      1,
      1,
    )
  }
}
