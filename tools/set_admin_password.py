#!/usr/bin/env python3
"""floppy.io 公式アカウントのパスワード設定 & 隠しファイルメモ作成"""

import hashlib
import os
import secrets
from pathlib import Path

import bcrypt
import pymysql
from pymysql.cursors import DictCursor

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
SECRET_FILE = BASE_DIR / ".floppy_admin.secret"

ENV_FILE = BACKEND_DIR / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

DB_HOST = os.getenv("FLOPPY_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("FLOPPY_DB_PORT", "3306"))
DB_NAME = os.getenv("FLOPPY_DB_NAME", "floppy_io")
DB_USER = os.getenv("FLOPPY_DB_USER", "floppy")
DB_PASS = os.getenv("FLOPPY_DB_PASS", "floppy")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def main():
    # わかりやすく安全なパスワード
    # 例: floppy_2026_admin または ランダム文字列
    random_part = secrets.token_hex(4)
    admin_password = f"floppy_admin_{random_part}"
    password_hash = hash_password(admin_password)

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )

    try:
        with conn.cursor() as cur:
            # floppy アカウントのパスワード更新
            cur.execute(
                """UPDATE users
                   SET password_hash = %s,
                       display_name = 'floppy.io'
                   WHERE id = 1 OR username = 'floppy'""",
                (password_hash,),
            )
            
            # APIトークンも発行
            api_token = secrets.token_hex(32)
            cur.execute(
                "INSERT INTO api_tokens (user_id, token) VALUES (1, %s)",
                (hash_token(api_token),),
            )

        # 隠しファイルにメモを保存
        memo_content = f"""# floppy.io 公式アカウント情報（管理者用メモ）
# ※ このファイルは隠しファイル (.floppy_admin.secret) であり、.gitignore により Git 対象外です。

[アカウント情報]
ユーザーID: 1
表示名: floppy.io
ユーザー名 (ログインID): floppy （または floppy.io）
パスワード: {admin_password}

[API トークン (Bearer)]
トークン: {api_token}

[ログインURL]
ローカル環境: http://localhost:3000/login (または設定中のポート)
公開環境: https://fdd.wawa-app.me/floppy.io/login
"""
        SECRET_FILE.write_text(memo_content, encoding="utf-8")
        # 権限を 600 に設定
        os.chmod(SECRET_FILE, 0o600)

        print("=== floppy.io 公式アカウント情報を設定しました ===")
        print(f"ユーザー名: floppy (または floppy.io)")
        print(f"表示名: floppy.io")
        print(f"パスワード: {admin_password}")
        print(f"メモ保存先: {SECRET_FILE}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

