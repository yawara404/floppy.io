"""floppy.io — ドット絵 (16×16 / 256 バイト)"""

from __future__ import annotations

import re

GRID_SIZE = 16

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

_PIXEL_RE = re.compile(r"^[0-9A-Fa-f]{256}$")
_ART_RE = re.compile(r"[1-9A-Fa-f]")


def normalize_pixel(value: str | None) -> str:
    """256 文字の 16 進文字列に正規化する (不正なら全透明)"""
    if isinstance(value, str) and _PIXEL_RE.match(value):
        return value.upper()
    return "0" * 256


def is_blank_pixel(pixel: str) -> bool:
    return pixel.strip("0") == ""


def has_pixel_art(pixel: str | None) -> bool:
    return bool(_ART_RE.search(str(pixel or "")))


def pixel_svg(pixel: str, cell: int = 8) -> str:
    """自己完結型 SVG を生成する (埋め込みプレビュー用)"""
    data = pixel if has_pixel_art(pixel) else FLOPPY_AVATAR_PIXEL
    size = GRID_SIZE * cell

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
        f'shape-rendering="crispEdges" viewBox="0 0 {size} {size}">'
    ]

    for index in range(GRID_SIZE * GRID_SIZE):
        color = PIXEL_PALETTE[int(data[index], 16)]
        x = (index % GRID_SIZE) * cell
        y = (index // GRID_SIZE) * cell
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{color}"/>'
        )

    parts.append("</svg>")
    return "".join(parts)
