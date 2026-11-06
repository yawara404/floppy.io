"""floppy.io — 認証 / ユーザー整形"""

from __future__ import annotations

import hashlib
import secrets
import time
from collections import deque
from typing import Any

import bcrypt
from fastapi import HTTPException, Request

from .db import execute, fetch_one
from .config import TOKEN_TTL_DAYS
from .utils.uploads import upload_url

USER_COLUMNS = """id, username, display_name, bio,
  avatar_path, avatar_mime, avatar_bytes, avatar_width, avatar_height,
  icon_pixel, allow_replies,
  created_at"""

# --- 簡易レート制限 (プロセス内) -------------------------------------------
# 単一プロセス運用を前提とした軽量な防御。複数ワーカー / 大規模運用では
# Redis などの共有ストアに置き換えること。
_RATE_LIMITS: dict[str, deque[float]] = {}

# 長期間動かし続けてもメモリが増え続けないよう、一定回数ごとに
# 「最後のアクセスが古いバケット」を捨てる（監視カメラ等の IP ローテート対策）。
_RATE_LIMIT_IDLE_SECONDS = 3600.0
_RATE_LIMIT_SWEEP_EVERY = 256
_rate_limit_calls = 0


def _sweep_rate_limits(now: float) -> None:
    for key in list(_RATE_LIMITS):
        hits = _RATE_LIMITS[key]
        if not hits or now - hits[-1] > _RATE_LIMIT_IDLE_SECONDS:
            _RATE_LIMITS.pop(key, None)


def rate_limit(
    request: Request,
    bucket: str,
    limit: int = 8,
    window_seconds: int = 60,
) -> None:
    global _rate_limit_calls

    client = request.client.host if request.client else "unknown"
    key = f"{bucket}:{client}"
    now = time.monotonic()
    hits = _RATE_LIMITS.setdefault(key, deque())

    while hits and now - hits[0] > window_seconds:
        hits.popleft()

    if len(hits) >= limit:
        raise HTTPException(
            429,
            "試行回数が多すぎます。しばらく待ってから再試行してください。",
        )

    hits.append(now)

    _rate_limit_calls += 1
    if _rate_limit_calls % _RATE_LIMIT_SWEEP_EVERY == 0:
        _sweep_rate_limits(now)


def hash_token(token: str) -> str:
    """API トークンは DB に平文で置かず SHA-256 で保存する"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode(
        "ascii"
    )


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    # PHP の password_hash() は $2y$ を生成する。bcrypt は $2b$ として扱える。
    normalized = password_hash.replace("$2y$", "$2b$", 1)
    try:
        return bcrypt.checkpw(password.encode("utf-8"), normalized.encode("ascii"))
    except ValueError:
        return False


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    return header[7:].strip() or None


def current_user(request: Request) -> dict[str, Any] | None:
    if hasattr(request.state, "floppy_user"):
        return request.state.floppy_user

    token = bearer_token(request)
    user = None

    if token:
        digest = hash_token(token)
        ttl_sql = ""
        ttl_params: tuple[object, ...] = ()
        if TOKEN_TTL_DAYS > 0:
            ttl_sql = " AND t.created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"
            ttl_params = (TOKEN_TTL_DAYS,)

        user = fetch_one(
            """SELECT u.id, u.username, u.display_name, u.bio,
                      u.avatar_path, u.avatar_mime, u.avatar_bytes,
                      u.avatar_width, u.avatar_height, u.icon_pixel,
                      u.allow_replies, u.created_at
                 FROM api_tokens t
                 JOIN users u ON u.id = t.user_id
                WHERE t.token = %s"""
            + ttl_sql,
            (digest, *ttl_params),
        )

        # 旧 PHP 版が発行した平文トークンとの互換性。
        # 見つかった時点でハッシュに置き換える。
        if user is None:
            user = fetch_one(
                """SELECT u.id, u.username, u.display_name, u.bio,
                          u.avatar_path, u.avatar_mime, u.avatar_bytes,
                          u.avatar_width, u.avatar_height, u.icon_pixel,
                          u.allow_replies, u.created_at
                     FROM api_tokens t
                     JOIN users u ON u.id = t.user_id
                    WHERE t.token = %s"""
                + ttl_sql,
                (token, *ttl_params),
            )
            if user is not None:
                execute(
                    "UPDATE api_tokens SET token = %s WHERE token = %s",
                    (digest, token),
                )

    request.state.floppy_user = user
    return user


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="ログインが必要です。")
    return user


def issue_token(user_id: int) -> str:
    token = secrets.token_hex(32)
    execute(
        "INSERT INTO api_tokens (user_id, token) VALUES (%s, %s)",
        (user_id, hash_token(token)),
    )
    return token


def user_stats(user_id: int) -> dict[str, int]:
    row = fetch_one(
        """SELECT COALESCE(SUM(total_bytes), 0) AS total_bytes,
                  COUNT(*) AS post_count,
                  COALESCE(MAX(total_bytes), 0) AS largest_post_bytes
             FROM posts
            WHERE user_id = %s""",
        (user_id,),
    ) or {}
    return {
        "total_bytes": int(row.get("total_bytes") or 0),
        "post_count": int(row.get("post_count") or 0),
        "largest_post_bytes": int(row.get("largest_post_bytes") or 0),
    }


def follow_stats(user_id: int) -> dict[str, int]:
    row = fetch_one(
        """SELECT (SELECT COUNT(*) FROM follows WHERE follower_id = %s) AS following_count,
                  (SELECT COUNT(*) FROM follows WHERE followee_id = %s) AS follower_count""",
        (user_id, user_id),
    ) or {}
    return {
        "following_count": int(row.get("following_count") or 0),
        "follower_count": int(row.get("follower_count") or 0),
    }


def is_following(follower_id: int, followee_id: int) -> bool:
    row = fetch_one(
        "SELECT 1 AS found FROM follows WHERE follower_id = %s AND followee_id = %s",
        (follower_id, followee_id),
    )
    return bool(row)


def user_avatar_pixel(user_id: int) -> dict[str, object] | None:
    """最新の正方形ドット絵投稿をアイコン代わりに使う (32×24 は対象外)"""
    row = fetch_one(
        """SELECT pixel_data, pixel_width, pixel_height FROM posts
            WHERE user_id = %s
              AND pixel_width = pixel_height
              AND pixel_data <> REPEAT('0', CHAR_LENGTH(pixel_data))
            ORDER BY created_at DESC, id DESC LIMIT 1""",
        (user_id,),
    )
    if not row:
        return None
    return {
        "pixel": row.get("pixel_data") or "",
        "width": int(row.get("pixel_width") or 16),
        "height": int(row.get("pixel_height") or 16),
    }


def public_user(row: dict[str, Any], with_stats: bool = True) -> dict[str, Any]:
    user_id = int(row["id"])
    avatar = user_avatar_pixel(user_id)
    user: dict[str, Any] = {
        "id": user_id,
        "username": row["username"],
        "display_name": row["display_name"] or row["username"],
        "bio": row["bio"],
        "created_at": row["created_at"],
        "avatar_url": upload_url(row.get("avatar_path")),
        # 最新投稿のドット絵（アイコン未設定時のフォールバック）
        "avatar_pixel": avatar["pixel"] if avatar else None,
        "avatar_pixel_width": int(avatar["width"]) if avatar else 0,
        "avatar_pixel_height": int(avatar["height"]) if avatar else 0,
        # ユーザーが設定した 32×32 のドット絵アイコン（空は未設定）
        "icon_pixel": row.get("icon_pixel") or "",
        # 返信の受け付け（既定はオフ＝返信できない）
        "allow_replies": bool(int(row.get("allow_replies") or 0)),
    }

    if with_stats:
        user.update(user_stats(user_id))
        user.update(follow_stats(user_id))

    return user


def is_valid_username(username: str) -> bool:
    import re

    return bool(re.fullmatch(r"[A-Za-z0-9_]{3,20}", username or ""))


def char_length(value: str) -> int:
    return len(str(value))
