"""floppy.io — いいね / フォロー API"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..db import execute, fetch_one
from ..posts import like_count
from ..schemas import FollowIn, IdIn
from ..security import follow_stats, is_following, require_user

router = APIRouter(prefix="/api", tags=["social"])


@router.post("/like")
def toggle_like(request: Request, payload: IdIn) -> dict:
    user = require_user(request)
    post_id = int(payload.id or 0)

    if post_id <= 0:
        raise HTTPException(400, "投稿 ID が不正です。")

    if not fetch_one("SELECT id FROM posts WHERE id = %s", (post_id,)):
        raise HTTPException(404, "投稿が見つかりません。")

    existing = fetch_one(
        "SELECT 1 AS found FROM likes WHERE post_id = %s AND user_id = %s",
        (post_id, int(user["id"])),
    )

    if existing:
        execute(
            "DELETE FROM likes WHERE post_id = %s AND user_id = %s",
            (post_id, int(user["id"])),
        )
        liked = False
    else:
        execute(
            "INSERT INTO likes (post_id, user_id) VALUES (%s, %s)",
            (post_id, int(user["id"])),
        )
        liked = True

    return {"liked": liked, "like_count": like_count(post_id)}


@router.post("/follow")
def toggle_follow(request: Request, payload: FollowIn) -> dict:
    user = require_user(request)

    username = payload.username.strip()
    target_id = int(payload.id or 0)

    if not username and target_id <= 0:
        raise HTTPException(400, "フォローするユーザーを指定してください。")

    target = fetch_one(
        "SELECT id FROM users WHERE username = %s"
        if username
        else "SELECT id FROM users WHERE id = %s",
        (username if username else target_id,),
    )

    if not target:
        raise HTTPException(404, "ユーザーが見つかりません。")

    target_id = int(target["id"])
    my_id = int(user["id"])

    if target_id == my_id:
        raise HTTPException(400, "自分自身はフォローできません。")

    if is_following(my_id, target_id):
        execute(
            "DELETE FROM follows WHERE follower_id = %s AND followee_id = %s",
            (my_id, target_id),
        )
        following = False
    else:
        execute(
            "INSERT INTO follows (follower_id, followee_id) VALUES (%s, %s)",
            (my_id, target_id),
        )
        following = True

    return {
        "following": following,
        "follower_count": follow_stats(target_id)["follower_count"],
    }
