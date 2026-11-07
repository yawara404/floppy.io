"""floppy.io — ディスク (コミュニティ) の整形"""

from __future__ import annotations

from typing import Any

from .db import fetch_all

# ディスク一覧 / 詳細で共通して使う列
DISK_COLUMNS = """d.id,
  d.slug,
  d.name,
  d.description,
  d.owner_id,
  u.username AS owner_username,
  d.created_at"""

# 件数・最終投稿・参加状態を付けるサブクエリ
#   %s には閲覧者の user_id (未ログインは 0) を渡す
DISK_STATS = """(SELECT COUNT(*) FROM posts p
                   WHERE p.disk_id = d.id AND p.reply_to_id IS NULL) AS post_count,
  (SELECT COUNT(*) FROM disk_members m WHERE m.disk_id = d.id) AS member_count,
  (SELECT MAX(p.created_at) FROM posts p WHERE p.disk_id = d.id) AS last_post_at,
  (dm.user_id IS NOT NULL) AS is_member"""

DISK_JOINS = """JOIN users u ON u.id = d.owner_id
  LEFT JOIN disk_members dm ON dm.disk_id = d.id AND dm.user_id = %s"""


def disk_payload(row: dict[str, Any] | None, is_member: bool | None = None) -> dict | None:
    """DB の 1 行をフロントエンド向けのディスク情報に変換する"""
    if not row:
        return None

    def as_int(value: object) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    member = bool(as_int(row.get("is_member"))) if is_member is None else bool(is_member)

    return {
        "id": as_int(row.get("id")),
        "slug": row.get("slug") or "",
        "name": row.get("name") or "",
        "description": row.get("description") or "",
        "owner_id": as_int(row.get("owner_id")),
        "owner_username": row.get("owner_username") or "",
        "created_at": row.get("created_at"),
        "post_count": as_int(row.get("post_count")),
        "member_count": as_int(row.get("member_count")),
        "last_post_at": row.get("last_post_at"),
        "is_member": member,
    }


def attach_disks(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """投稿に書き込み先ディスクの最小情報 (id / slug / name) を付ける

    投稿一覧の SQL に毎回 LEFT JOIN を足さずに済むよう、disk_id をまとめて
    1 クエリで引く。ディスクに属さない投稿は disk = None。
    """
    if not posts:
        return posts

    ids = sorted({int(post["disk_id"]) for post in posts if post.get("disk_id")})
    mapping: dict[int, dict[str, Any]] = {}

    if ids:
        placeholders = ",".join(["%s"] * len(ids))
        rows = fetch_all(
            f"SELECT id, slug, name FROM disks WHERE id IN ({placeholders})",
            tuple(ids),
        )
        mapping = {
            int(row["id"]): {
                "id": int(row["id"]),
                "slug": row["slug"],
                "name": row["name"],
            }
            for row in rows
        }

    for post in posts:
        disk_id = post.get("disk_id")
        post["disk"] = mapping.get(int(disk_id)) if disk_id else None

    return posts
