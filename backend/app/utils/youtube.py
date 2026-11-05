"""floppy.io — YouTube 連携 (Data API v3 は任意)"""

from __future__ import annotations

import re
from urllib.parse import quote

import httpx

from ..config import YOUTUBE_API_KEY

_VIDEO_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:[^\s]*&)?v=|embed/|shorts/|v/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})",
    re.IGNORECASE,
)


def youtube_video_id(text: str) -> str | None:
    match = _VIDEO_RE.search(text or "")
    return match.group(1) if match else None


def youtube_thumbnail_url(video_id: str) -> str:
    return f"https://i.ytimg.com/vi/{quote(video_id)}/hqdefault.jpg"


async def _fetch_metadata(video_id: str) -> dict[str, str] | None:
    if not YOUTUBE_API_KEY:
        return None

    url = (
        "https://www.googleapis.com/youtube/v3/videos?part=snippet&id="
        + quote(video_id)
        + "&key="
        + quote(YOUTUBE_API_KEY)
    )

    try:
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    items = data.get("items") or []
    if not items:
        return None

    snippet = items[0].get("snippet") or {}
    thumbs = snippet.get("thumbnails") or {}
    thumbnail = (
        (thumbs.get("medium") or {}).get("url")
        or (thumbs.get("high") or {}).get("url")
        or (thumbs.get("default") or {}).get("url")
        or ""
    )

    return {
        "title": str(snippet.get("title") or ""),
        "thumbnail": str(thumbnail),
    }


async def youtube_embed_info(text: str) -> dict[str, str]:
    video_id = youtube_video_id(text)
    if not video_id:
        return {"id": "", "title": "", "thumbnail": ""}

    metadata = await _fetch_metadata(video_id)

    return {
        "id": video_id,
        "title": (metadata or {}).get("title", "")[:255],
        "thumbnail": (metadata or {}).get("thumbnail")
        or youtube_thumbnail_url(video_id),
    }
