"""floppy.io — 画像判定 (PHP の getimagesize 相当)"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import DISK_LIMIT_BYTES


@dataclass(frozen=True)
class ImageInfo:
    mime: str
    ext: str
    width: int
    height: int


def _png(data: bytes) -> ImageInfo | None:
    if len(data) < 24 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    return ImageInfo(
        "image/png",
        "png",
        int.from_bytes(data[16:20], "big"),
        int.from_bytes(data[20:24], "big"),
    )


def _gif(data: bytes) -> ImageInfo | None:
    if len(data) < 10 or data[:6] not in (b"GIF87a", b"GIF89a"):
        return None
    return ImageInfo(
        "image/gif",
        "gif",
        int.from_bytes(data[6:8], "little"),
        int.from_bytes(data[8:10], "little"),
    )


def _jpeg(data: bytes) -> ImageInfo | None:
    if len(data) < 4 or data[0:2] != b"\xff\xd8":
        return None

    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue

        marker = data[offset + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            offset += 2
            continue

        size = int.from_bytes(data[offset + 2 : offset + 4], "big")
        if size < 2:
            break

        is_sof = 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC)

        if is_sof:
            return ImageInfo(
                "image/jpeg",
                "jpg",
                int.from_bytes(data[offset + 7 : offset + 9], "big"),
                int.from_bytes(data[offset + 5 : offset + 7], "big"),
            )

        offset += 2 + size

    return None


def _webp(data: bytes) -> ImageInfo | None:
    if len(data) < 30 or data[0:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None

    chunk = data[12:16]

    if chunk == b"VP8 ":
        return ImageInfo(
            "image/webp",
            "webp",
            int.from_bytes(data[26:28], "little") & 0x3FFF,
            int.from_bytes(data[28:30], "little") & 0x3FFF,
        )

    if chunk == b"VP8L":
        width = 1 + (((data[22] & 0x3F) << 8) | data[21])
        height = 1 + (
            ((data[24] & 0x0F) << 10)
            | (data[23] << 2)
            | ((data[22] & 0xC0) >> 6)
        )
        return ImageInfo("image/webp", "webp", width, height)

    if chunk == b"VP8X":
        return ImageInfo(
            "image/webp",
            "webp",
            1 + int.from_bytes(data[24:27], "little"),
            1 + int.from_bytes(data[27:30], "little"),
        )

    return None


def image_info(data: bytes) -> ImageInfo | None:
    if not data:
        return None
    return _png(data) or _jpeg(data) or _gif(data) or _webp(data)


def validate_image_data(data: bytes) -> tuple[ImageInfo | None, str | None]:
    """(info, error) を返す。error が None なら有効。"""
    if not data:
        return None, "画像が選択されていません。"

    if len(data) > DISK_LIMIT_BYTES:
        return None, "画像が大きすぎます（1 枚で 1.44MB まで）。"

    info = image_info(data)
    if info is None:
        return None, "対応していない画像形式です（JPEG / PNG / GIF / WebP）。"

    return info, None
