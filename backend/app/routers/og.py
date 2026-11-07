"""floppy.io — 投稿別 OGP (Twitter / SNS クローラー向け)

SPA のままではクローラーが投稿本文を読めないため、Twitterbot などの
User-Agent のときだけ、この HTML を公開ゲートウェイ経由で返す。
人間のブラウザには従来どおり frontend/dist の SPA を返す。
"""

from __future__ import annotations

import html
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..db import fetch_one
from ..utils.og_image import render_pixel_card_png
from ..utils.pixels import is_blank_pixel
from ..utils.uploads import absolute_base, absolute_upload_url

router = APIRouter(prefix="/api", tags=["og"])

POST_SQL = """SELECT p.id,
                     p.text,
                     p.pixel_data,
                     p.pixel_width,
                     p.pixel_height,
                     p.image_path,
                     p.youtube_id,
                     p.youtube_title,
                     p.youtube_thumbnail,
                     p.created_at,
                     u.username,
                     u.display_name,
                     d.name AS disk_name
                FROM posts p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN disks d ON d.id = p.disk_id
               WHERE p.id = %s"""

_URL_RE = re.compile(r"https?://\S+")
_SPACE_RE = re.compile(r"\s+")

OG_HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Vary": "User-Agent",
    "X-Robots-Tag": "noindex",
}


def _esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _truncate(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _description_text(value: object) -> str:
    text = _URL_RE.sub(" ", str(value or ""))
    return _SPACE_RE.sub(" ", text).strip()


def _post_kind(row: dict) -> str:
    if row.get("youtube_id"):
        return "YouTube"
    if row.get("image_path"):
        return "画像"
    if not is_blank_pixel(str(row.get("pixel_data") or "")):
        return "ドット絵"
    return "テキスト"


def _youtube_thumb(row: dict) -> str:
    video_id = str(row.get("youtube_id") or "")
    if not video_id:
        return ""

    # DB のサムネイルは mqdefault (320×180) のことがあるため、
    # OGP では確実に存在する hqdefault (480×360) を使う。
    return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"


def _post_image(request: Request, row: dict, post_id: int) -> tuple[str, str]:
    """(画像URL, サイズ指定の meta HTML)

    共有カードと同じく YouTube > 画像 > ドット絵 > サイト共通カードの順。
    """
    base = absolute_base(request)

    thumb = _youtube_thumb(row)
    if thumb:
        return thumb, ""

    image_url = absolute_upload_url(request, row.get("image_path"))
    if image_url:
        return image_url, ""

    if not is_blank_pixel(str(row.get("pixel_data") or "")):
        image_url = f"{base}api/og/post/{post_id}/image.png"
        return image_url, (
            '<meta property="og:image:width" content="1200">'
            '<meta property="og:image:height" content="630">'
            '<meta property="og:image:type" content="image/png">'
        )

    image_url = f"{base}card.png"
    return image_url, (
        '<meta property="og:image:width" content="1200">'
        '<meta property="og:image:height" content="630">'
        '<meta property="og:image:type" content="image/png">'
    )


def _published_time(value: object) -> str:
    raw = str(value or "")
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return ""
    return f"{parsed:%Y-%m-%dT%H:%M:%S}+09:00"


@router.get("/og/post/{post_id}", response_class=HTMLResponse)
def post_og(request: Request, post_id: int) -> HTMLResponse:
    """投稿 1 件分の OGP メタだけを持つ軽量 HTML"""
    row = fetch_one(POST_SQL, (post_id,))
    if not row:
        return HTMLResponse(
            '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
            "<title>投稿が見つかりません — floppy.io</title></head>"
            "<body><p>投稿が見つかりません。</p></body></html>",
            status_code=404,
            headers=OG_HEADERS,
        )

    base = absolute_base(request)
    post_url = f"{base}p/{post_id}"

    author = str(row["username"])
    shown = str(row["display_name"] or row["username"])
    kind = _post_kind(row)
    title = _truncate(f"No.{post_id} {shown} (@{author}) — floppy.io", 100)

    parts: list[str] = []
    if row.get("disk_name"):
        parts.append(f"[D] {row['disk_name']}")
    text = _description_text(row.get("text"))
    if text:
        parts.append(text)
    else:
        parts.append(f"{kind}の投稿")
    description = _truncate(" · ".join(parts), 180)

    image_url, image_meta = _post_image(request, row, post_id)
    image_alt = _truncate(f"{shown} の投稿 No.{post_id}", 100)
    published = _published_time(row.get("created_at"))

    meta = [
        f'<meta name="description" content="{_esc(description)}">',
        '<meta property="og:type" content="article">',
        '<meta property="og:site_name" content="floppy.io">',
        '<meta property="og:locale" content="ja_JP">',
        f'<meta property="og:title" content="{_esc(title)}">',
        f'<meta property="og:description" content="{_esc(description)}">',
        f'<meta property="og:url" content="{_esc(post_url)}">',
        f'<meta property="og:image" content="{_esc(image_url)}">',
        f'<meta property="og:image:secure_url" content="{_esc(image_url)}">',
        f'<meta property="og:image:alt" content="{_esc(image_alt)}">',
        image_meta,
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{_esc(title)}">',
        f'<meta name="twitter:description" content="{_esc(description)}">',
        f'<meta name="twitter:image" content="{_esc(image_url)}">',
        f'<meta name="twitter:image:alt" content="{_esc(image_alt)}">',
        f'<meta name="twitter:url" content="{_esc(post_url)}">',
        '<meta name="robots" content="noindex">',
        f'<link rel="canonical" href="{_esc(post_url)}">',
    ]
    if published:
        meta.append(
            f'<meta property="article:published_time" content="{_esc(published)}">'
        )

    document = (
        '<!doctype html><html lang="ja"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_esc(title)}</title>"
        + "".join(meta)
        + "</head><body>"
        f'<p><a href="{_esc(post_url)}">{_esc(title)}</a></p>'
        f"<p>{_esc(description)}</p>"
        "</body></html>"
    )

    return HTMLResponse(document, headers=OG_HEADERS)


@router.get("/og/post/{post_id}/image.png")
def post_og_image(request: Request, post_id: int) -> Response:
    """投稿別の OGP 画像。

    画像 / YouTube はその画像へリダイレクトし、ドット絵は 1200×630 の
    PNG をその場で生成する。
    """
    row = fetch_one(
        """SELECT pixel_data, pixel_width, pixel_height,
                  image_path, youtube_id, youtube_thumbnail
             FROM posts WHERE id = %s""",
        (post_id,),
    )
    if not row:
        raise HTTPException(404, "投稿が見つかりません。")

    thumb = _youtube_thumb(row)
    if thumb:
        return RedirectResponse(thumb, status_code=302)

    image_url = absolute_upload_url(request, row.get("image_path"))
    if image_url:
        return RedirectResponse(image_url, status_code=302)

    png = render_pixel_card_png(
        row.get("pixel_data"),
        row.get("pixel_width"),
        row.get("pixel_height"),
    )
    return Response(
        content=png,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )
