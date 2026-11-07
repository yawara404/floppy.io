"""floppy.io — 検索サジェスト API

検索フォームの入力中に、ユーザー / ディスク / 投稿を横断して候補を返す。
本文の全文検索は既存の GET /api/posts?q= が担当する。
"""

from __future__ import annotations

import hashlib
import re
from urllib.parse import quote

from fastapi import APIRouter

from ..db import fetch_all
from ..utils.pixels import normalize_icon_pixel
from ..utils.uploads import public_base_path, upload_url

router = APIRouter(prefix="/api", tags=["search"])

MAX_QUERY_LENGTH = 64
LIMIT_USERS = 5
LIMIT_DISKS = 5
LIMIT_POSTS = 3
POST_EXCERPT_CHARS = 120


def like_escape(value: str) -> str:
    return re.sub(r"([\\%_])", r"\\\1", value)


def icon_url(row: dict) -> str:
    icon = normalize_icon_pixel(row.get("icon_pixel"))
    avatar_path = str(row.get("avatar_path") or "")
    version = (
        hashlib.sha1(f"{icon}|{avatar_path}".encode("utf-8")).hexdigest()[:8]
        if icon or avatar_path
        else ""
    )
    return (
        f"{public_base_path()}api/icon/{quote(str(row['username']))}.svg"
        + (f"?v={version}" if version else "")
    )


@router.get("/search/suggest")
def search_suggest(q: str = "") -> dict:
    """入力中のキーワードから候補を返す（空なら空配列）"""
    keyword = q.strip()[:MAX_QUERY_LENGTH]
    if not keyword:
        return {"q": "", "users": [], "disks": [], "posts": []}

    escaped = like_escape(keyword)
    like = f"%{escaped}%"
    prefix = f"{escaped}%"

    # ---------------------------------------------------------------- users
    user_rows = fetch_all(
        """SELECT id, username, display_name, avatar_path, icon_pixel
             FROM users
            WHERE username LIKE %s OR display_name LIKE %s
            ORDER BY (username = %s) DESC,
                     (username LIKE %s) DESC,
                     (display_name LIKE %s) DESC,
                     username ASC
            LIMIT %s""",
        (like, like, keyword, prefix, prefix, LIMIT_USERS),
    )

    users = [
        {
            "id": int(row["id"]),
            "username": row["username"],
            "display_name": row["display_name"] or row["username"],
            "avatar_url": upload_url(row.get("avatar_path")),
            "icon_url": icon_url(row),
        }
        for row in user_rows
    ]

    # ---------------------------------------------------------------- disks
    disk_rows = fetch_all(
        """SELECT d.id,
                  d.slug,
                  d.name,
                  d.description,
                  (SELECT COUNT(*) FROM posts p
                    WHERE p.disk_id = d.id AND p.reply_to_id IS NULL) AS post_count
             FROM disks d
            WHERE d.name LIKE %s OR d.slug LIKE %s OR d.description LIKE %s
            ORDER BY (d.name = %s) DESC,
                     (d.name LIKE %s) DESC,
                     (d.slug LIKE %s) DESC,
                     d.name ASC
            LIMIT %s""",
        (like, like, like, keyword, prefix, prefix, LIMIT_DISKS),
    )

    disks = [
        {
            "id": int(row["id"]),
            "slug": row["slug"],
            "name": row["name"],
            "description": row["description"] or "",
            "post_count": int(row.get("post_count") or 0),
        }
        for row in disk_rows
    ]

    # ---------------------------------------------------------------- posts
    post_rows = fetch_all(
        f"""SELECT p.id,
                   LEFT(p.text, {POST_EXCERPT_CHARS}) AS text,
                   p.image_path,
                   p.youtube_id,
                   u.username,
                   u.display_name,
                   p.created_at
              FROM posts p
              JOIN users u ON u.id = p.user_id
             WHERE p.reply_to_id IS NULL
               AND (p.text LIKE %s OR u.username LIKE %s OR u.display_name LIKE %s)
             ORDER BY p.created_at DESC, p.id DESC
             LIMIT %s""",
        (like, like, like, LIMIT_POSTS),
    )

    posts = []
    for row in post_rows:
        if row.get("youtube_id"):
            kind = "youtube"
        elif row.get("image_path"):
            kind = "image"
        else:
            kind = "text"

        posts.append(
            {
                "id": int(row["id"]),
                "text": (row.get("text") or "").strip(),
                "username": row["username"],
                "display_name": row["display_name"] or row["username"],
                "kind": kind,
            }
        )

    return {"q": keyword, "users": users, "disks": disks, "posts": posts}
