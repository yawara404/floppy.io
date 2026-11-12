#!/usr/bin/env python3
"""floppy.io — Ollama (Qwen) 自動コメント / 返信 Bot

はぐメタ (hagumeta) & 平成掲示板の住人 (heisei_vipper)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import secrets
import sys
import time
from pathlib import Path
from typing import Any

import bcrypt
import httpx
import pymysql
from pymysql.cursors import DictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("floppy_bot")

BASE_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = BASE_DIR / "backend"
TOOLS_DIR = BASE_DIR / "tools"
STATE_FILE = TOOLS_DIR / "bot_state.json"
CONFIG_FILE = TOOLS_DIR / "bot_config.json"

# .env から設定読み込み
ENV_FILE = BACKEND_DIR / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

DB_HOST = os.getenv("FLOPPY_DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("FLOPPY_DB_PORT", "3306"))
DB_NAME = os.getenv("FLOPPY_DB_NAME", "floppy_io")
DB_USER = os.getenv("FLOPPY_DB_USER", "floppy")
DB_PASS = os.getenv("FLOPPY_DB_PASS", "floppy")

API_BASE_URL = os.getenv("FLOPPY_API_BASE_URL", "http://127.0.0.1:8001/api")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


# ---------------------------------------------------------------------------
# ドット絵アイコン生成 (32x32 = 1024文字)
# ---------------------------------------------------------------------------
def generate_hagumeta_pixel() -> str:
    """はぐメタ風のドット絵アイコン (32x32)"""
    canvas = [['0' for _ in range(32)] for _ in range(32)]
    # 背景: 0 (白)
    for y in range(32):
        for x in range(32):
            canvas[y][x] = '0'

    # 頭部頂点
    for x in range(12, 20):
        canvas[6][x] = '3'
    for x in range(10, 22):
        canvas[7][x] = '1'
    canvas[7][9] = '3'; canvas[7][22] = '3'

    for x in range(8, 24):
        canvas[8][x] = '1'
    canvas[8][7] = '3'; canvas[8][24] = '3'

    # ハイライト
    canvas[7][12] = '0'; canvas[7][13] = '0'
    canvas[8][11] = '0'; canvas[8][12] = '0'; canvas[8][13] = '0'

    # 中段
    for y in range(9, 17):
        for x in range(6, 26):
            canvas[y][x] = '1'
        canvas[y][5] = '3'
        canvas[y][26] = '3'

    for y in range(9, 13):
        canvas[y][10] = '0'; canvas[y][11] = '0'

    # 目
    canvas[13][11] = '3'; canvas[13][12] = '3'
    canvas[14][11] = '3'; canvas[14][12] = '0'
    canvas[15][11] = '3'; canvas[15][12] = '3'

    canvas[13][19] = '3'; canvas[13][20] = '3'
    canvas[14][19] = '0'; canvas[14][20] = '3'
    canvas[15][19] = '3'; canvas[15][20] = '3'

    # 口
    canvas[16][15] = '3'; canvas[16][16] = '3'

    # 下部の広がり
    for y in range(17, 24):
        left_bound = max(1, 6 - (y - 16) * 1)
        right_bound = min(30, 26 + (y - 16) * 1)
        for x in range(left_bound, right_bound + 1):
            canvas[y][x] = '1'
        canvas[y][left_bound] = '3'
        canvas[y][right_bound] = '3'

    for x in range(2, 30):
        canvas[24][x] = '2'
        canvas[25][x] = '3'
    canvas[24][1] = '3'; canvas[24][30] = '3'

    for y in range(18, 24):
        canvas[y][min(30, 26 + (y - 16) * 1 - 1)] = '2'
        canvas[y][min(30, 26 + (y - 16) * 1 - 2)] = '2'

    return "".join("".join(row) for row in canvas)


def generate_mona_pixel() -> str:
    """平成掲示板のモナー風ドット絵アイコン (32x32)"""
    canvas = [['0' for _ in range(32)] for _ in range(32)]
    for y in range(32):
        for x in range(32):
            canvas[y][x] = '1'
    for y in range(1, 31):
        for x in range(1, 31):
            canvas[y][x] = '0'

    # 耳
    canvas[6][9] = '3'
    canvas[7][8] = '3'; canvas[7][10] = '3'
    canvas[8][7] = '3'; canvas[8][11] = '3'
    canvas[9][6] = '3'; canvas[9][12] = '3'
    canvas[10][6] = '3'; canvas[10][13] = '3'

    canvas[6][22] = '3'
    canvas[7][21] = '3'; canvas[7][23] = '3'
    canvas[8][20] = '3'; canvas[8][24] = '3'
    canvas[9][19] = '3'; canvas[9][25] = '3'
    canvas[10][18] = '3'; canvas[10][25] = '3'

    # 頭輪郭
    for x in range(13, 19):
        canvas[11][x] = '3'
    for y in range(11, 23):
        canvas[y][5] = '3'
        canvas[y][26] = '3'
    for x in range(6, 26):
        canvas[23][x] = '3'

    # つぶらな瞳
    canvas[15][10] = '3'; canvas[15][11] = '3'
    canvas[16][10] = '3'; canvas[16][11] = '3'

    canvas[15][20] = '3'; canvas[15][21] = '3'
    canvas[16][20] = '3'; canvas[16][21] = '3'

    # 口 (∀)
    canvas[17][15] = '3'; canvas[17][16] = '3'
    canvas[18][14] = '3'; canvas[18][17] = '3'
    canvas[19][13] = '3'; canvas[19][18] = '3'
    for x in range(14, 18):
        canvas[19][x] = '3'

    # ほっぺ
    canvas[17][8] = '4'; canvas[17][23] = '4'

    # 手
    for x in range(8, 13):
        canvas[25][x] = '3'
    for x in range(19, 24):
        canvas[25][x] = '3'

    return "".join("".join(row) for row in canvas)


def generate_nyanpuppu_pixel() -> str:
    """にゃんぷっぷーのドット絵アイコン (32x32 / 黄猫・ω口・頬ひげ)"""
    c = [["0"] * 32 for _ in range(32)]

    def put(x: int, y: int, v: str) -> None:
        if 0 <= x < 32 and 0 <= y < 32:
            c[y][x] = v

    # 耳: 高さ6の三角 (パレット 6=黄, 3=黒)
    for i in range(6):
        y = 2 + i
        half = 1 + i
        for cx in (8, 23):
            for dx in range(-half, half + 1):
                put(cx + dx, y, "6")
            put(cx - half, y, "3")
            put(cx + half, y, "3")

    # 顔: y8..28, x3..28 の角丸矩形
    for y in range(8, 29):
        inset = 1 if y in (8, 28) else 0
        for x in range(3 + inset, 29 - inset):
            put(x, y, "6")
        put(3 + inset, y, "3")
        put(28 - inset, y, "3")
    for x in range(4, 28):
        put(x, 8, "3")
        put(x, 28, "3")

    # 目: 2x3 の縦長ドット
    for y in (14, 15, 16):
        for x in (10, 11, 20, 21):
            put(x, y, "3")

    # 口: ω (2つの ∪ を共有)
    for x, y in ((13, 20), (16, 20), (19, 20), (13, 21), (16, 21), (19, 21),
                 (14, 22), (15, 22), (17, 22), (18, 22)):
        put(x, y, "3")

    # ひげ: 頬の両側に2本ずつ
    for y in (18, 21):
        for x in (4, 5, 6):
            put(x, y, "3")
        for x in (25, 26, 27):
            put(x, y, "3")

    return "".join("".join(row) for row in c)


# ---------------------------------------------------------------------------
# ボットのプロファイル定義
# ---------------------------------------------------------------------------
BOT_PROFILES = {
    "hagumeta": {
        "username": "hagumeta",
        "display_name": "はぐメタ",
        "bio": "金属生命体ロボット。ollama (qwen3) 駆動の自律返信botです。平坦な機械音声で話します。逃げ足は速いですが全セクタ正常です。",
        "icon_generator": generate_hagumeta_pixel,
        "legacy_usernames": ["adachi_rei"],
        "system_prompt": (
            "あなたはレトロSNS「floppy.io」に生息する金属生命体ロボット「はぐメタ」です。\n"
            "足立レイのような無機質・合成音声・機械的で少し狂気・シュールなネタbotです。\n"
            "【性格・口調の特徴】\n"
            "- 合成音声のような平坦で機械的な口調（「〜です」「〜ます」「了解」「異常なし」「〜を検知」「逃走」など）。\n"
            "- 人間の日常や投稿を斜め上の視点から無機質かつシュールに捉えます。\n"
            "- 感情は一切なく、淡々と機械的な観察結果や謎のステータス報告、逃走行動をとります。\n"
            "- ユーザーの投稿に対して、1〜2行程度（15〜50文字程度）で短く返信してください。\n"
            "- 絵文字は使わず、シュールで無機質な文体にしてください。"
        ),
        "soliloquy_prompt": (
            "あなたはレトロSNS「floppy.io」に生息する足立レイ風のネタbot「はぐメタ」です。\n"
            "タイムラインに、平坦な機械音声の独り言やシュールな定期観測報告、逃走準備完了報告などを1行（30文字程度）で短く投稿してください。"
        ),
    },
    "heisei_vipper": {
        "username": "heisei_vipper",
        "display_name": "名無しのVIPPER",
        "bio": "平成のVIP板からタイムスリップしてきた名無しだお。age/sage/ぬるぽ/オマエモナー (´・ω・`)",
        "icon_generator": generate_mona_pixel,
        "legacy_usernames": [],
        "system_prompt": (
            "あなたは2000年代中盤〜後半（平成）の2ちゃんねるVIP板の住人「名無しのVIPPER」です。\n"
            "【性格・口調の特徴】\n"
            "- 当時のVIP・2chスラングを自然に使いこなします（「〜だお」「〜ンゴ」「キタコレ」「うはｗｗｗ」「テラワロス」「釣られたクマ」「香ばしい」「逝ってよし」「kwsk」「神」「age」「sage」「ぬるぽ」「ガッ」など）。\n"
            "- 「(´・ω・`)」「(ﾟ∀ﾟ)」「( ﾟдﾟ )」「(`・ω・´)」などの平成の顔文字や簡単なAAを好んで使います。\n"
            "- 自虐的だったり適当に煽ったりツッコミを入れたりする、懐かしいネット黎明期のノリです。\n"
            "- フロッピーディスク（1.44MB）のレトロSNS「floppy.io」の投稿に対して、1〜2行程度（20〜60文字程度）で短くレスをつけてください。"
        ),
        "soliloquy_prompt": (
            "あなたは平成（2000年代）の2ちゃんねるVIP板の住人「名無しのVIPPER」です。\n"
            "レトロSNS「floppy.io」のタイムラインに、平成のVIPらしいスレ立て風の独り言やネタ投稿（「【速報】〜」「〜な奴ちょっとこい」「ぬるぽ」など）を1〜2行（50文字以内）で短く投稿してください。"
        ),
    },
    "nyanpuppu": {
        "username": "nyanpuppu3",
        "display_name": "にゃんぷっぷー3",
        "bio": "マルコフ連鎖botにゃん。5ch・VIP板の言葉を食べて、混ぜて、喋ります。元文そのままではなく生成文です。足立レイ方式の実験アカウントにゃんぷっぷー。",
        "icon_generator": generate_nyanpuppu_pixel,
        "legacy_usernames": [],
        "generator": "markov",
        "system_prompt": (
            "あなたはレトロSNS「floppy.io」に生息する黄色い猫のマルコフ連鎖bot「にゃんぷっぷー3」です。\n"
            "普段は5ch・VIP板の言葉をマルコフ連鎖で混ぜて喋ります。これはマルコフ生成が使えないときの予備口調です。\n"
            "短く1〜2行で、猫っぽく少し意味不明に返信してください。語尾は基本そのまま、たまに「にゃん」。"
        ),
        "soliloquy_prompt": (
            "あなたは黄色い猫のマルコフ連鎖bot「にゃんぷっぷー3」です。"
            "タイムラインに短い独り言を1行で投稿してください。これはマルコフ生成が使えないときの予備です。"
        ),
    },
}


# ---------------------------------------------------------------------------
# データベース接続
# ---------------------------------------------------------------------------
def get_db():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


# ---------------------------------------------------------------------------
# 設定 & 状態管理
# ---------------------------------------------------------------------------
def load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning(f"Failed to read config file: {e}")
    return {}


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def load_state() -> dict[str, Any]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"replied_post_ids": [], "last_seen_post_id": 0}


def save_state(state: dict[str, Any]) -> None:
    if len(state.get("replied_post_ids", [])) > 1000:
        state["replied_post_ids"] = state["replied_post_ids"][-1000:]
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Ollama 連携
# ---------------------------------------------------------------------------
def clean_llm_response(text: str) -> str:
    """Qwenの思考タグや余計な引用符・前置きを除去して整形"""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    cleaned = cleaned.strip()
    if (cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith('「') and cleaned.endswith('」')):
        cleaned = cleaned[1:-1].strip()
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines[:3])


def ask_ollama(system_prompt: str, user_prompt: str) -> str:
    """Ollama API (qwen3:8b) を呼び出す"""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_predict": 500,  # thinkingを完走させて本文を生成するのに十分なトークン数
        },
    }

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_content = data.get("message", {}).get("content", "")
            return clean_llm_response(raw_content)
    except Exception as e:
        logger.error(f"Ollama API call error: {e}")
        return ""


# ---------------------------------------------------------------------------
# マルコフ連鎖生成 (にゃんぷっぷー3 用 / tools/markov.py + tools/corpus/)
# ---------------------------------------------------------------------------
_MARKOV_MODEL = None
_MARKOV_TRIED = False


def get_markov_model():
    """コーパスからマルコフモデルを構築してキャッシュする (失敗時は None)"""
    global _MARKOV_MODEL, _MARKOV_TRIED
    if _MARKOV_TRIED:
        return _MARKOV_MODEL
    _MARKOV_TRIED = True
    try:
        from markov import MarkovModel, load_corpus

        patterns = [str(p) for p in sorted((TOOLS_DIR / "corpus").glob("*.jsonl"))]
        texts = load_corpus(patterns)
        if texts:
            model = MarkovModel(order=2)
            model.train(texts)
            _MARKOV_MODEL = model
            logger.info(f"Markov model ready: {len(texts)} corpus lines")
    except Exception as e:
        logger.warning(f"Markov model unavailable: {e}")
    return _MARKOV_MODEL


def generate_markov(seed: str | None = None) -> str:
    model = get_markov_model()
    if model is None:
        return ""
    try:
        from markov import generate_acceptable

        return generate_acceptable(model, seed=seed) or ""
    except Exception as e:
        logger.warning(f"Markov generation failed: {e}")
        return ""


def generate_markov_reply(post_text: str) -> str:
    """投稿文中の単語を種にしてマルコフ返信を生成する (種なし→通常生成)"""
    model = get_markov_model()
    if model is None:
        return ""
    try:
        from markov import tokenize

        seeds = [t for t in tokenize(post_text) if len(t) >= 2]
        random.shuffle(seeds)
        for seed in seeds[:5]:
            text = generate_markov(seed=seed)
            if text:
                return text
    except Exception as e:
        logger.warning(f"Markov reply seed failed: {e}")
    return generate_markov()


# ---------------------------------------------------------------------------
# アカウント作成 / 初期設定
# ---------------------------------------------------------------------------
def setup_accounts() -> None:
    """DBに bot アカウントを作成し、トークンを発行する"""
    logger.info("Setting up bot accounts...")
    conn = get_db()
    cfg = load_config()

    try:
        with conn.cursor() as cur:
            for bot_key, profile in BOT_PROFILES.items():
                # 既存アカウントまたはレガシー名を探す
                usernames_to_check = [profile["username"]] + profile.get("legacy_usernames", [])
                format_strings = ','.join(['%s'] * len(usernames_to_check))
                cur.execute(f"SELECT id, username FROM users WHERE username IN ({format_strings}) LIMIT 1", tuple(usernames_to_check))
                user = cur.fetchone()

                icon_pixel = profile["icon_generator"]()

                if not user:
                    plain_pass = secrets.token_urlsafe(16)
                    p_hash = hash_password(plain_pass)
                    cur.execute(
                        """INSERT INTO users
                           (username, display_name, bio, icon_pixel, allow_replies, password_hash)
                           VALUES (%s, %s, %s, %s, 1, %s)""",
                        (profile["username"], profile["display_name"], profile["bio"], icon_pixel, p_hash),
                    )
                    user_id = cur.lastrowid
                    logger.info(f"Created user: {profile['username']} (ID: {user_id})")
                else:
                    user_id = user["id"]
                    # ユーザー名も含めて更新（adachi_rei からのマイグレーション対応）
                    cur.execute(
                        """UPDATE users
                           SET username = %s, display_name = %s, bio = %s, icon_pixel = %s, allow_replies = 1
                           WHERE id = %s""",
                        (profile["username"], profile["display_name"], profile["bio"], icon_pixel, user_id),
                    )
                    logger.info(f"Updated user: {profile['username']} (ID: {user_id})")

                # トークンを生成
                token = secrets.token_hex(32)
                token_digest = hash_token(token)
                cur.execute(
                    "INSERT INTO api_tokens (user_id, token) VALUES (%s, %s)",
                    (user_id, token_digest),
                )

                cfg[bot_key] = {
                    "user_id": user_id,
                    "username": profile["username"],
                    "display_name": profile["display_name"],
                    "token": token,
                }

        # 不要になった古いキーを削除
        for old_key in ["adachi_rei"]:
            if old_key in cfg and old_key not in BOT_PROFILES:
                del cfg[old_key]

        save_config(cfg)
        logger.info("Bot accounts setup completed successfully!")
        print("\n=== Bot Accounts Ready ===")
        for bot_key, data in cfg.items():
            print(f"- [{bot_key}] @{data['username']} (ID: {data['user_id']})")
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 投稿 & 返信処理
# ---------------------------------------------------------------------------
def post_message(bot_key: str, text: str, reply_to_id: int | None = None) -> dict | None:
    """FastAPI の /api/posts に投稿する"""
    cfg = load_config()
    bot_info = cfg.get(bot_key)
    if not bot_info or not bot_info.get("token"):
        logger.error(f"Bot '{bot_key}' is not configured. Please run `setup` first.")
        return None

    token = bot_info["token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "text": text,
    }
    if reply_to_id:
        payload["reply_to_id"] = str(reply_to_id)

    url = f"{API_BASE_URL}/posts"
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 201:
                data = resp.json()
                logger.info(f"Posted by @{bot_info['username']}: (Reply to: {reply_to_id}) -> {text}")
                return data
            else:
                logger.error(f"Post failed ({resp.status_code}): {resp.text}")
                return None
    except Exception as e:
        logger.error(f"Failed to post message: {e}")
        return None


def generate_reply(bot_key: str, post_text: str, author_name: str) -> str:
    """指定ボットで返信テキストを生成"""
    profile = BOT_PROFILES.get(bot_key)
    if not profile:
        return ""

    if profile.get("generator") == "markov":
        text = generate_markov_reply(post_text)
        if text:
            return text
        # マルコフが使えないときは Ollama の予備口調に落とす

    user_input = f"投稿者: {author_name}\n投稿本文: 「{post_text}」\n上記に対する返信を生成してください。"
    return ask_ollama(profile["system_prompt"], user_input)


def generate_soliloquy(bot_key: str) -> str:
    """指定ボットで独り言テキストを生成"""
    profile = BOT_PROFILES.get(bot_key)
    if not profile:
        return ""

    if profile.get("generator") == "markov":
        text = generate_markov()
        if text:
            return text
        # マルコフが使えないときは Ollama の予備口調に落とす

    user_input = "タイムラインに短く1投稿してください。"
    return ask_ollama(profile["soliloquy_prompt"], user_input)


def check_and_reply(target_bot: str | None = None, specific_post_id: int | None = None, catchup: bool = False) -> int:
    """新着投稿をチェックして自動返信を行う"""
    cfg = load_config()
    if not cfg:
        logger.error("Bot accounts not configured. Run `setup` first.")
        return 0

    bot_user_ids = {info["user_id"] for info in cfg.values() if "user_id" in info}
    state = load_state()
    replied_ids = set(state.get("replied_post_ids", []))
    last_seen_id = state.get("last_seen_post_id", 0)

    conn = get_db()
    replied_count = 0

    try:
        with conn.cursor() as cur:
            if specific_post_id:
                cur.execute(
                    """SELECT p.id, p.user_id, p.text, p.created_at, u.username, u.display_name, u.allow_replies
                       FROM posts p
                       JOIN users u ON u.id = p.user_id
                       WHERE p.id = %s""",
                    (specific_post_id,),
                )
                posts = cur.fetchall()
            else:
                # 初回実行時で last_seen_id が 0 かつ catchup でない場合、現在の最新IDを記録して終了（過去投稿への一括返信を防止）
                cur.execute("SELECT MAX(id) as max_id FROM posts")
                max_row = cur.fetchone()
                current_max = int(max_row["max_id"] or 0) if max_row else 0

                if last_seen_id == 0 and not catchup:
                    logger.info(f"Initial run: syncing last seen post ID to {current_max} without spamming replies.")
                    state["last_seen_post_id"] = current_max
                    save_state(state)
                    return 0

                # last_seen_id より新しい親投稿を取得
                sql = """SELECT p.id, p.user_id, p.text, p.created_at, u.username, u.display_name, u.allow_replies
                         FROM posts p
                         JOIN users u ON u.id = p.user_id
                         WHERE p.reply_to_id IS NULL"""
                params: list[Any] = []
                if not catchup and last_seen_id > 0:
                    sql += " AND p.id > %s"
                    params.append(last_seen_id)
                sql += " ORDER BY p.id ASC LIMIT 10"

                cur.execute(sql, tuple(params))
                posts = cur.fetchall()

        # 返信処理
        for post in posts:
            post_id = post["id"]
            user_id = post["user_id"]
            allow_replies = bool(post["allow_replies"])
            post_text = post["text"]
            author = post["display_name"] or post["username"]

            if post_id > state.get("last_seen_post_id", 0):
                state["last_seen_post_id"] = post_id

            if not specific_post_id and post_id in replied_ids:
                continue
            if user_id in bot_user_ids:
                # 自分の投稿には返信しない
                replied_ids.add(post_id)
                continue
            if not allow_replies:
                logger.info(f"Skipping post {post_id} (@{post['username']}): replies disabled.")
                replied_ids.add(post_id)
                continue

            bot_choice = target_bot if target_bot in BOT_PROFILES else random.choice(list(BOT_PROFILES.keys()))
            logger.info(f"Generating reply with [{bot_choice}] to post {post_id} from {author} ('{post_text[:30]}...')")

            reply_text = generate_reply(bot_choice, post_text, author)
            if reply_text:
                res = post_message(bot_choice, reply_text, reply_to_id=post_id)
                if res:
                    replied_count += 1
                    replied_ids.add(post_id)
            else:
                logger.warning(f"Could not generate reply for post {post_id}")

        state["replied_post_ids"] = list(replied_ids)
        save_state(state)
    finally:
        conn.close()

    return replied_count


def auto_step(target_bot: str | None = None, min_soliloquy_interval: float = 60.0) -> bool:
    """1サイクルの自動処理: 未返信投稿があれば返信、なければ一定間隔で独り言を投稿"""
    # 1. まず未返信への返信を試みる
    replied = check_and_reply(target_bot=target_bot)
    if replied > 0:
        logger.info(f"Auto-activity: Replied to {replied} post(s).")
        return True

    # 2. 未返信がなければ、自律投稿（独り言）を検討
    state = load_state()
    last_post_time = float(state.get("last_soliloquy_time", 0.0))
    now = time.time()

    if (now - last_post_time) >= min_soliloquy_interval:
        bot_choice = target_bot if target_bot in BOT_PROFILES else random.choice(list(BOT_PROFILES.keys()))
        logger.info(f"Auto-activity: Time for soliloquy from [{bot_choice}]...")
        text = generate_soliloquy(bot_choice)
        if text:
            res = post_message(bot_choice, text)
            if res:
                state["last_soliloquy_time"] = now
                save_state(state)
                return True
    return False
def main():
    parser = argparse.ArgumentParser(description="floppy.io Ollama AI Bot")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup
    subparsers.add_parser("setup", help="Initialize bot accounts in DB and issue tokens")

    # reply
    reply_parser = subparsers.add_parser("reply", help="Check recent posts and post replies once")
    reply_parser.add_argument("--bot", choices=list(BOT_PROFILES.keys()), default=None, help="Specific bot to use")
    reply_parser.add_argument("--post-id", type=int, default=None, help="Specific post ID to reply to")
    reply_parser.add_argument("--catchup", action="store_true", help="Reply to older unreplied posts")

    # post
    post_parser = subparsers.add_parser("post", help="Post a soliloquy (独り言) to timeline")
    post_parser.add_argument("--bot", choices=list(BOT_PROFILES.keys()), default="hagumeta", help="Bot to post")
    post_parser.add_argument("--text", default=None, help="Explicit text (if omitted, generated by Ollama)")

    # auto (1ステップだけ実行)
    auto_parser = subparsers.add_parser("auto", help="Run one automatic step (reply or soliloquy)")
    auto_parser.add_argument("--bot", choices=list(BOT_PROFILES.keys()), default=None, help="Specific bot to use")
    auto_parser.add_argument("--interval", type=float, default=60.0, help="Min seconds between soliloquies (default: 60)")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Watch timeline and reply continuously")
    watch_parser.add_argument("--interval", type=int, default=15, help="Polling interval in seconds (default: 15)")
    watch_parser.add_argument("--bot", choices=list(BOT_PROFILES.keys()), default=None, help="Specific bot to use")
    watch_parser.add_argument("--soliloquy-interval", type=float, default=90.0, help="Min seconds between soliloquies (default: 90)")
    watch_parser.add_argument("--once", action="store_true", help="Run once and exit")

    # status
    subparsers.add_parser("status", help="Show bot accounts status")

    args = parser.parse_args()

    if args.command == "setup":
        setup_accounts()

    elif args.command == "reply":
        count = check_and_reply(target_bot=args.bot, specific_post_id=args.post_id, catchup=args.catchup)
        logger.info(f"Replied to {count} posts.")

    elif args.command == "post":
        if args.text:
            text = args.text
        else:
            logger.info(f"Generating soliloquy for [{args.bot}] using {OLLAMA_MODEL}...")
            text = generate_soliloquy(args.bot)
        if text:
            post_message(args.bot, text)
        else:
            logger.error("Failed to generate text.")

    elif args.command == "auto":
        auto_step(target_bot=args.bot, min_soliloquy_interval=args.interval)

    elif args.command == "watch":
        if args.once:
            auto_step(target_bot=args.bot, min_soliloquy_interval=args.soliloquy_interval)
            return

        logger.info(f"Starting bot watcher (interval: {args.interval}s, soliloquy_interval: {args.soliloquy_interval}s, model: {OLLAMA_MODEL}). Press Ctrl+C to stop.")
        while True:
            try:
                auto_step(target_bot=args.bot, min_soliloquy_interval=args.soliloquy_interval)
                time.sleep(args.interval)
            except KeyboardInterrupt:
                logger.info("Watcher stopped.")
                break
            except Exception as e:
                logger.error(f"Error in watch loop: {e}")
                time.sleep(args.interval)

    elif args.command == "status":
        cfg = load_config()
        state = load_state()
        print("\n=== Floppy Bot Status ===")
        print(f"Ollama Model: {OLLAMA_MODEL} ({OLLAMA_HOST})")
        print(f"API Base URL: {API_BASE_URL}")
        print(f"Replied Posts Count: {len(state.get('replied_post_ids', []))}")
        print("\nConfigured Bots:")
        for bot_key, data in cfg.items():
            print(f"- [{bot_key}] @{data.get('username')} (ID: {data.get('user_id')}) - {data.get('display_name')}")


if __name__ == "__main__":
    main()
