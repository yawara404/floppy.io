"""floppy.io — ディスク (コミュニティ) API

「フォロー中」タイムラインの代わりに、フロッピー 1 枚に見立てた
コミュニティ（ディスク）を提供する。誰でも閲覧でき、書き込みには
ログインとディスクへの参加が必要。
"""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException, Request, status

from ..db import execute, fetch_all, fetch_one
from ..disks import (
    DISK_COLUMNS,
    DISK_JOINS,
    DISK_STATS,
    attach_disks,
    disk_payload,
)
from ..posts import POST_COLUMNS, attach_likes, attach_reply_counts, with_media
from ..schemas import DiskIn, DiskRefIn
from ..security import current_user, rate_limit, require_user

router = APIRouter(prefix="/api", tags=["disks"])

# URL (/d/:slug) に使える形。小文字英数字とハイフン、2〜32 文字。
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,31}$")

NAME_MAX = 40
DESCRIPTION_MAX = 300


def like_escape(value: str) -> str:
    return re.sub(r"([\\%_])", r"\\\1", value)


def viewer_id(request: Request) -> int:
    me = current_user(request)
    return int(me["id"]) if me else 0


def find_disk(request: Request, slug: str) -> dict:
    """slug からディスク 1 件を取得する（無ければ 404）"""
    row = fetch_one(
        f"""SELECT {DISK_COLUMNS}, {DISK_STATS}
              FROM disks d
              {DISK_JOINS}
             WHERE d.slug = %s""",
        (viewer_id(request), slug.strip().lower()),
    )
    if not row:
        raise HTTPException(404, "ディスクが見つかりません。")
    return row


@router.get("/disks")
def list_disks(request: Request, filter: str = "", q: str = "") -> dict:
    """ディスク一覧。filter=joined で参加中のディスクだけを返す"""
    me = current_user(request)
    scope = filter.strip().lower()
    keyword = q.strip()

    if scope == "joined" and not me:
        raise HTTPException(401, "参加中のディスクを見るにはログインが必要です。")

    params: list[object] = [int(me["id"]) if me else 0]
    where: list[str] = []

    if scope == "joined":
        where.append("dm.user_id IS NOT NULL")

    if keyword:
        like = f"%{like_escape(keyword)}%"
        where.append("(d.name LIKE %s OR d.slug LIKE %s OR d.description LIKE %s)")
        params.extend([like, like, like])

    sql = f"""SELECT {DISK_COLUMNS}, {DISK_STATS}
                FROM disks d
                {DISK_JOINS}"""

    if where:
        sql += " WHERE " + " AND ".join(where)

    # 最終書き込みが新しい順。まだ空のディスクは後ろに回す。
    sql += """ ORDER BY (last_post_at IS NULL) ASC,
                        last_post_at DESC,
                        d.created_at DESC
                LIMIT 100"""

    rows = fetch_all(sql, tuple(params))
    return {"disks": [disk_payload(row) for row in rows]}


@router.post("/disks", status_code=status.HTTP_201_CREATED)
def create_disk(request: Request, payload: DiskIn) -> dict:
    user = require_user(request)
    rate_limit(request, "disk_create", limit=10, window_seconds=3600)

    name = payload.name.strip()
    slug = payload.slug.strip().lower()
    description = payload.description.strip()

    if not name:
        raise HTTPException(400, "ディスク名を入力してください。")
    if len(name) > NAME_MAX:
        raise HTTPException(400, f"ディスク名は {NAME_MAX} 文字までです。")
    if not SLUG_RE.fullmatch(slug):
        raise HTTPException(
            400,
            "ディスク ID は半角英数字とハイフン（2〜32 文字）で入力してください。",
        )
    if len(description) > DESCRIPTION_MAX:
        raise HTTPException(400, f"説明は {DESCRIPTION_MAX} 文字までです。")

    if fetch_one("SELECT id FROM disks WHERE slug = %s", (slug,)):
        raise HTTPException(409, "このディスク ID は既に使われています。")

    disk_id = execute(
        "INSERT INTO disks (slug, name, description, owner_id) VALUES (%s, %s, %s, %s)",
        (slug, name, description, int(user["id"])),
    )

    # 作成者は自動で参加する
    execute(
        "INSERT INTO disk_members (disk_id, user_id) VALUES (%s, %s)",
        (disk_id, int(user["id"])),
    )

    row = fetch_one(
        f"""SELECT {DISK_COLUMNS}, {DISK_STATS}
              FROM disks d
              {DISK_JOINS}
             WHERE d.id = %s""",
        (int(user["id"]), disk_id),
    )
    return {"disk": disk_payload(row, True)}


@router.post("/disks/join")
def toggle_disk_membership(request: Request, payload: DiskRefIn) -> dict:
    """ディスクへの参加 / 退出を切り替える"""
    user = require_user(request)
    my_id = int(user["id"])

    slug = payload.slug.strip().lower()
    disk_id = int(payload.id or 0)

    if not slug and disk_id <= 0:
        raise HTTPException(400, "参加するディスクを指定してください。")

    target = fetch_one(
        "SELECT id, slug FROM disks WHERE slug = %s"
        if slug
        else "SELECT id, slug FROM disks WHERE id = %s",
        (slug if slug else disk_id,),
    )
    if not target:
        raise HTTPException(404, "ディスクが見つかりません。")

    disk_id = int(target["id"])

    if fetch_one(
        "SELECT 1 AS found FROM disk_members WHERE disk_id = %s AND user_id = %s",
        (disk_id, my_id),
    ):
        execute(
            "DELETE FROM disk_members WHERE disk_id = %s AND user_id = %s",
            (disk_id, my_id),
        )
        joined = False
    else:
        execute(
            "INSERT INTO disk_members (disk_id, user_id) VALUES (%s, %s)",
            (disk_id, my_id),
        )
        joined = True

    count = fetch_one(
        "SELECT COUNT(*) AS c FROM disk_members WHERE disk_id = %s",
        (disk_id,),
    ) or {}

    return {"is_member": joined, "member_count": int(count.get("c") or 0)}


@router.get("/disks/{slug}")
def get_disk(request: Request, slug: str) -> dict:
    """ディスク 1 件とその書き込み一覧"""
    me = current_user(request)
    row = find_disk(request, slug)

    posts = fetch_all(
        f"""SELECT {POST_COLUMNS}
              FROM posts p
              JOIN users u ON u.id = p.user_id
             WHERE p.disk_id = %s AND p.reply_to_id IS NULL
             ORDER BY p.created_at DESC, p.id DESC
             LIMIT 100""",
        (int(row["id"]),),
    )

    post_list = attach_disks(
        attach_reply_counts(
            attach_likes([with_media(post) for post in posts], me)
        )
    )

    return {"disk": disk_payload(row), "posts": post_list}
