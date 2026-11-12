#!/usr/bin/env python3
"""floppy.io — にゃんぷっぷー3 (マルコフ連鎖bot)

collector_5ch.py が集めたコーパスを markov.py で混ぜて投稿する専用ランナー。
bot.py (Ollama勢) とは独立に動く。

使い方:
    ./tools/nyanpuppu.sh generate           # 候補を10個出すだけ
    ./tools/nyanpuppu.sh post               # 生成して1件投稿
    ./tools/nyanpuppu.sh post --text "..."  # 文を指定して投稿

設定は tools/nyanpuppu_config.json (token を含むので共有しないこと):
    {"username": "nyanpuppu3", "display_name": "にゃんぷっぷー3",
     "token": "...", "password": "...",
     "api_base_url": "http://127.0.0.1:8001/api"}
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
ROOT_DIR = TOOLS_DIR.parent
CONFIG_FILE = TOOLS_DIR / "nyanpuppu_config.json"
sys.path.insert(0, str(TOOLS_DIR))

from markov import MarkovModel, generate_acceptable, load_corpus  # noqa: E402


# ---------------------------------------------------------------------------
# ドット絵アイコン (32x32 = 1024文字 / パレット: 0=白 1=銀 2=灰 3=黒 4=赤)
# ---------------------------------------------------------------------------
def generate_nyan_pixel() -> str:
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
# API
# ---------------------------------------------------------------------------
def load_config() -> dict:
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def api_post(cfg: dict, path: str, payload: dict) -> dict:
    base = cfg.get("api_base_url", "http://127.0.0.1:8001/api").rstrip("/")
    req = urllib.request.Request(
        base + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {cfg['token']}",
            "Content-Type": "application/json",
            # 既定の Python-urllib UA は Cloudflare に弾かれることがあるため明示する
            "User-Agent": "floppy-nyanpuppu/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_model() -> MarkovModel:
    patterns = [str(p) for p in sorted((TOOLS_DIR / "corpus").glob("*.jsonl"))]
    texts = load_corpus(patterns)
    model = MarkovModel(order=2)
    model.train(texts)
    return model


def main() -> int:
    ap = argparse.ArgumentParser(description="nyanpuppu-3 markov bot")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("generate", help="候補文を出すだけ")
    p_post = sub.add_parser("post", help="生成して投稿する")
    p_post.add_argument("--text", default=None)
    p_post.add_argument("--api-base", default=None, help="投稿先APIの上書き")
    args = ap.parse_args()

    model = build_model()
    if args.command == "generate":
        for _ in range(10):
            print(generate_acceptable(model) or "(生成失敗)")
        return 0

    cfg = load_config()
    if args.api_base:
        cfg["api_base_url"] = args.api_base
    text = args.text or generate_acceptable(model)
    if not text:
        print("生成に失敗しました", file=sys.stderr)
        return 1
    res = api_post(cfg, "/posts", {"text": text})
    post_id = res.get("id") or (res.get("post") or {}).get("id")
    print(f"posted: id={post_id} text={text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
