"""floppy.io — 投稿 API"""

from __future__ import annotations

import html
import re
from datetime import datetime
import subprocess
import sys
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from ..config import DISK_LIMIT_BYTES
from ..db import execute, fetch_all, fetch_one
from ..disks import attach_disks
from ..posts import POST_COLUMNS, attach_likes, attach_reply_counts, with_media
from ..security import current_user, require_user
from ..utils.images import validate_image_data
from ..utils.pixels import (
    is_blank_pixel,
    normalize_canvas_size,
    normalize_pixel,
    pixel_svg,
)
from ..utils.sql import like_escape
from ..utils.uploads import (
    absolute_base,
    absolute_upload_url,
    delete_upload,
    floppy_kind,
    floppy_store_ext,
    save_upload,
    validate_floppy_data,
)
from ..utils.youtube import youtube_embed_info

router = APIRouter(prefix="/api", tags=["posts"])

_last_bot_trigger_time = 0.0
_BOT_TRIGGER_INTERVAL = 30.0  # 30秒に1回までバックグラウンドで自動投稿/返信をチェック

def maybe_trigger_bot_background() -> None:
    global _last_bot_trigger_time
    now = time.monotonic()
    if now - _last_bot_trigger_time < _BOT_TRIGGER_INTERVAL:
        return
    _last_bot_trigger_time = now

    root_dir = Path(__file__).resolve().parent.parent.parent
    bot_script = root_dir / "tools" / "bot.py"
    if bot_script.exists():
        try:
            subprocess.Popen(
                [sys.executable, str(bot_script), "auto"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception:
            pass



# 埋め込みカード用: 本文中の URL をリンクにする（HTML は必ずエスケープする）
_URL_RE = re.compile(r"(https?://[^\s<]+)")


def format_card_text(value: str) -> str:
    normalized = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    parts = _URL_RE.split(normalized)
    pieces: list[str] = []

    for index, part in enumerate(parts):
        if index % 2:
            href = html.escape(part, quote=True)
            # X と同じように、表示はスキームを省いて長い URL を省略する
            label = part.replace("https://", "").replace("http://", "")
            if len(label) > 36:
                label = label[:36] + "…"
            label = html.escape(label)
            pieces.append(
                f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
                'style="color:#1d9bf0;text-decoration:none">'
                f"{label}</a>"
            )
        else:
            pieces.append(html.escape(part).replace("\n", "<br>"))

    return "".join(pieces)


def format_card_time(value: object) -> tuple[str, str]:
    """'YYYY-MM-DD HH:MM:SS' → (HH:MM, YYYY年M月D日)"""
    raw = str(value or "")

    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return "", raw

    return f"{parsed:%H:%M}", f"{parsed.year}年{parsed.month}月{parsed.day}日"


def media_card_html(image_html: str, caption: str = "") -> str:
    """サイトの投稿と同じ、ドット枠のメディアブロック"""
    caption_html = (
        '<div style="margin-top:4px;font-family:'
        "'IBM Plex Mono',ui-monospace,monospace;font-size:10px;"
        f'color:#6b6f63">{caption}</div>'
        if caption
        else ""
    )

    return (
        '<div style="margin-top:10px;border:2px solid #23262b;'
        'background:#ffffff;line-height:0;overflow:hidden">'
        f"{image_html}</div>{caption_html}"
    )


@router.get("/posts")
def list_posts(
    request: Request,
    username: str = "",
    q: str = "",
    feed: str = "",
    disk: str = "",
    bot: str = "",
) -> dict:
    maybe_trigger_bot_background()
    username = username.strip()
    keyword = q.strip()
    disk_slug = disk.strip().lower()
    bot_filter = bot.strip().lower()

    sql = f"""SELECT {POST_COLUMNS}
                FROM posts p
                JOIN users u ON u.id = p.user_id"""
    where: list[str] = []
    params: list[object] = []

    # 返信はスレッドページ（/api/thread）でのみ表示する
    where.append("p.reply_to_id IS NULL")

    # bot フィルター (bot=0 / bot=false: bot除外, bot=only: botのみ)
    bot_names = ("hagumeta", "heisei_vipper", "adachi_rei")
    if bot_filter in ("0", "false", "off", "no"):
        placeholders = ",".join(["%s"] * len(bot_names))
        where.append(f"u.username NOT IN ({placeholders})")
        params.extend(bot_names)
    elif bot_filter in ("only", "1", "bot"):
        if bot_filter == "only":
            placeholders = ",".join(["%s"] * len(bot_names))
            where.append(f"u.username IN ({placeholders})")
            params.extend(bot_names)

    if username:
        where.append("u.username = %s")
        params.append(username)

    # ディスク (コミュニティ) の書き込みだけを返す
    if disk_slug:
        where.append("p.disk_id = (SELECT id FROM disks WHERE slug = %s)")
        params.append(disk_slug)

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
    posts = attach_disks(
        attach_reply_counts(
            attach_likes([with_media(row) for row in rows], current_user(request))
        )
    )
    return {"posts": posts}


@router.post("/posts", status_code=status.HTTP_201_CREATED)
async def create_post(request: Request) -> dict:
    user = require_user(request)
    maybe_trigger_bot_background()

    content_type = request.headers.get("content-type", "")
    is_multipart = content_type.startswith("multipart/form-data")

    text = ""
    pixel_raw = ""
    pixel_width_raw = ""
    pixel_height_raw = ""
    reply_raw = ""
    disk_raw = ""
    image_file = None
    floppy_file = None

    if is_multipart:
        form = await request.form()
        text = str(form.get("text") or "")
        pixel_raw = str(form.get("pixel_data") or "")
        pixel_width_raw = str(form.get("pixel_width") or "")
        pixel_height_raw = str(form.get("pixel_height") or "")
        reply_raw = str(form.get("reply_to_id") or "")
        disk_raw = str(form.get("disk_id") or "")
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
            pixel_width_raw = str(payload.get("pixel_width") or "")
            pixel_height_raw = str(payload.get("pixel_height") or "")
            reply_raw = str(payload.get("reply_to_id") or "")
            disk_raw = str(payload.get("disk_id") or "")

    # キャンバスは 16×16 / 32×32 / 32×24 のいずれか（不正なら 16×16）
    pixel_width, pixel_height = normalize_canvas_size(
        pixel_width_raw or 16, pixel_height_raw or 16
    )
    pixel_bytes = pixel_width * pixel_height
    pixel = normalize_pixel(pixel_raw, pixel_width, pixel_height)

    # 返信先（0 / 空は通常投稿）。返信への返信も同じスレッドにまとめるため、
    # 実際に保存するのはスレッドのルート投稿 ID になる。
    reply_target_id = 0
    if reply_raw.strip():
        try:
            reply_target_id = int(reply_raw.strip())
        except (TypeError, ValueError):
            raise HTTPException(400, "返信先の投稿 ID が不正です。") from None
        if reply_target_id <= 0:
            raise HTTPException(400, "返信先の投稿 ID が不正です。")

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

    # 返信先の検証。返信を受け付ける設定（allow_replies）がオフの投稿には
    # 返信できない。既定はオフなので、本人が設定でオンにした投稿だけが対象。
    reply_root_id: int | None = None
    if reply_target_id:
        target = fetch_one(
            "SELECT id, reply_to_id FROM posts WHERE id = %s",
            (reply_target_id,),
        )
        if not target:
            raise HTTPException(404, "返信先の投稿が見つかりません。")

        # 返信への返信も同じスレッド（ルート投稿）にまとめる
        reply_root_id = int(target["reply_to_id"] or target["id"])

        root = fetch_one(
            """SELECT u.allow_replies
                 FROM posts p
                 JOIN users u ON u.id = p.user_id
                WHERE p.id = %s""",
            (reply_root_id,),
        )
        if not root:
            raise HTTPException(404, "返信先の投稿が見つかりません。")

        if not int(root.get("allow_replies") or 0):
            raise HTTPException(403, "この投稿は返信を受け付けていません。")

    # 書き込み先のディスク (コミュニティ)。返信はディスクに紐づけない。
    disk_id: int | None = None
    if disk_raw.strip() and not reply_root_id:
        try:
            disk_id = int(disk_raw.strip())
        except (TypeError, ValueError):
            raise HTTPException(400, "ディスク ID が不正です。") from None
        if disk_id <= 0:
            raise HTTPException(400, "ディスク ID が不正です。")

        if not fetch_one("SELECT id FROM disks WHERE id = %s", (disk_id,)):
            raise HTTPException(404, "ディスクが見つかりません。")

        # 書き込めるのは参加メンバーだけ（作成者は自動参加）
        if not fetch_one(
            "SELECT 1 AS found FROM disk_members WHERE disk_id = %s AND user_id = %s",
            (disk_id, int(user["id"])),
        ):
            raise HTTPException(403, "このディスクに参加すると書き込めます。")

    if not text and is_blank_pixel(pixel) and not image and not floppy:
        raise HTTPException(
            400,
            "本文・ドット絵・画像・フロッピーファイルのいずれかを入力してください。",
        )

    text_bytes = len(text.encode("utf-8"))
    image_bytes = len(image_data) if image else 0
    floppy_bytes = int(floppy["bytes"]) if floppy else 0
    total_bytes = text_bytes + pixel_bytes + image_bytes + floppy_bytes

    if total_bytes > DISK_LIMIT_BYTES:
        raise HTTPException(
            403,
            "1 投稿あたりの容量上限（1.44MB）を超えています。"
            f"（本文 {text_bytes:,} + ドット絵 {pixel_bytes}"
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
                (user_id, reply_to_id, disk_id, text, pixel_data,
                 pixel_width, pixel_height,
                 image_path, image_mime, image_bytes,
                 image_width, image_height, youtube_id, youtube_title, youtube_thumbnail,
                 floppy_path, floppy_name, floppy_bytes,
                 text_bytes, pixel_bytes, total_bytes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                int(user["id"]),
                reply_root_id,
                disk_id,
                text,
                pixel,
                pixel_width,
                pixel_height,
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
                pixel_bytes,
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
    posts = attach_disks(
        attach_reply_counts(attach_likes([with_media(row)], user))
    )

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

    # 返信はフラットなスレッド（reply_to_id = ルート投稿）なので、
    # ルート投稿を削除するときはスレッド内の返信も一緒に削除する。
    replies = fetch_all(
        "SELECT image_path, floppy_path FROM posts WHERE reply_to_id = %s",
        (post_id,),
    )
    execute("DELETE FROM posts WHERE reply_to_id = %s", (post_id,))
    for reply in replies:
        delete_upload(reply.get("image_path"))
        delete_upload(reply.get("floppy_path"))

    execute(
        "DELETE FROM posts WHERE id = %s AND user_id = %s",
        (post_id, int(user["id"])),
    )
    delete_upload(row.get("image_path"))
    delete_upload(row.get("floppy_path"))

    return {"deleted": post_id, "deleted_replies": len(replies)}


@router.get("/thread")
def thread(request: Request, id: int = 0) -> dict:
    """投稿 1 件とそのスレッド（返信一覧）を返す"""
    if id <= 0:
        raise HTTPException(400, "投稿 ID が不正です。")

    sql = f"""SELECT {POST_COLUMNS}
                FROM posts p
                JOIN users u ON u.id = p.user_id
               WHERE p.id = %s"""

    row = fetch_one(sql, (id,))
    if not row:
        raise HTTPException(404, "投稿が見つかりません。")

    # 返信の ID を指定された場合は、スレッドのルート投稿に寄せる
    root_id = int(row["reply_to_id"] or row["id"])
    if root_id != int(row["id"]):
        row = fetch_one(sql, (root_id,))
        if not row:
            raise HTTPException(404, "投稿が見つかりません。")

    replies = fetch_all(
        f"""SELECT {POST_COLUMNS}
              FROM posts p
              JOIN users u ON u.id = p.user_id
             WHERE p.reply_to_id = %s
             ORDER BY p.created_at ASC, p.id ASC""",
        (root_id,),
    )

    me = current_user(request)
    post = attach_disks(
        attach_reply_counts(attach_likes([with_media(row)], me))
    )[0]
    reply_list = attach_disks(
        attach_reply_counts(
            attach_likes([with_media(reply) for reply in replies], me)
        )
    )

    return {"post": post, "replies": reply_list}


@router.get("/preview")
def preview(request: Request, id: int = 0) -> dict:
    if id <= 0:
        raise HTTPException(400, "投稿 ID が不正です。")

    row = fetch_one(
        """SELECT p.id,
                  u.username,
                  u.display_name,
                  u.avatar_path,
                  p.text,
                  p.pixel_data,
                  p.pixel_width,
                  p.pixel_height,
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
                  p.disk_id,
                  d.name AS disk_name,
                  p.created_at,
                  (SELECT COUNT(*) FROM likes l WHERE l.post_id = p.id) AS like_count,
                  (SELECT COUNT(*) FROM posts r WHERE r.reply_to_id = p.id) AS reply_count
             FROM posts p
             JOIN users u ON u.id = p.user_id
             LEFT JOIN disks d ON d.id = p.disk_id
            WHERE p.id = %s""",
        (id,),
    )

    if not row:
        raise HTTPException(404, "投稿が見つかりません。")

    author = str(row["username"])
    shown = str(row["display_name"] or row["username"])
    text_html = format_card_text(str(row["text"] or ""))
    time_label, date_label = format_card_time(row.get("created_at"))
    like_count = int(row.get("like_count") or 0)
    reply_count = int(row.get("reply_count") or 0)
    post_url = f"{absolute_base(request)}p/{int(row['id'])}"

    pixel_width = int(row.get("pixel_width") or 16)
    pixel_height = int(row.get("pixel_height") or 16)
    svg = pixel_svg(str(row["pixel_data"]), pixel_width, pixel_height)

    # サイトの投稿カードと同じく、投稿のドット絵をアバターにする
    avatar_responsive = svg.replace(
        "<svg ",
        '<svg style="width:100%;height:100%;display:block" ',
        1,
    )
    avatar_html = (
        '<div style="flex:0 0 auto;width:44px;height:44px;'
        'border:1px solid #23262b;background:#ffffff;padding:2px;'
        'box-sizing:border-box;line-height:0;overflow:hidden">'
        f"{avatar_responsive}</div>"
    )

    image_url = absolute_upload_url(request, row.get("image_path"))
    floppy_url = absolute_upload_url(request, row.get("floppy_path"))

    # サイトの投稿と同じ優先順 (YouTube > 画像 > ドット絵)
    media_block = ""
    if row.get("youtube_id"):
        video_id = str(row["youtube_id"])
        thumb = str(
            row.get("youtube_thumbnail")
            or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        )
        title = html.escape(str(row.get("youtube_title") or "YouTube 動画"))
        video_url = html.escape(
            f"https://www.youtube.com/watch?v={video_id}", quote=True
        )
        media_block = media_card_html(
            f'<img src="{html.escape(thumb, quote=True)}" alt="" '
            'style="width:100%;max-height:320px;object-fit:cover;display:block">',
            f'<a href="{video_url}" target="_blank" rel="noopener noreferrer" '
            'style="color:#16538c;text-decoration:none">▶ '
            f"{title}</a>",
        )
    elif image_url:
        media_block = media_card_html(
            f'<img src="{html.escape(image_url, quote=True)}" alt="" '
            'style="width:100%;max-height:320px;object-fit:cover;display:block">',
        )
    elif not is_blank_pixel(str(row.get("pixel_data") or "")):
        responsive_svg = svg.replace(
            "<svg ",
            '<svg style="width:100%;height:auto;display:block" ',
            1,
        )
        media_block = media_card_html(
            f'<div style="padding:10px;background:#ffffff">{responsive_svg}</div>',
        )

    floppy_html = ""
    if floppy_url:
        floppy_name = html.escape(str(row.get("floppy_name") or "floppy.bin"))
        floppy_bytes = f"{int(row.get('floppy_bytes') or 0):,}"
        href = html.escape(floppy_url, quote=True)

        if row.get("floppy_name") and floppy_kind(str(row["floppy_name"])) == "audio":
            floppy_html = (
                '<div style="margin-top:10px;padding:8px 10px;'
                'border:1px solid #cec8b5;background:#f7f3e7;color:#23262b">'
                '<div style="font-family:'
                "'IBM Plex Mono',ui-monospace,monospace;font-size:10px\">"
                f"[♪] {floppy_name} · {floppy_bytes} bytes</div>"
                f'<audio controls preload="none" src="{href}" '
                'style="width:100%;margin-top:4px"></audio></div>'
            )
        else:
            floppy_html = (
                f'<a href="{href}" target="_blank" rel="noopener noreferrer" '
                'style="display:flex;align-items:center;gap:8px;margin-top:10px;'
                'padding:8px 10px;border:1px solid #cec8b5;background:#f7f3e7;'
                'color:#23262b;text-decoration:none;font-size:11px">'
                '<span style="font-family:ui-monospace,monospace;color:#c4661f">[F]</span>'
                f'<span><span style="display:block">{floppy_name}</span>'
                '<span style="display:block;font-family:ui-monospace,monospace;'
                f'font-size:9px;color:#6b6f63">{floppy_bytes} bytes</span></span></a>'
            )

    disk_suffix = (
        f" · [D] {html.escape(str(row['disk_name']))}"
        if row.get("disk_name")
        else ""
    )

    if row.get("youtube_id"):
        kind = "YOUTUBE"
    elif image_url:
        kind = "IMAGE"
    elif row.get("floppy_name"):
        kind = "AUDIO" if floppy_kind(str(row["floppy_name"])) == "audio" else "FILE"
    elif not is_blank_pixel(str(row.get("pixel_data") or "")):
        kind = "PIXEL"
    else:
        kind = "TEXT"

    bytes_label = f"{int(row['total_bytes']):,}"

    text_block = (
        '<div style="margin-top:10px;font-size:13px;line-height:1.8;'
        'white-space:pre-wrap;word-break:break-word">'
        f"{text_html}</div>"
        if text_html
        else ""
    )

    kind_html = (
        '<span style="flex:0 0 auto;padding:1px 5px;border:1px solid #cec8b5;'
        'background:#f7f3e7;color:#1d6540;font-family:'
        "'IBM Plex Mono',ui-monospace,monospace;font-size:8px;"
        f'letter-spacing:.04em">{kind}</span>'
    )

    card_html = (
        '<div style="max-width:420px;margin:0;background:#fffdf7;'
        'border:2px solid #23262b;box-shadow:4px 4px 0 #c9c3b1;'
        'color:#23262b;font-family:'
        "'Noto Sans JP','Hiragino Sans','Yu Gothic',sans-serif;"
        'line-height:1.7;text-align:left;box-sizing:border-box">'
        '<div style="display:flex;align-items:center;justify-content:space-between;'
        'gap:10px;padding:8px 12px;background:#cfe9d8;border-bottom:2px solid #174d35;'
        'color:#174d35;font-family:'
        "'IBM Plex Mono',ui-monospace,monospace;font-size:9px;letter-spacing:.06em\">"
        "<span>FLOPPY.IO / SHARED POST</span>"
        f"<span>No.{int(row['id'])}</span></div>"
        '<div style="padding:12px">'
        '<div style="display:flex;align-items:flex-start;gap:11px">'
        f"{avatar_html}"
        '<div style="flex:1 1 auto;min-width:0">'
        '<div style="font-family:'
        "'DotGothic16','Noto Sans JP',sans-serif;font-size:15px;"
        'font-weight:700;color:#1d6540;line-height:1.3">'
        f"{html.escape(shown)}</div>"
        '<div style="font-family:'
        "'IBM Plex Mono',ui-monospace,monospace;font-size:9px;color:#6b6f63\">"
        f"@{html.escape(author)}{disk_suffix}</div>"
        '<div style="font-family:'
        "'IBM Plex Mono',ui-monospace,monospace;font-size:8px;color:#6b6f63;"
        'margin-top:1px">'
        f"{date_label} {time_label} / {bytes_label} bytes</div>"
        "</div>"
        f"{kind_html}"
        "</div>"
        f"{text_block}{media_block}{floppy_html}"
        '<div style="margin-top:10px;padding-top:8px;border-top:1px dashed #cec8b5;'
        'display:flex;flex-wrap:wrap;align-items:center;gap:12px;font-family:'
        "'IBM Plex Mono',ui-monospace,monospace;font-size:9px;color:#6b6f63\">"
        f'<span style="color:#b83a63">♥ {like_count}</span>'
        f"<span>↩ {reply_count}</span>"
        f"<span>{bytes_label} bytes</span>"
        f'<a href="{html.escape(post_url, quote=True)}" target="_blank" '
        'rel="noopener noreferrer" style="color:#16538c;text-decoration:none;'
        'margin-left:auto">↗ 投稿を開く</a>'
        "</div></div></div>"
    )

    return {
        "type": "floppy_io:post",
        "version": "1.0",
        "id": int(row["id"]),
        "author": author,
        "author_name": shown,
        "like_count": like_count,
        "reply_count": reply_count,
        "post_url": post_url,
        "text": row["text"],
        "pixel_data": row["pixel_data"],
        "pixel_width": int(row.get("pixel_width") or 16),
        "pixel_height": int(row.get("pixel_height") or 16),
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

