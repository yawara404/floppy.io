"""floppy.io — FastAPI アプリ

起動:
  uvicorn app.main:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pymysql import MySQLError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from .config import API_DOCS_ENABLED, CORS_ORIGINS, DISK_LIMIT_BYTES
from .db import fetch_one
from .routers import auth, posts, social, uploads, users

app = FastAPI(
    title="floppy.io API",
    version="2.0.0",
    docs_url="/api/docs" if API_DOCS_ENABLED else None,
    openapi_url="/api/openapi.json" if API_DOCS_ENABLED else None,
    redoc_url=None,
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
    return JSONResponse(
        {"error": "データベースに接続できません。MySQL の起動と設定を確認してください。"},
        status_code=503,
    )


@app.get("/api/health")
def health() -> dict:
    row = fetch_one("SELECT 1 AS ok")
    return {
        "ok": bool(row and row.get("ok") == 1),
        "service": "floppy.io-api",
        "version": "2.0.0",
        "limit_bytes": DISK_LIMIT_BYTES,
    }


app.include_router(auth.router)
app.include_router(posts.router)
app.include_router(users.router)
app.include_router(social.router)
app.include_router(uploads.router)
