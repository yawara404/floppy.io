"""floppy.io — ユーザーアイコン URL の共通化

投稿カード / 検索サジェスト / プロフィールで同じ URL を組み立てる。
`/api/icon/<username>.svg` はアイコン未設定でも初期アイコンを返す。
"""

from __future__ import annotations

import hashlib
from urllib.parse import quote

from .pixels import normalize_icon_pixel
from .uploads import public_base_path


def icon_version(icon_pixel: object, avatar_path: object = "") -> str:
    """アイコン内容の短いハッシュ。空なら ''（バージョン無し）。"""
    icon = normalize_icon_pixel(icon_pixel)
    avatar = str(avatar_path or "")
    if not icon and not avatar:
        return ""
    return hashlib.sha1(f"{icon}|{avatar}".encode("utf-8")).hexdigest()[:8]


def icon_url(
    username: object,
    icon_pixel: object = "",
    avatar_path: object = "",
) -> str:
    """投稿カード用アバターの URL。内容が変わると ?v= も変わる。"""
    version = icon_version(icon_pixel, avatar_path)
    url = f"{public_base_path()}api/icon/{quote(str(username))}.svg"
    return f"{url}?v={version}" if version else url
