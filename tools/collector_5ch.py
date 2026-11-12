#!/usr/bin/env python3
"""floppy.io — 5ch コレクタ試作 (ニュー速VIP)

5ch の公開エンドポイント (subject.txt / dat) からレス本文を取得し、
bot のコーパス用に掃除・フィルタして jsonl で書き出す。

使い方:
    python3 tools/collector_5ch.py                     # VIP板・新着8スレ
    python3 tools/collector_5ch.py --threads 20 --strategy top
    python3 tools/collector_5ch.py --out tools/corpus/news4vip.jsonl

出力 jsonl の1行:
    {"source": "5ch", "board": "news4vip", "thread_key": "...",
     "thread_title": "...", "kind": "res" | "title", "text": "..."}

設計メモ:
- 標準ライブラリのみ (backend/.venv でもそのまま動く)
- 板サーバーは移転するので bbsmenu.json から動的に解決する
- 本文以外 (名前・ID・日付) はコーパスに入れない
- 差別語・暴力表現・個人情報らしき断片はフィルタで落とす (NG_WORDS)
- 取得間隔を空ける。dat の全件取得はスレ単位で最大 --threads スレまで
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

USER_AGENT = "floppy.io-bot-corpus-collector/0.1 (prototype; polite fetch)"
MENU_JSON_URL = "https://menu.5ch.net/bbsmenu.json"
FALLBACK_BOARDS = {
    "news4vip": "https://mi.5ch.io/news4vip/",
}

# ---------------------------------------------------------------------------
# フィルタ設定
# ---------------------------------------------------------------------------
# コーパスに入れたくない語。5ch の生テキストには差別語や攻撃表現が混ざるため、
# ここで落とす。語を追加するときは「bot に言わせたくないか」だけで判断する。
NG_WORDS = [
    # 差別・蔑称
    "ガイジ", "池沼", "キチガイ", "きちがい", "気違い",
    "土人", "チョン", "部落", "穢多", "非人",
    "障害者死", "在日", "売国", "反日",
    # 暴力・自傷の直接表現
    "死ね", "死んで", "殺す", "殺せ", "自殺し", "首吊",
    # 性的暴力
    "レイプ", "強姦", "痴漢",
    # 露骨な性的表現 (常駐スレのコーパスで特に混ざりやすい)
    "ぶっかけ", "肛門", "手コキ", "フェラ", "パイズリ", "中出し",
    "射精", "勃起", "ちんこ", "まんこ", "オナニー", "性器", "エロ過ぎ",
    "おっぱい", "セックス",
    # 個人特定っぽい誘導
    "晒せ", "晒すぞ", "特定し",
]

# スレごと除外するタイトル (運営告知・システムスレはコーパスにならない)
TITLE_BLOCK_WORDS = ["お知らせ", "★", "運営", "システムのお"]
# 投稿者名がこれらを含むレスは運営・システム投稿として丸ごと除外
SYSTEM_NAME_MARKERS = ["★", "運営", "システム"]

MIN_CHARS = 4
MAX_CHARS = 120

RE_URL = re.compile(r"https?://\S+|www\.\S+")
RE_ANCHOR = re.compile(r">>\s?\d+(?:-\d+)?")
RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
RE_PHONE = re.compile(r"0\d{1,4}-\d{1,4}-\d{4}|0\d{9,10}")
RE_LONG_DIGITS = re.compile(r"\d{7,}")
RE_TAG = re.compile(r"<[^>]*>")
RE_THREAD_COUNT = re.compile(r"\((\d+)\)\s*$")
RE_SPACES = re.compile(r"[ \t\u3000]+")


def fetch_bytes(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_cp932(url: str) -> str:
    return fetch_bytes(url).decode("cp932", errors="replace")


# ---------------------------------------------------------------------------
# 板URL解決 / スレ一覧
# ---------------------------------------------------------------------------
def resolve_board_url(board: str) -> str:
    """bbsmenu.json から板の現在URLを引く。失敗したらフォールバック表。"""
    try:
        data = json.loads(fetch_bytes(MENU_JSON_URL).decode("utf-8", "replace"))
        found: list[str] = []

        def walk(obj: Any) -> None:
            if isinstance(obj, dict):
                if obj.get("directory_name") == board and obj.get("url"):
                    found.append(str(obj["url"]))
                for v in obj.values():
                    walk(v)
            elif isinstance(obj, list):
                for v in obj:
                    walk(v)

        walk(data)
        if found:
            return found[0] if found[0].endswith("/") else found[0] + "/"
    except Exception as e:  # メニュー取得失敗時はフォールバックへ
        print(f"[warn] bbsmenu.json 取得失敗: {e}", file=sys.stderr)
    if board in FALLBACK_BOARDS:
        return FALLBACK_BOARDS[board]
    raise SystemExit(f"板URLを解決できませんでした: {board}")


def parse_subject(text: str) -> list[dict[str, Any]]:
    threads = []
    for line in text.strip().splitlines():
        if "<>" not in line:
            continue
        dat_name, title = line.split("<>", 1)
        key = dat_name.replace(".dat", "")
        m = RE_THREAD_COUNT.search(title)
        count = int(m.group(1)) if m else 0
        title = RE_THREAD_COUNT.sub("", title).strip()
        threads.append({"key": key, "title": title, "res_count": count})
    return threads


def select_threads(
    threads: list[dict[str, Any]],
    n: int,
    strategy: str,
    min_res: int,
    max_res: int,
) -> list[dict[str, Any]]:
    pool = [
        t
        for t in threads
        if min_res <= t["res_count"] <= max_res
        and not any(b in t["title"] for b in TITLE_BLOCK_WORDS)
        and not any(ng in t["title"] for ng in NG_WORDS)
    ]
    if strategy == "top":
        pool.sort(key=lambda t: t["res_count"], reverse=True)
    else:  # recent: スレ立て時刻 (key) の新しい順
        pool.sort(key=lambda t: int(t["key"]), reverse=True)
    return pool[:n]


# ---------------------------------------------------------------------------
# dat パース / 掃除
# ---------------------------------------------------------------------------
def parse_dat(text: str) -> tuple[str, list[str]]:
    """dat を (スレタイ, レス本文リスト) に分解する。本文フィールドだけ返す。"""
    thread_title = ""
    bodies: list[str] = []
    for line in text.strip().splitlines():
        parts = line.split("<>")
        if len(parts) < 4:
            continue
        if any(m in parts[0] for m in SYSTEM_NAME_MARKERS):
            continue  # 運営・システム投稿はコーパスにしない
        body = parts[3]
        if len(parts) >= 5 and parts[4]:
            thread_title = parts[4]
        bodies.append(body)
    return thread_title, bodies


def is_aa_like(line: str) -> bool:
    """AA・記号主体の行かどうか。大まかな判定で十分。"""
    if not line:
        return True
    symbolish = sum(
        1
        for ch in line
        if not (
            "\u3040" <= ch <= "\u30ff"  # かな
            or "\u4e00" <= ch <= "\u9fff"  # 漢字
            or ch.isalnum()
        )
    )
    return symbolish / len(line) > 0.65 and len(line) > 8


def clean_lines(body: str) -> list[str]:
    """レス本文を候補行のリストにする。フィルタ理由の集計は呼び出し側。"""
    text = body.replace("<br>", "\n")
    text = RE_TAG.sub("", text)
    text = html.unescape(text)
    out = []
    for raw in text.splitlines():
        line = RE_ANCHOR.sub("", raw)
        line = RE_URL.sub("", line)
        line = RE_SPACES.sub(" ", line).strip(" 　・")
        if line:
            out.append(line)
    return out


def filter_reason(line: str) -> str | None:
    """残すなら None、落とすなら理由を返す。"""
    if len(line) < MIN_CHARS:
        return "too_short"
    if len(line) > MAX_CHARS:
        return "too_long"
    if RE_EMAIL.search(line) or RE_PHONE.search(line):
        return "personal_info"
    if RE_LONG_DIGITS.search(line):
        return "digits"
    if line.startswith("/") or ".dat" in line or ".txt" in line.lower():
        return "path_like"
    if any(ng in line for ng in NG_WORDS):
        return "ng_word"
    if is_aa_like(line):
        return "aa_like"
    return None


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="5ch corpus collector (prototype)")
    ap.add_argument("--board", default="news4vip", help="板ディレクトリ名")
    ap.add_argument("--threads", type=int, default=8, help="取得するスレ数")
    ap.add_argument("--strategy", choices=["recent", "top"], default="recent")
    ap.add_argument("--min-res", type=int, default=5, help="対象スレの最小レス数")
    ap.add_argument(
        "--max-thread-res",
        type=int,
        default=500,
        help="対象スレの最大レス数 (常駐スレを避ける)",
    )
    ap.add_argument(
        "--max-res-per-thread", type=int, default=300, help="1スレから読む最大レス数"
    )
    ap.add_argument(
        "--out",
        default="tools/corpus/news4vip.jsonl",
        help="出力 jsonl (floppy_io ルートからの相対でも可)",
    )
    ap.add_argument("--delay", type=float, default=1.0, help="dat取得間隔(秒)")
    ap.add_argument("--no-titles", action="store_true", help="スレタイをコーパスに含めない")
    args = ap.parse_args()

    board_url = resolve_board_url(args.board)
    print(f"board: {args.board} -> {board_url}")

    subject = fetch_cp932(board_url + "subject.txt")
    threads = select_threads(
        parse_subject(subject),
        args.threads,
        args.strategy,
        args.min_res,
        args.max_thread_res,
    )
    print(f"target threads: {len(threads)}")

    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    drops: Counter[str] = Counter()
    raw_res = 0

    for i, th in enumerate(threads):
        if i > 0:
            time.sleep(args.delay)
        dat_url = f"{board_url}dat/{th['key']}.dat"
        try:
            dat_text = fetch_cp932(dat_url)
        except Exception as e:
            print(f"[warn] dat取得失敗 {th['key']}: {e}", file=sys.stderr)
            continue
        title, bodies = parse_dat(dat_text)
        title = title or th["title"]
        raw_res += len(bodies)

        if not args.no_titles and title and title not in seen:
            if filter_reason(title) is None:
                seen.add(title)
                records.append(
                    {
                        "source": "5ch",
                        "board": args.board,
                        "thread_key": th["key"],
                        "thread_title": title,
                        "kind": "title",
                        "text": title,
                        "fetched_at": fetched_at,
                    }
                )
        for body in bodies[: args.max_res_per_thread]:
            for line in clean_lines(body):
                reason = filter_reason(line)
                if reason:
                    drops[reason] += 1
                    continue
                if line in seen:
                    drops["duplicate"] += 1
                    continue
                seen.add(line)
                records.append(
                    {
                        "source": "5ch",
                        "board": args.board,
                        "thread_key": th["key"],
                        "thread_title": title,
                        "kind": "res",
                        "text": line,
                        "fetched_at": fetched_at,
                    }
                )
        print(f"  [{th['key']}] {title[:40]}  res={len(bodies)}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = {
        "board": args.board,
        "board_url": board_url,
        "threads": len(threads),
        "raw_responses": raw_res,
        "kept_lines": len(records),
        "drops": dict(drops),
        "fetched_at": fetched_at,
    }
    stats_path = out_path.with_suffix(".stats.json")
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False, indent=2))
    print(f"wrote: {out_path} / {stats_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
