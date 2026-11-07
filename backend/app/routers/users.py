"""floppy.io — ユーザー / プロフィール API"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response

from ..config import DISK_LIMIT_BYTES
from ..db import execute, fetch_all, fetch_one
from ..disks import attach_disks
from ..posts import POST_COLUMNS, attach_likes, attach_reply_counts, with_media
from ..schemas import IconPixelIn, PasswordIn, ProfileIn, ReplySettingIn
from ..security import (
    USER_COLUMNS,
    char_length,
    current_user,
    hash_password,
    is_following,
    public_user,
    require_user,
    user_avatar_pixel,
    verify_password,
)
from ..utils.images import validate_image_data
from ..utils.pixels import normalize_icon_pixel, pixel_svg
from ..utils.uploads import absolute_upload_url, delete_upload, save_upload, upload_url

router = APIRouter(prefix="/api", tags=["users"])


@router.get("/users/{username}/connections/{kind}")
def get_connections(
    request: Request,
    username: str,
    kind: str,
    offset: int = Query(default=0, ge=0),
) -> dict:
    """公開プロフィールのフォロー関係。認証情報は返さず、50 件ずつ取得する。"""
    if kind not in ("following", "followers"):
        raise HTTPException(400, "一覧の種類が正しくありません。")
    owner = fetch_one("SELECT id FROM users WHERE username = %s", (username.strip(),))
    if not owner:
        raise HTTPException(404, "ユーザーが見つかりません。")

    me = current_user(request)
    my_id = int(me["id"]) if me else 0
    # 列名は上記で検証した種類からだけ選び、入力値はすべてバインドする。
    owner_column, member_column = (
        ("follower_id", "followee_id") if kind == "following"
        else ("followee_id", "follower_id")
    )
    rows = fetch_all(
        f"""SELECT u.id, u.username, u.display_name, u.bio, u.icon_pixel, u.avatar_path,
                   EXISTS(SELECT 1 FROM follows mine
                           WHERE mine.follower_id = %s AND mine.followee_id = u.id) AS following
              FROM follows f JOIN users u ON u.id = f.{member_column}
             WHERE f.{owner_column} = %s
             ORDER BY f.created_at DESC, u.id DESC
             LIMIT 51 OFFSET %s""",
        (my_id, int(owner["id"]), offset),
    )
    return {
        "users": [
            {
                "id": int(row["id"]), "username": row["username"],
                "display_name": row["display_name"] or row["username"],
                "bio": row["bio"], "icon_pixel": row.get("icon_pixel") or "",
                "avatar_url": upload_url(row.get("avatar_path")),
                "following": bool(row["following"]), "is_self": int(row["id"]) == my_id,
            }
            for row in rows[:50]
        ],
        "next_offset": offset + 50 if len(rows) > 50 else None,
    }


@router.get("/icon/{username}.svg")
def get_icon_svg(request: Request, username: str) -> Response:
    """投稿カード用のアバター画像を解決して返す。

    優先順位（プロフィールと同じ）:
      1. 32×32 のドット絵アイコン
      2. アップロードされたプロフィール画像（リダイレクト）
      3. 最新の正方形ドット絵投稿
    どれも無ければ 404（フロントは [F] にフォールバックする）。
    """
    row = fetch_one(
        "SELECT id, icon_pixel, avatar_path FROM users WHERE username = %s",
        (username.strip(),),
    )
    if not row:
        raise HTTPException(404, "ユーザーが見つかりません。")

    icon = normalize_icon_pixel(row.get("icon_pixel"))
    if icon:
        return Response(
            content=pixel_svg(icon, 32, 32, cell=8),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    avatar_url = absolute_upload_url(request, row.get("avatar_path"))
    if avatar_url:
        return RedirectResponse(
            avatar_url,
            status_code=302,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    pixel = user_avatar_pixel(int(row["id"]))
    if pixel:
        return Response(
            content=pixel_svg(
                str(pixel["pixel"]),
                int(pixel["width"]),
                int(pixel["height"]),
                cell=8,
            ),
            media_type="image/svg+xml",
            headers={"Cache-Control": "public, max-age=300"},
        )

    raise HTTPException(404, "アイコンが設定されていません。")



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
        "posts": attach_disks(
            attach_reply_counts(
                attach_likes([with_media(post) for post in posts], me)
            )
        ),
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


@router.post("/update_icon_pixel")
def update_icon_pixel(request: Request, payload: IconPixelIn) -> dict:
    """32×32 のドット絵アイコンを設定する（空文字で未設定に戻す）"""
    user = require_user(request)

    raw = payload.pixel_data.strip()
    if raw and (
        len(raw) != 1024
        or any(ch not in "0123456789abcdefABCDEF" for ch in raw)
    ):
        raise HTTPException(
            400,
            "アイコンは 32×32 のドット絵（1024 文字）で指定してください。",
        )

    # 全透明 (0000...) は「未設定」として扱う
    pixel = normalize_icon_pixel(raw)

    execute(
        "UPDATE users SET icon_pixel = %s WHERE id = %s",
        (pixel, int(user["id"])),
    )

    row = fetch_one(
        f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (int(user["id"]),)
    )
    return {"user": public_user(row)}


@router.post("/update_reply_setting")
def update_reply_setting(request: Request, payload: ReplySettingIn) -> dict:
    """返信の受け付けをオン / オフする（既定はオフ＝返信できない）"""
    user = require_user(request)

    execute(
        "UPDATE users SET allow_replies = %s WHERE id = %s",
        (1 if payload.allow_replies else 0, int(user["id"])),
    )

    row = fetch_one(
        f"SELECT {USER_COLUMNS} FROM users WHERE id = %s", (int(user["id"]),)
    )
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
