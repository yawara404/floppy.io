"""floppy.io — 認証 API"""

from __future__ import annotations

import pymysql
from fastapi import APIRouter, HTTPException, Request, status

from ..db import execute, fetch_one
from ..schemas import LoginIn, RegisterIn
from ..security import (
    USER_COLUMNS,
    bearer_token,
    char_length,
    hash_password,
    hash_token,
    is_valid_username,
    issue_token,
    public_user,
    rate_limit,
    require_user,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: Request, payload: RegisterIn) -> dict:
    rate_limit(request, "register", limit=5, window_seconds=300)

    username = payload.username.strip()
    password = payload.password
    display_name = payload.display_name.strip()

    if not is_valid_username(username):
        raise HTTPException(
            400,
            "ユーザー名は半角英数字とアンダースコア (_) の 3〜20 文字で入力してください。",
        )

    if len(password.encode("utf-8")) < 6:
        raise HTTPException(400, "パスワードは 6 文字以上にしてください。")

    if char_length(display_name) > 64:
        raise HTTPException(400, "表示名は 64 文字以内にしてください。")

    if fetch_one("SELECT id FROM users WHERE username = %s", (username,)):
        raise HTTPException(409, "このユーザー名は既に使われています。")

    try:
        user_id = execute(
            """INSERT INTO users (username, display_name, bio, password_hash)
               VALUES (%s, %s, %s, %s)""",
            (username, display_name or username, "", hash_password(password)),
        )
    except pymysql.err.IntegrityError:
        raise HTTPException(409, "このユーザー名は既に使われています。") from None
    # 接続不能 / スキーマ不足などの DB エラーは握りつぶさず、
    # main.py の共通ハンドラに復旧手順付きの 503 を返させる。

    # ここから先で失敗すると「ユーザーだけ作られた」状態が残り、
    # 再登録が 409 になって詰む。失敗時は作成を取り消す。
    try:
        token = issue_token(user_id)
        row = fetch_one(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (user_id,))
        return {"token": token, "user": public_user(row)}
    except Exception:
        try:
            # api_tokens は ON DELETE CASCADE で一緒に消える
            execute("DELETE FROM users WHERE id = %s", (user_id,))
        except pymysql.MySQLError:
            pass
        # 接続不能 / スキーマ不足は main.py の共通ハンドラに任せる
        raise


@router.post("/login")
def login(request: Request, payload: LoginIn) -> dict:
    rate_limit(request, "login", limit=10, window_seconds=60)

    username = payload.username.strip()
    password = payload.password

    if not username or not password:
        raise HTTPException(400, "ユーザー名とパスワードを入力してください。")

    row = fetch_one(
        """SELECT id, username, display_name, bio,
                  avatar_path, avatar_mime, avatar_bytes,
                  avatar_width, avatar_height, icon_pixel, allow_replies,
                  created_at, password_hash
             FROM users
            WHERE username = %s
               OR (username = 'floppy' AND %s IN ('floppy.io', 'floppy_io'))""",
        (username, username),
    )

    if not row or not verify_password(password, str(row.get("password_hash") or "")):
        raise HTTPException(401, "ユーザー名またはパスワードが違います。")

    token = issue_token(int(row["id"]))
    return {"token": token, "user": public_user(row)}


@router.post("/logout")
def logout(request: Request) -> dict:
    require_user(request)

    token = bearer_token(request)
    if token:
        execute(
            "DELETE FROM api_tokens WHERE token = %s OR token = %s",
            (hash_token(token), token),
        )

    return {"ok": True}


@router.get("/me")
def me(request: Request) -> dict:
    user = require_user(request)
    return {"user": public_user(user)}
