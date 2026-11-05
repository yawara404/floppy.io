"""floppy.io — 投稿の整形 / いいね"""

from __future__ import annotations

from typing import Any

from .db import fetch_all, fetch_one
from .utils.uploads import floppy_kind, upload_url

POST_COLUMNS = """p.id,
  p.user_id,
  u.username,
  u.display_name,
  p.text,
  p.pixel_data,
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


def with_media(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return row
    result = dict(row)
    result["image_url"] = upload_url(row.get("image_path"))
    result["floppy_url"] = upload_url(row.get("floppy_path"))
    result["floppy_kind"] = (
        floppy_kind(row["floppy_name"]) if row.get("floppy_name") else None
    )
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


def like_count(post_id: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM likes WHERE post_id = %s", (post_id,)
    )
    return int(row["c"]) if row else 0
