"""floppy.io — ユーザー / プロフィール API"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..config import DISK_LIMIT_BYTES
from ..db import execute, fetch_all, fetch_one
from ..posts import POST_COLUMNS, attach_likes, with_media
from ..schemas import PasswordIn, ProfileIn
from ..security import (
    USER_COLUMNS,
    char_length,
    current_user,
    hash_password,
    is_following,
    public_user,
    require_user,
    verify_password,
)
from ..utils.images import validate_image_data
from ..utils.uploads import delete_upload, save_upload

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/user")
def get_user(request: Request, username: str = "") -> dict:
    username = username.strip()
    if not username:
        raise HTTPException(400, "ユーザー名を指定してください。")

    row = fetch_one(f"SELECT {USER_COLUMNS} FROM users WHERE username = %s", (username,))
    if not row:
        raise HTTPException(404, "ユーザーが見つかりません。")

    posts = fetch_all(
        f"""SELECT {POST_COLUMNS}
              FROM posts p
              JOIN users u ON u.id = p.user_id
             WHERE p.user_id = %s
             ORDER BY p.created_at DESC, p.id DESC
             LIMIT 200""",
        (int(row["id"]),),
    )

    me = current_user(request)
    user = public_user(row)
    user["is_self"] = bool(me and int(me["id"]) == int(row["id"]))
    user["following"] = bool(
        me
        and not user["is_self"]
        and is_following(int(me["id"]), int(row["id"]))
    )

    return {
        "user": user,
        "posts": attach_likes([with_media(post) for post in posts], me),
    }


@router.post("/update_profile")
def update_profile(request: Request, payload: ProfileIn) -> dict:
    user = require_user(request)

    display_name = payload.display_name.strip()
    bio = payload.bio.strip()

    if not display_name:
        raise HTTPException(400, "表示名を入力してください。")

    if char_length(display_name) > 64:
        raise HTTPException(400, "表示名は 64 文字以内にしてください。")

    if char_length(bio) > 300:
        raise HTTPException(400, "bio は 300 文字以内にしてください。")

    execute(
        "UPDATE users SET display_name = %s, bio = %s WHERE id = %s",
        (display_name, bio, int(user["id"])),
    )

    row = fetch_one(f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (int(user["id"]),))
    return {"user": public_user(row)}


@router.post("/change_password")
def change_password(request: Request, payload: PasswordIn) -> dict:
    user = require_user(request)

    current = payload.current_password
    new = payload.new_password

    if len(new.encode("utf-8")) < 6:
        raise HTTPException(400, "新しいパスワードは 6 文字以上にしてください。")

    row = fetch_one(
        "SELECT password_hash FROM users WHERE id = %s", (int(user["id"]),)
    )
    if not row or not verify_password(current, str(row.get("password_hash") or "")):
        raise HTTPException(400, "現在のパスワードが違います。")

    execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (hash_password(new), int(user["id"])),
    )

    return {"ok": True}


@router.post("/update_avatar")
async def update_avatar(request: Request) -> dict:
    user = require_user(request)
    form = await request.form()

    row = fetch_one("SELECT avatar_path FROM users WHERE id = %s", (int(user["id"]),))
    current_path = str((row or {}).get("avatar_path") or "")

    if str(form.get("remove") or "") == "1":
        execute(
            """UPDATE users
                  SET avatar_path = '', avatar_mime = '', avatar_bytes = 0,
                      avatar_width = 0, avatar_height = 0
                WHERE id = %s""",
            (int(user["id"]),),
        )
        delete_upload(current_path)
        fresh = fetch_one(
            f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (int(user["id"]),)
        )
        return {"user": public_user(fresh)}

    avatar = form.get("avatar")
    if avatar is None or not hasattr(avatar, "read"):
        raise HTTPException(400, "画像が選択されていません。")

    data = await avatar.read()
    info, error = validate_image_data(data)
    if error:
        raise HTTPException(400, error)

    if len(data) > DISK_LIMIT_BYTES:
        raise HTTPException(400, "プロフィール画像は 1.44MB 以内にしてください。")

    try:
        path = save_upload(data, info.ext)
    except OSError:
        raise HTTPException(500, "画像の保存に失敗しました。") from None

    execute(
        """UPDATE users
              SET avatar_path = %s, avatar_mime = %s, avatar_bytes = %s,
                  avatar_width = %s, avatar_height = %s
            WHERE id = %s""",
        (
            path,
            info.mime,
            len(data),
            info.width,
            info.height,
            int(user["id"]),
        ),
    )

    delete_upload(current_path)
    fresh = fetch_one(
        f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (int(user["id"]),)
    )
    return {"user": public_user(fresh)}
