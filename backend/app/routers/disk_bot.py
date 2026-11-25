"""参加済みディスクで利用できる、読み取り専用の Bot コマンド。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..db import fetch_all, fetch_one
from ..security import rate_limit, require_user
from ..vendor.steamscordbot.disk import latest_posts
from .steam import playing_games

router = APIRouter(prefix="/api/disks", tags=["disk bot"])


def joined_disk(request: Request, slug: str) -> dict:
    user = require_user(request)
    rate_limit(request, "disk_bot", limit=90, window_seconds=60)
    disk = fetch_one(
        """SELECT d.id FROM disks d JOIN disk_members m ON m.disk_id = d.id
            WHERE d.slug = %s AND m.user_id = %s""",
        (slug, int(user["id"])),
    )
    if not disk:
        raise HTTPException(404, "ディスクに参加するとBotを利用できます。")
    return disk


@router.get("/{slug}/bot/latest")
def latest(request: Request, slug: str) -> dict:
    disk = joined_disk(request, slug)
    rows = fetch_all(
        """SELECT p.id, u.username, LEFT(p.text, 120) AS excerpt
             FROM posts p JOIN users u ON u.id = p.user_id
            WHERE p.disk_id = %s AND p.reply_to_id IS NULL
            ORDER BY p.created_at DESC, p.id DESC LIMIT 5""",
        (disk["id"],),
    )
    return {"posts": latest_posts(rows)}


@router.get("/{slug}/bot/playing")
def playing(request: Request, slug: str, username: str = "") -> dict:
    disk = joined_disk(request, slug)
    username = username.strip().removeprefix("@")
    if not username or len(username) > 32:
        raise HTTPException(400, "ディスク参加者のユーザー名を入力してください。")

    link = fetch_one(
        """SELECT s.steam_id FROM disk_members m
             JOIN users u ON u.id = m.user_id
             JOIN steam_accounts s ON s.user_id = u.id
            WHERE m.disk_id = %s AND u.username = %s AND s.show_in_disks = 1""",
        (disk["id"], username),
    )
    if not link:
        return {"playing": None}
    steam_id = link["steam_id"]
    return {"playing": playing_games([steam_id]).get(steam_id)}
