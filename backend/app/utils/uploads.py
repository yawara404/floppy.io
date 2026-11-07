"""floppy.io — アップロード保存 / URL / 添付ファイル"""

from __future__ import annotations

import re
import secrets
from pathlib import Path
from urllib.parse import quote, urlparse

from fastapi import Request

from ..config import DISK_LIMIT_BYTES, PUBLIC_BASE_URL, UPLOAD_DIR

PLAYABLE_AUDIO_EXT = {
    "mp3",
    "wav",
    "ogg",
    "oga",
    "opus",
    "m4a",
    "aac",
    "flac",
    "weba",
}

AUDIO_CONTENT_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "oga": "audio/ogg",
    "opus": "audio/ogg",
    "m4a": "audio/mp4",
    "aac": "audio/mp4",
    "flac": "audio/flac",
    "weba": "audio/webm",
}

IMAGE_CONTENT_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "webp": "image/webp",
}

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def ensure_upload_dir() -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOAD_DIR


def safe_filename(name: str) -> str:
    cleaned = str(name or "").replace("\\", "/").replace("\0", "").split("/")[-1].strip()
    return cleaned[:255] or "floppy.bin"


def save_upload(data: bytes, ext: str) -> str:
    directory = ensure_upload_dir()
    safe_ext = re.sub(r"[^a-z0-9]", "", str(ext).lower()) or "bin"
    name = f"{secrets.token_hex(16)}.{safe_ext}"
    (directory / name).write_bytes(data)
    return name


def delete_upload(name: str | None) -> None:
    if not name:
        return
    safe = Path(str(name)).name
    if safe in ("", ".", ".."):
        return
    try:
        (UPLOAD_DIR / safe).unlink(missing_ok=True)
    except OSError:
        pass


def floppy_kind(name: str) -> str:
    ext = Path(str(name)).suffix.lstrip(".").lower()
    return "audio" if ext in PLAYABLE_AUDIO_EXT else "file"


def floppy_store_ext(name: str) -> str:
    ext = Path(str(name)).suffix.lstrip(".").lower()
    return ext if ext in PLAYABLE_AUDIO_EXT else "bin"


def content_type_for(name: str) -> str:
    ext = Path(str(name)).suffix.lstrip(".").lower()
    return (
        IMAGE_CONTENT_TYPES.get(ext)
        or AUDIO_CONTENT_TYPES.get(ext)
        or "application/octet-stream"
    )


def is_image_ext(name: str) -> bool:
    return Path(str(name)).suffix.lstrip(".").lower() in IMAGE_CONTENT_TYPES


def is_audio_ext(name: str) -> bool:
    return Path(str(name)).suffix.lstrip(".").lower() in AUDIO_CONTENT_TYPES


def upload_exists(name: str | None) -> bool:
    """DB に記録されたファイルが実在するか"""
    if not name:
        return False
    safe = Path(str(name)).name
    if safe in ("", ".", ".."):
        return False
    try:
        return (UPLOAD_DIR / safe).is_file()
    except OSError:
        return False


def public_base_path() -> str:
    """公開 URL のパス部分 (例: /floppy.io/)。

    PUBLIC_BASE_URL が未設定ならルート配信とみなす。
    """
    if PUBLIC_BASE_URL:
        path = urlparse(PUBLIC_BASE_URL).path or "/"
        return path if path.endswith("/") else path + "/"
    return "/"


def upload_url(name: str | None) -> str | None:
    """DB のファイル名 → ブラウザ用の URL

    以前は './uploads/xxx' という相対 URL を返していたが、SPA の
    /u/name や /p/12 では '/u/uploads/xxx' に解決されて 404 になっていた。
    アプリの baseURL を前置した絶対パスを返す。
    実ファイルが無い場合も None を返し、壊れた画像アイコンを出さない。
    """
    if not upload_exists(name):
        return None
    return f"{public_base_path()}uploads/{quote(str(name))}"


def absolute_base(request: Request) -> str:
    """埋め込み HTML 用の絶対 URL ベース"""
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL.rstrip("/") + "/"
    return str(request.base_url)


def absolute_upload_url(request: Request, name: str | None) -> str | None:
    if not upload_exists(name):
        return None
    return f"{absolute_base(request)}uploads/{quote(str(name))}"


def validate_floppy_filename(name: str) -> bool:
    return bool(_SAFE_NAME_RE.match(name))


def validate_floppy_data(data: bytes, filename: str) -> tuple[dict | None, str | None]:
    if not data:
        return None, "ファイルが空です。"

    if len(data) > DISK_LIMIT_BYTES:
        return None, "フロッピーファイルは 1.44MB 以内にしてください。"

    return {
        "bytes": len(data),
        "name": safe_filename(filename),
    }, None
