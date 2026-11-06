"""floppy.io — 公開用ゲートウェイ (静的配信 + FastAPI プロキシ)

https://fdd.wawa-app.me/floppy.io/ を、このマシン上の

    frontend/dist            (Nuxt の静的ビルド)
    http://127.0.0.1:8001    (FastAPI / uvicorn)

で配信する。Cloudflare Tunnel の ingress から http://127.0.0.1:8899 へ
流すだけで、Apache / nginx の ProxyPass 相当の構成になる。

    /floppy.io/            -> frontend/dist/index.html
    /floppy.io/_nuxt/...   -> frontend/dist/_nuxt/...
    /floppy.io/u/name      -> frontend/dist/index.html (履歴モードの SPA フォールバック)
    /floppy.io/p/12        -> frontend/dist/index.html (履歴モードの SPA フォールバック)
    /floppy.io/api/...     -> FastAPI /api/...
    /floppy.io/uploads/... -> FastAPI /uploads/...

起動 / 停止は tools/public.sh を使う:
    ./tools/public.sh start | stop | status

環境変数:
    FLOPPY_API_URL   転送先 (既定 http://127.0.0.1:8001)
    FLOPPY_WEB_PORT  待ち受けポート (既定 8899)
"""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse, Response
from starlette.routing import Route

BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = (BASE_DIR / "frontend" / "dist").resolve()

API_URL = os.getenv("FLOPPY_API_URL", "http://127.0.0.1:8001").rstrip("/")
WEB_PORT = int(os.getenv("FLOPPY_WEB_PORT", "8899"))
PREFIX = "/floppy.io"

# 上流にそのまま渡さないヘッダー
_HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
    "content-encoding",
}

_client = httpx.AsyncClient(base_url=API_URL, timeout=30.0)


def _safe_dist_path(rel: str) -> Path | None:
    """dist 配下に収まるパスだけ返す (パストラバーサル対策)"""
    if not rel or rel.endswith("/"):
        rel = rel + "index.html"
    candidate = (DIST_DIR / rel).resolve()
    try:
        candidate.relative_to(DIST_DIR)
    except ValueError:
        return None
    return candidate


async def _serve_static(path: str) -> Response:
    target = _safe_dist_path(path)
    if target and target.is_file():
        media_type, _ = mimetypes.guess_type(str(target))
        return FileResponse(target, media_type=media_type)

    # 履歴モードの SPA フォールバック:
    # /u/name や /p/12 のような拡張子のないパスは index.html を返す。
    # _nuxt/*.js などの実ファイル要求は 404 にして、HTML を JS として
    # 返してしまわないようにする。
    if Path(path).suffix:
        return Response(
            "Not Found",
            status_code=404,
            media_type="text/plain; charset=utf-8",
        )

    index = DIST_DIR / "index.html"
    if index.is_file():
        return FileResponse(
            index,
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-cache"},
        )

    return Response("frontend/dist がありません。npm run build を実行してください。", 503)


async def _proxy(request: Request, upstream_path: str) -> Response:
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in _HOP_BY_HOP
    }
    headers["X-Forwarded-Host"] = request.headers.get("host", "")
    headers["X-Forwarded-Proto"] = request.url.scheme

    body = await request.body()

    try:
        upstream = await _client.request(
            request.method,
            upstream_path,
            params=request.query_params,
            headers=headers,
            content=body,
        )
    except httpx.RequestError:
        return Response(
            "API に接続できません。",
            status_code=502,
            media_type="text/plain; charset=utf-8",
        )

    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower() not in _HOP_BY_HOP
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


async def root(request: Request) -> Response:
    return RedirectResponse(f"{PREFIX}/", status_code=301)


async def floppy_root(request: Request) -> Response:
    return RedirectResponse(f"{PREFIX}/", status_code=301)


async def floppy(request: Request) -> Response:
    path = request.path_params.get("path", "")

    # API / アップロード画像は FastAPI へ
    if path == "api" or path.startswith("api/"):
        return await _proxy(request, "/" + path)
    if path == "uploads" or path.startswith("uploads/"):
        return await _proxy(request, "/" + path)

    # それ以外は frontend/dist の静的ファイル
    return await _serve_static(path)


app = Starlette(
    routes=[
        Route("/", root, methods=["GET", "HEAD"]),
        Route(PREFIX, floppy_root, methods=["GET", "HEAD"]),
        Route(
            PREFIX + "/{path:path}",
            floppy,
            methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        ),
    ]
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=WEB_PORT, log_level="info")
