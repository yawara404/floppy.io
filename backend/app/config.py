# floppy.io — FastAPI 設定
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DISK_LIMIT_BYTES = 1_474_560

DB_HOST = os.getenv("FLOPPY_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("FLOPPY_DB_PORT", "3306"))
DB_NAME = os.getenv("FLOPPY_DB_NAME", "floppy_io")
DB_USER = os.getenv("FLOPPY_DB_USER", "floppy")
DB_PASS = os.getenv("FLOPPY_DB_PASS", "floppy")

UPLOAD_DIR = Path(
    os.getenv("FLOPPY_UPLOAD_DIR", str(BASE_DIR / "uploads"))
).resolve()

YOUTUBE_API_KEY = os.getenv("FLOPPY_YOUTUBE_API_KEY", "")

# API ドキュメント (/api/docs) は既定で無効。開発時のみ 1 にする。
API_DOCS_ENABLED = os.getenv("FLOPPY_API_DOCS", "0") == "1"

# API トークンの有効期限 (日)。0 は無期限。
TOKEN_TTL_DAYS = int(os.getenv("FLOPPY_TOKEN_TTL_DAYS", "0"))

# 埋め込み HTML に入れる絶対 URL のベース。
# 例: https://fdd.wawa-app.me/floppy.io/
PUBLIC_BASE_URL = os.getenv("FLOPPY_PUBLIC_BASE_URL", "").strip()

# 開発時に別オリジンのフロントエンドから叩けるようにする
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("FLOPPY_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]

MAX_UPLOAD_BYTES = DISK_LIMIT_BYTES
