"""floppy.io — 投稿 API"""

from __future__ import annotations

import html
import re

from fastapi import APIRouter, HTTPException, Request, status
from ..utils.pixels import pixel_svg
from ..utils.uploads import absolute_base, absolute_upload_url, floppy_kind

from ..config import DISK_LIMIT_BYTES
from ..db import execute, fetch_all, fetch_one
from ..posts import POST_COLUMNS, attach_likes, with_media
from ..security import current_user, require_user
from ..utils.images import validate_image_data
from ..utils.pixels import is_blank_pixel, normalize_pixel
from ..utils.uploads import (
    delete_upload,
    floppy_store_ext,
    save_upload,
    validate_floppy_data,
)
from ..utils.youtube import youtube_embed_info

router = APIRouter(prefix="/api", tags=["posts"])


def like_escape(value: str) -> str:
    return re.sub(r"([\\%_])", r"\\\1", value)


@router.get("/posts")
def list_posts(
    request: Request,
    username: str = "",
    q: str = "",
    feed: str = "",
) -> dict:
    username = username.strip()
    keyword = q.strip()

    sql = f"""SELECT {POST_COLUMNS}
                FROM posts p
                JOIN users u ON u.id = p.user_id"""
    where: list[str] = []
    params: list[object] = []

    if username:
        where.append("u.username = %s")
        params.append(username)

    if feed == "following":
        me = current_user(request)
        if me is None:
            raise HTTPException(401, "ログインが必要です。")
        where.append(
            "(p.user_id = %s OR p.user_id IN "
            "(SELECT followee_id FROM follows WHERE follower_id = %s))"
        )
        params.extend([int(me["id"]), int(me["id"])])

    if keyword:
        like = f"%{like_escape(keyword)}%"
        where.append("(p.text LIKE %s OR u.username LIKE %s OR u.display_name LIKE %s)")
        params.extend([like, like, like])

    if where:
        sql += " WHERE " + " AND ".join(where)

    sql += " ORDER BY p.created_at DESC, p.id DESC LIMIT 200"

    rows = fetch_all(sql, tuple(params))
    posts = attach_likes([with_media(row) for row in rows], current_user(request))
    return {"posts": posts}


@router.post("/posts", status_code=status.HTTP_201_CREATED)
async def create_post(request: Request) -> dict:
    user = require_user(request)

    content_type = request.headers.get("content-type", "")
    is_multipart = content_type.startswith("multipart/form-data")

    text = ""
    pixel_raw = ""
    image_file = None
    floppy_file = None

    if is_multipart:
        form = await request.form()
        text = str(form.get("text") or "")
        pixel_raw = str(form.get("pixel_data") or "")
        image_file = form.get("image")
        floppy_file = form.get("floppy")
    else:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            text = str(payload.get("text") or "")
            pixel_raw = str(payload.get("pixel_data") or "")

    pixel = normalize_pixel(pixel_raw)

    image_data = b""
    if image_file is not None and hasattr(image_file, "read"):
        image_data = await image_file.read()

    floppy_data = b""
    floppy_filename = ""
    if floppy_file is not None and hasattr(floppy_file, "read"):
        floppy_data = await floppy_file.read()
        floppy_filename = str(getattr(floppy_file, "filename", "") or "")

    image = None
    if image_data:
        info, error = validate_image_data(image_data)
        if error:
            raise HTTPException(400, error)
        image = info

    floppy = None
    if floppy_data:
        floppy, error = validate_floppy_data(floppy_data, floppy_filename)
        if error:
            raise HTTPException(400, error)

    if not text and is_blank_pixel(pixel) and not image and not floppy:
        raise HTTPException(
            400,
            "本文・ドット絵・画像・フロッピーファイルのいずれかを入力してください。",
        )

    text_bytes = len(text.encode("utf-8"))
    image_bytes = len(image_data) if image else 0
    floppy_bytes = int(floppy["bytes"]) if floppy else 0
    total_bytes = text_bytes + 256 + image_bytes + floppy_bytes

    if total_bytes > DISK_LIMIT_BYTES:
        raise HTTPException(
            403,
            "1 投稿あたりの容量上限（1.44MB）を超えています。"
            f"（本文 {text_bytes:,} + ドット絵 256"
            f" + 画像 {image_bytes:,} + フロッピー {floppy_bytes:,} bytes）",
        )

    image_path = ""
    floppy_path = ""

    try:
        if image:
            image_path = save_upload(image_data, image.ext)
        if floppy:
            floppy_path = save_upload(
                floppy_data, floppy_store_ext(str(floppy["name"]))
            )
    except OSError:
        delete_upload(image_path)
        delete_upload(floppy_path)
        raise HTTPException(500, "ファイルの保存に失敗しました。") from None

    youtube = await youtube_embed_info(text)

    try:
        post_id = execute(
            """INSERT INTO posts
                (user_id, text, pixel_data, image_path, image_mime, image_bytes,
                 image_width, image_height, youtube_id, youtube_title, youtube_thumbnail,
                 floppy_path, floppy_name, floppy_bytes,
                 text_bytes, pixel_bytes, total_bytes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                int(user["id"]),
                text,
                pixel,
                image_path,
                image.mime if image else "",
                image_bytes,
                image.width if image else 0,
                image.height if image else 0,
                youtube["id"],
                youtube["title"],
                youtube["thumbnail"],
                floppy_path,
                floppy["name"] if floppy else "",
                floppy_bytes,
                text_bytes,
                256,
                total_bytes,
            ),
        )
    except Exception:
        delete_upload(image_path)
        delete_upload(floppy_path)
        raise HTTPException(500, "投稿の保存に失敗しました。") from None

    row = fetch_one(
        f"""SELECT {POST_COLUMNS}
              FROM posts p
              JOIN users u ON u.id = p.user_id
             WHERE p.id = %s""",
        (post_id,),
    )
    posts = attach_likes([with_media(row)], user)

    return {"post": posts[0]}


@router.post("/delete_post")
@router.delete("/delete_post")
def delete_post(request: Request, payload: dict | None = None) -> dict:
    user = require_user(request)

    raw_id = (payload or {}).get("id", 0)
    try:
        post_id = int(raw_id or 0)
    except (TypeError, ValueError):
        post_id = 0

    if post_id <= 0:
        raise HTTPException(400, "投稿 ID が不正です。")

    row = fetch_one(
        "SELECT image_path, floppy_path FROM posts WHERE id = %s AND user_id = %s",
        (post_id, int(user["id"])),
    )

    if not row:
        raise HTTPException(404, "投稿が見つかりません。")

    execute(
        "DELETE FROM posts WHERE id = %s AND user_id = %s",
        (post_id, int(user["id"])),
    )
    delete_upload(row.get("image_path"))
    delete_upload(row.get("floppy_path"))

    return {"deleted": post_id}


@router.get("/preview")
def preview(request: Request, id: int = 0) -> dict:
    if id <= 0:
        raise HTTPException(400, "投稿 ID が不正です。")

    row = fetch_one(
        """SELECT p.id,
                  u.username,
                  u.display_name,
                  p.text,
                  p.pixel_data,
                  p.image_path,
                  p.image_bytes,
                  p.image_width,
                  p.image_height,
                  p.youtube_id,
                  p.youtube_title,
                  p.youtube_thumbnail,
                  p.floppy_path,
                  p.floppy_name,
                  p.floppy_bytes,
                  p.total_bytes,
                  p.created_at
             FROM posts p
             JOIN users u ON u.id = p.user_id
            WHERE p.id = %s""",
        (id,),
    )

    if not row:
        raise HTTPException(404, "投稿が見つかりません。")

    author = str(row["username"])
    shown = str(row["display_name"] or row["username"])
    text = html.escape(str(row["text"] or ""))
    bytes_label = f"{int(row['total_bytes']):,}"
    date = html.escape(str(row["created_at"]))
    svg = pixel_svg(str(row["pixel_data"]))

    image_url = absolute_upload_url(request, row.get("image_path"))
    image_html = (
        f'<div style="margin:8px 0"><img src="{html.escape(image_url)}" alt="" '
        'style="max-width:100%;display:block;border-radius:8px;border:1px solid #29343d"></div>'
        if image_url
        else ""
    )

    youtube_html = ""
    if row.get("youtube_id"):
        video_id = str(row["youtube_id"])
        thumb = str(
            row.get("youtube_thumbnail")
            or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        )
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        title = html.escape(str(row.get("youtube_title") or "YouTube"))
        youtube_html = (
            f'<div style="margin:8px 0"><a href="{video_url}" target="_blank" '
            f'rel="noopener"><img src="{html.escape(thumb)}" alt="" '
            'style="max-width:100%;display:block;border-radius:8px;border:1px solid #29343d"></a>'
            f'<div style="font-size:10px;color:#8a99a8;margin-top:4px">▶ {title}</div></div>'
        )

    floppy_url = absolute_upload_url(request, row.get("floppy_path"))
    floppy_html = ""
    if floppy_url:
        floppy_name = html.escape(str(row.get("floppy_name") or "floppy.bin"))
        floppy_bytes = f"{int(row.get('floppy_bytes') or 0):,}"
        href = html.escape(floppy_url)
        if row.get("floppy_name") and floppy_kind(str(row["floppy_name"])) == "audio":
            floppy_html = (
                f'<div style="margin:8px 0"><div style="font-size:10px;color:#8a99a8">'
                f"💾 {floppy_name} · {floppy_bytes} bytes</div>"
                f'<audio controls preload="none" src="{href}" '
                'style="width:100%;max-width:320px;margin-top:4px"></audio></div>'
            )
        else:
            floppy_html = (
                f'<div style="margin:8px 0"><a href="{href}" '
                'style="font-size:10px;color:#7df9c6;text-decoration:none">'
                f"💾 {floppy_name} · {floppy_bytes} bytes をダウンロード</a></div>"
            )

    card_html = (
        "<div style=\"font-family:'Courier New',monospace;background:#0b1117;"
        "border:1px solid #2a3a33;border-radius:12px;padding:14px;max-width:360px;"
        'color:#e9eef4;box-sizing:border-box">'
        '<div style="display:flex;gap:12px;align-items:flex-start">'
        '<div style="background:#ffffff;border-radius:6px;padding:4px;line-height:0">'
        f"{svg}</div>"
        '<div style="min-width:0">'
        '<div style="font-family:Arial,sans-serif;font-weight:700;color:#7df9c6;'
        'letter-spacing:.1em;font-size:11px">FLOPPY.IO / SHARED DISK</div>'
        f'<div style="margin:8px 0;white-space:pre-wrap;word-break:break-word;'
        f'font-size:12px;line-height:1.7">{text}</div>'
        f"{image_html}{youtube_html}{floppy_html}"
        '<div style="font-size:10px;color:#8a99a8;margin-top:8px">'
        f"{html.escape(shown)} (@{html.escape(author)}) · {bytes_label} bytes · {date}</div>"
        "</div></div></div>"
    )

    return {
        "type": "floppy_io:post",
        "version": "1.0",
        "id": int(row["id"]),
        "author": author,
        "author_name": shown,
        "text": row["text"],
        "pixel_data": row["pixel_data"],
        "pixel_svg": svg,
        "image_url": image_url,
        "image_bytes": int(row.get("image_bytes") or 0),
        "youtube_id": str(row.get("youtube_id") or ""),
        "youtube_title": str(row.get("youtube_title") or ""),
        "youtube_thumbnail": str(row.get("youtube_thumbnail") or ""),
        "floppy_url": floppy_url,
        "floppy_name": str(row.get("floppy_name") or ""),
        "floppy_bytes": int(row.get("floppy_bytes") or 0),
        "floppy_kind": floppy_kind(str(row["floppy_name"]))
        if row.get("floppy_name")
        else None,
        "total_bytes": int(row["total_bytes"]),
        "created_at": row["created_at"],
        "url": f"{absolute_base(request)}api/preview?id={int(row['id'])}",
        "html": card_html,
    }


@router.get("/disk_usage")
def disk_usage(username: str = "") -> dict:
    username = username.strip()

    sql = """SELECT COALESCE(SUM(total_bytes), 0) AS total_bytes,
                    COUNT(*) AS post_count,
                    COALESCE(MAX(total_bytes), 0) AS largest_post_bytes
               FROM posts"""
    params: tuple[object, ...] = ()

    if username:
        sql += " JOIN users u ON u.id = posts.user_id WHERE u.username = %s"
        params = (username,)

    row = fetch_one(sql, params) or {}

    return {
        "limit_bytes": DISK_LIMIT_BYTES,
        "limit_scope": "post",
        "username": username or None,
        "total_bytes": int(row.get("total_bytes") or 0),
        "post_count": int(row.get("post_count") or 0),
        "largest_post_bytes": int(row.get("largest_post_bytes") or 0),
    }

