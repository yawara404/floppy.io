"""floppy.io — ドット絵 (16×16 / 256 バイト、アイコンは 32×32 / 1024 バイト)"""

from __future__ import annotations

import re

GRID_SIZE = 16

# プロフィールアイコン用の 32×32 グリッド
ICON_GRID_SIZE = 32

# 投稿で選べるドット絵キャンバス (幅, 高さ)
#   16×16 … クラシック（旧データとの互換）
#   32×32 … 正方形
#   32×24 … Miiverse 風（4:3）
PIXEL_CANVASES = ((16, 16), (32, 32), (32, 24))
DEFAULT_CANVAS = (16, 16)

PIXEL_PALETTE = [
    "#ffffff",
    "#c0c0c0",
    "#808080",
    "#000000",
    "#ff0000",
    "#800000",
    "#ffff00",
    "#808000",
    "#00ff00",
    "#008000",
    "#00ffff",
    "#008080",
    "#0000ff",
    "#000080",
    "#ff00ff",
    "#800080",
]

FLOPPY_AVATAR_PIXEL = "".join(
    [
        "3333333333333333",
        "3222222222222223",
        "3211111111111123",
        "3211111111111123",
        "3211000000001123",
        "3211000000001123",
        "3211111111111123",
        "3222222222222223",
        "3222222222222223",
        "3000000000000003",
        "3000000000000003",
        "3000000000000003",
        "3000000000000003",
        "3000000000000003",
        "3000000000000003",
        "3333333333333333",
    ]
)

_ICON_PIXEL_RE = re.compile(r"^[0-9A-Fa-f]{1024}$")
_HEX_RE = re.compile(r"^[0-9A-Fa-f]+$")
_ART_RE = re.compile(r"[1-9A-Fa-f]")


def normalize_canvas_size(width: object, height: object) -> tuple[int, int]:
    """キャンバスサイズを検証して (幅, 高さ) を返す (不正なら 16×16)"""
    try:
        w = int(width)
        h = int(height)
    except (TypeError, ValueError):
        return DEFAULT_CANVAS
    return (w, h) if (w, h) in PIXEL_CANVASES else DEFAULT_CANVAS


def normalize_pixel(
    value: str | None, width: object = 16, height: object = 16
) -> str:
    """指定キャンバスの 16 進文字列に正規化する (不正なら全透明)"""
    w, h = normalize_canvas_size(width, height)
    size = w * h
    if (
        isinstance(value, str)
        and len(value) == size
        and _HEX_RE.match(value)
    ):
        return value.upper()
    return "0" * size


def normalize_icon_pixel(value: str | None) -> str:
    """プロフィールアイコン用の 1024 文字 (32×32) に正規化する。

    空 / 全透明 / 不正な値は「未設定」として空文字を返す。
    """
    if isinstance(value, str) and _ICON_PIXEL_RE.match(value):
        pixel = value.upper()
        return "" if pixel.strip("0") == "" else pixel
    return ""


def is_blank_pixel(pixel: str) -> bool:
    return pixel.strip("0") == ""


def has_pixel_art(pixel: str | None) -> bool:
    return bool(_ART_RE.search(str(pixel or "")))


def pixel_svg(
    pixel: str, width: object = 16, height: object = 16, cell: int = 8
) -> str:
    """自己完結型 SVG を生成する (埋め込みプレビュー用)

    16×16 / 32×32 / 32×24 のキャンバスに対応する。
    未描画のときは 16×16 のフロッピーアイコンを表示する。
    """
    w, h = normalize_canvas_size(width, height)

    if has_pixel_art(pixel) and isinstance(pixel, str) and len(pixel) == w * h:
        data = pixel.upper()
    else:
        w = h = GRID_SIZE
        data = FLOPPY_AVATAR_PIXEL

    size_w = w * cell
    size_h = h * cell

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size_w}" height="{size_h}" '
        f'shape-rendering="crispEdges" viewBox="0 0 {size_w} {size_h}">'
    ]

    for index in range(w * h):
        color = PIXEL_PALETTE[int(data[index], 16)]
        x = (index % w) * cell
        y = (index // w) * cell
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color}"/>'
        )

    parts.append("</svg>")
    return "".join(parts)
