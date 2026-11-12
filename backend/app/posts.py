"""floppy.io — 投稿の整形 / いいね"""

from __future__ import annotations

from typing import Any

from .db import fetch_all, fetch_one
from .utils.avatars import icon_url
from .utils.uploads import floppy_kind, upload_url

POST_COLUMNS = """p.id,
  p.user_id,
  p.reply_to_id,
  p.disk_id,
  u.username,
  u.display_name,
  u.avatar_path,
  u.icon_pixel,
  u.allow_replies AS author_allow_replies,
  p.text,
  p.pixel_data,
  p.pixel_width,
  p.pixel_height,
  p.image_path,
  p.image_mime,
  p.image_bytes,
  p.image_width,
  p.image_height,
  p.youtube_id,
  p.youtube_title,
  p.youtube_thumbnail,
  p.floppy_path,
  p.floppy_name,
  p.floppy_bytes,
  p.text_bytes,
  p.pixel_bytes,
  p.total_bytes,
  p.created_at"""


BOT_USERNAMES = {"hagumeta", "heisei_vipper", "adachi_rei", "nyanpuppu3", "nyanpuppu"}


def is_bot_username(username: str | None) -> bool:
    if not username:
        return False
    u = username.lower()
    return u in BOT_USERNAMES or u.startswith("nyanpuppu")


def with_media(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return row
    result = dict(row)
    result["is_bot"] = is_bot_username(str(result.get("username") or ""))
    result["image_url"] = upload_url(row.get("image_path"))
    result["floppy_url"] = upload_url(row.get("floppy_path"))
    result["floppy_kind"] = (
        floppy_kind(row["floppy_name"]) if row.get("floppy_name") else None
    )

    # 投稿者のアイコン URL。プロフィールの 32×32 アイコン → アップロード画像 →
    # 最新の正方形ドット絵、の順で /api/icon/<username>.svg が解決する。
    result["author_avatar_url"] = upload_url(row.get("avatar_path"))
    result["author_icon_url"] = icon_url(
        row["username"], row.get("icon_pixel"), row.get("avatar_path")
    )
    result.pop("avatar_path", None)
    result.pop("icon_pixel", None)

    # 返信の受け付け設定（投稿者本人の設定）。既定はオフ＝返信できない。
    result["replies_enabled"] = bool(int(row.get("author_allow_replies") or 0))
    result.pop("author_allow_replies", None)
    result["reply_to_id"] = (
        int(row["reply_to_id"]) if row.get("reply_to_id") else None
    )
    result["disk_id"] = int(row["disk_id"]) if row.get("disk_id") else None
    result["pixel_width"] = int(row.get("pixel_width") or 16)
    result["pixel_height"] = int(row.get("pixel_height") or 16)
    return result


def attach_likes(
    posts: list[dict[str, Any]], user: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    if not posts:
        return posts

    ids = [int(post["id"]) for post in posts]
    placeholders = ",".join(["%s"] * len(ids))

    counts = {
        int(row["post_id"]): int(row["c"])
        for row in fetch_all(
            f"""SELECT post_id, COUNT(*) AS c
                  FROM likes
                 WHERE post_id IN ({placeholders})
                 GROUP BY post_id""",
            tuple(ids),
        )
    }

    liked: set[int] = set()
    if user:
        liked = {
            int(row["post_id"])
            for row in fetch_all(
                f"""SELECT post_id FROM likes
                     WHERE user_id = %s AND post_id IN ({placeholders})""",
                (int(user["id"]), *ids),
            )
        }

    for post in posts:
        post_id = int(post["id"])
        post["like_count"] = counts.get(post_id, 0)
        post["liked"] = post_id in liked

    return posts


def attach_reply_counts(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """各投稿に、その投稿をルートとする返信の件数を付ける"""
    if not posts:
        return posts

    ids = [int(post["id"]) for post in posts]
    placeholders = ",".join(["%s"] * len(ids))

    counts = {
        int(row["reply_to_id"]): int(row["c"])
        for row in fetch_all(
            f"""SELECT reply_to_id, COUNT(*) AS c
                  FROM posts
                 WHERE reply_to_id IN ({placeholders})
                 GROUP BY reply_to_id""",
            tuple(ids),
        )
    }

    for post in posts:
        post["reply_count"] = counts.get(int(post["id"]), 0)

    return posts


def like_count(post_id: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM likes WHERE post_id = %s", (post_id,)
    )
    return int(row["c"]) if row else 0
