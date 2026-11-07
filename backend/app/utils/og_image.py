"""floppy.io — 投稿別 OGP 画像 (ドット絵から PNG を生成)

Pillow などの画像ライブラリを増やさず、標準ライブラリ (zlib / struct) だけで
1200×630 の PNG を組み立てる。テキストは描かず、投稿のドット絵を
サイトの紙色・ミントのヘッダー・ドット枠で額装する。
X (Twitter) の summary_large_image 用。
"""

from __future__ import annotations

import binascii
import struct
import zlib

from .pixels import (
    FLOPPY_AVATAR_PIXEL,
    GRID_SIZE,
    PIXEL_PALETTE,
    has_pixel_art,
    normalize_canvas_size,
)

CARD_WIDTH = 1200
CARD_HEIGHT = 630

PAPER = (255, 253, 247)
MINT = (207, 233, 216)
HEADER_INK = (23, 77, 53)
INK = (35, 38, 43)
SHADOW = (201, 195, 177)
WHITE = (255, 255, 255)

# ドット絵を収める領域 (ヘッダーの下)
ART_AREA = (180, 110, 1020, 570)
FRAME_PADDING = 16
HEADER_HEIGHT = 72


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


PALETTE_RGB = [_rgb(color) for color in PIXEL_PALETTE]


def _fill_rect(
    canvas: bytearray,
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    color: tuple[int, int, int],
) -> None:
    x0 = max(0, min(CARD_WIDTH, x0))
    x1 = max(0, min(CARD_WIDTH, x1))
    y0 = max(0, min(CARD_HEIGHT, y0))
    y1 = max(0, min(CARD_HEIGHT, y1))
    if x0 >= x1 or y0 >= y1:
        return

    row = bytes(color) * (x1 - x0)
    for y in range(y0, y1):
        start = (y * CARD_WIDTH + x0) * 3
        canvas[start : start + len(row)] = row


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)
    )


def _encode_png(width: int, height: int, canvas: bytearray) -> bytes:
    raw = bytearray()
    stride = width * 3

    for y in range(height):
        raw.append(0)  # filter type: none
        raw.extend(canvas[y * stride : (y + 1) * stride])

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)

    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + _chunk(b"IEND", b"")
    )


def render_pixel_card_png(
    pixel: object,
    width: object = GRID_SIZE,
    height: object = GRID_SIZE,
) -> bytes:
    """ドット絵をサイトのカード風に額装した 1200×630 PNG"""
    w, h = normalize_canvas_size(width, height)
    data = str(pixel or "").upper()

    if not has_pixel_art(data) or len(data) != w * h:
        w = h = GRID_SIZE
        data = FLOPPY_AVATAR_PIXEL

    canvas = bytearray(PAPER * (CARD_WIDTH * CARD_HEIGHT))

    # ミントのヘッダー
    _fill_rect(canvas, 0, 0, CARD_WIDTH, HEADER_HEIGHT, MINT)
    _fill_rect(canvas, 0, HEADER_HEIGHT - 4, CARD_WIDTH, HEADER_HEIGHT, HEADER_INK)

    # ドット絵の額縁サイズ
    area_x0, area_y0, area_x1, area_y1 = ART_AREA
    area_w = area_x1 - area_x0
    area_h = area_y1 - area_y0
    inner_w = area_w - FRAME_PADDING * 2
    inner_h = area_h - FRAME_PADDING * 2

    scale = max(1, min(inner_w // w, inner_h // h))
    art_w = w * scale
    art_h = h * scale
    frame_w = art_w + FRAME_PADDING * 2
    frame_h = art_h + FRAME_PADDING * 2

    frame_x = (CARD_WIDTH - frame_w) // 2
    frame_y = area_y0 + (area_h - frame_h) // 2

    # ハードシャドウ + 白い額 + ドット枠
    _fill_rect(canvas, frame_x + 8, frame_y + 8, frame_x + frame_w + 8, frame_y + frame_h + 8, SHADOW)
    _fill_rect(canvas, frame_x, frame_y, frame_x + frame_w, frame_y + frame_h, INK)
    _fill_rect(
        canvas,
        frame_x + 4,
        frame_y + 4,
        frame_x + frame_w - 4,
        frame_y + frame_h - 4,
        WHITE,
    )

    art_x = frame_x + FRAME_PADDING
    art_y = frame_y + FRAME_PADDING

    for index in range(w * h):
        color = PALETTE_RGB[int(data[index], 16)]
        px = art_x + (index % w) * scale
        py = art_y + (index // w) * scale
        _fill_rect(canvas, px, py, px + scale, py + scale, color)

    return _encode_png(CARD_WIDTH, CARD_HEIGHT, canvas)
