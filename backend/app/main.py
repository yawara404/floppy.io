"""floppy.io — FastAPI アプリ

起動:
  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import shutil
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymysql import MySQLError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .config import API_DOCS_ENABLED, CORS_ORIGINS, DISK_LIMIT_BYTES
from .db import fetch_all, fetch_one
from .routers import auth, posts, social, uploads, users
from .utils.uploads import ensure_upload_dir

logger = logging.getLogger("floppy.io")

STARTED_AT = time.time()

# ディスク残量がこれを下回ったら警告する（アップロード失敗 / MySQL 破損の前兆）
DISK_FREE_WARN_BYTES = 100 * 1024 * 1024

# 認証 (public_user) や一覧取得が参照するテーブル。
# 旧 PHP 版の DB をそのまま使うと follows が無く、ログイン / 新規登録が
# 一律 503 になるため、起動時に不足を検知してログに出す。
REQUIRED_TABLES = ("users", "api_tokens", "posts", "likes", "follows")

# MySQL のエラーコード
ER_NO_SUCH_TABLE = 1146
ER_BAD_FIELD_ERROR = 1054

SCHEMA_HINT = (
    "データベースのテーブル構成が古い可能性があります。"
    "database/schema.sql を適用してください"
    "（例: mysql -u root -p < database/schema.sql）。"
)


def _mysql_error_code(exc: MySQLError) -> int | None:
    if exc.args and isinstance(exc.args[0], int):
        return exc.args[0]
    return None


def _missing_tables() -> list[str]:
    """接続できる範囲で、不足しているテーブル名を返す"""
    try:
        rows = fetch_all("SHOW TABLES")
    except MySQLError:
        # DB 自体に接続できない場合はここでは何もしない（/api/health で確認できる）
        return []

    present = {str(value) for row in rows for value in row.values()}
    return [name for name in REQUIRED_TABLES if name not in present]


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = _missing_tables()
    if missing:
        logger.warning(
            "未作成のテーブルがあります: %s — database/schema.sql を適用してください"
            "（mysql -u root -p < database/schema.sql）。"
            "この状態ではログイン / 新規登録が 503 になります。",
            ", ".join(missing),
        )
    yield


app = FastAPI(
    title="floppy.io API",
    version="2.0.0",
    docs_url="/api/docs" if API_DOCS_ENABLED else None,
    openapi_url="/api/openapi.json" if API_DOCS_ENABLED else None,
    redoc_url=None,
    lifespan=lifespan,
)

MAX_REQUEST_BYTES = DISK_LIMIT_BYTES * 2 + 1024 * 1024


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=()",
        )
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        if request.url.path.startswith("/api"):
            response.headers.setdefault("Cache-Control", "no-store")
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api"):
            length = request.headers.get("content-length", "")
            if length.isdigit() and int(length) > MAX_REQUEST_BYTES:
                return JSONResponse(
                    {"error": "リクエストが大きすぎます。"},
                    status_code=413,
                )
        return await call_next(request)


app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS or ["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """フロントエンドが読む data.error 形式に統一する"""
    return JSONResponse(
        {"error": exc.detail},
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        {"error": "入力内容が不正です。", "details": exc.errors()},
        status_code=422,
    )


@app.exception_handler(MySQLError)
async def database_exception_handler(request: Request, exc: MySQLError):
    # 「接続できない」のか「テーブル / カラムが古い」のかを切り分けて返す。
    # 旧 PHP 版の DB をそのまま使うと follows が無く、ログイン・登録が
    # どちらも失敗するため、復旧手順まで案内する。
    if _mysql_error_code(exc) in (ER_NO_SUCH_TABLE, ER_BAD_FIELD_ERROR):
        return JSONResponse({"error": SCHEMA_HINT}, status_code=503)

    return JSONResponse(
        {"error": "データベースに接続できません。MySQL の起動と設定を確認してください。"},
        status_code=503,
    )


@app.get("/api/health")
def health() -> JSONResponse:
    """死活監視用。

    異常時は 503 を返すので、監視側はステータスコードだけでも判定できる。
    本文には復旧の手がかり（DB / スキーマ / ディスク / 稼働時間）を含める。
    """
    database_ok = True
    missing: list[str] = []

    try:
        row = fetch_one("SELECT 1 AS ok")
        database_ok = bool(row and row.get("ok") == 1)
        missing = _missing_tables()
    except MySQLError:
        database_ok = False

    disk_free_bytes = 0
    disk_total_bytes = 0
    disk_low = False
    try:
        usage = shutil.disk_usage(ensure_upload_dir())
        disk_free_bytes = usage.free
        disk_total_bytes = usage.total
        disk_low = usage.free < DISK_FREE_WARN_BYTES
    except OSError:
        # アップロード先が無い / 読めない場合も「異常」として扱う
        disk_low = True

    warnings: list[str] = []
    if not database_ok:
        warnings.append("database_unreachable")
    if missing:
        warnings.append("missing_tables")
    if disk_low:
        warnings.append("disk_space_low")

    healthy = database_ok and not missing and not disk_low

    return JSONResponse(
        {
            "ok": healthy,
            "service": "floppy.io-api",
            "version": "2.0.0",
            "limit_bytes": DISK_LIMIT_BYTES,
            "database": database_ok,
            "missing_tables": missing,
            "disk_free_bytes": disk_free_bytes,
            "disk_total_bytes": disk_total_bytes,
            "uptime_seconds": int(time.time() - STARTED_AT),
            "warnings": warnings,
        },
        status_code=200 if healthy else 503,
        headers={"Cache-Control": "no-store"},
    )


app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(social.router)
app.include_router(uploads.router)
