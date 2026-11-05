"""floppy.io — アップロード配信"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import UPLOAD_DIR
from ..utils.uploads import content_type_for, is_audio_ext, is_image_ext

router = APIRouter(tags=["uploads"])

NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@router.get("/uploads/{name}")
def read_upload(name: str) -> FileResponse:
    if not NAME_RE.fullmatch(name):
        raise HTTPException(404, "Not Found")

    path = UPLOAD_DIR / Path(name).name
    if not path.is_file():
        raise HTTPException(404, "Not Found")

    inline = is_image_ext(name) or is_audio_ext(name)
    disposition = "inline" if inline else "attachment"

    return FileResponse(
        path,
        media_type=content_type_for(name),
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''{name}"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cross-Origin-Resource-Policy": "cross-origin",
        },
    )
