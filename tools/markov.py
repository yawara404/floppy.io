#!/usr/bin/env python3
"""floppy.io — マルコフ連鎖テキスト生成 (足立レイ方式)

コーパス jsonl (collector_5ch.py の出力など) を単語レベルのマルコフ連鎖で混ぜて、
元文とは違う新しい一文を生成する。

使い方:
    python3 tools/markov.py --count 10
    python3 tools/markov.py --corpus tools/corpus/news4vip.jsonl --seed コーヒー

設計メモ:
- 分かち書きは Janome があれば使い、無ければ助詞ベースの簡易分割に落とす
  (Mac で使うときは backend/.venv/bin/pip install janome を推奨)
- 生成文が元コーパスと長く一致するものは「転載に近い」として棄却する
- NGワードを含む生成文も棄却する (collector_5ch.py と同じ方針)
"""

from __future__ import annotations

import argparse
import glob
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

BOS = "<BOS>"
EOS = "<EOS>"

NG_WORDS = [
    "ガイジ", "池沼", "キチガイ", "きちがい", "気違い",
    "土人", "チョン", "部落", "穢多", "非人",
    "障害者死", "在日", "売国", "反日",
    "死ね", "死んで", "殺す", "殺せ", "自殺し", "首吊",
    "レイプ", "強姦", "痴漢",
    "ぶっかけ", "肛門", "手コキ", "フェラ", "パイズリ", "中出し",
    "射精", "勃起", "ちんこ", "まんこ", "オナニー", "性器", "エロ過ぎ",
    "おっぱい", "セックス",
    "晒せ", "晒すぞ", "特定し",
]

# ---------------------------------------------------------------------------
# 分かち書き
# ---------------------------------------------------------------------------
_tokenizer = None
_tokenizer_tried = False


def tokenize(text: str) -> list[str]:
    global _tokenizer, _tokenizer_tried
    if not _tokenizer_tried:
        _tokenizer_tried = True
        try:
            from janome.tokenizer import Tokenizer

            _tokenizer = Tokenizer()
        except Exception:
            _tokenizer = None
    if _tokenizer is not None:
        return [t.surface for t in _tokenizer.tokenize(text) if t.surface.strip()]
    return _fallback_tokenize(text)


_PARTICLE_SPLIT = re.compile(
    r"(?<=[はがをにへとでもやねよかなぁわざ])|(?<=[、。！？!?…])"
)
_CHAR_RUN = re.compile(r"[ぁ-ん]+|[ァ-ヶー]+|[一-龯]+|[A-Za-z]+|[0-9]+|.")


def _fallback_tokenize(text: str) -> list[str]:
    """Janome が無いときの簡易分割。助詞の後と文字種の切れ目で割る。"""
    chunks: list[str] = []
    for run in _CHAR_RUN.findall(text):
        parts = _PARTICLE_SPLIT.split(run)
        chunks.extend(p for p in parts if p)
    return chunks


# ---------------------------------------------------------------------------
# マルコフ連鎖
# ---------------------------------------------------------------------------
class MarkovModel:
    def __init__(self, order: int = 2):
        self.order = order
        self.chain: dict[tuple[str, ...], list[str]] = defaultdict(list)
        self.starts: list[tuple[str, ...]] = []
        self.source_lines: list[str] = []

    def train(self, texts: list[str]) -> None:
        for text in texts:
            text = text.strip()
            if not text:
                continue
            if _symbol_ratio(text) > 0.45:
                continue  # AA断片など記号主体の行は学習しない
            self.source_lines.append(text)
            tokens = [BOS] * self.order + tokenize(text) + [EOS]
            for i in range(len(tokens) - self.order):
                state = tuple(tokens[i : i + self.order])
                nxt = tokens[i + self.order]
                self.chain[state].append(nxt)
                if all(w == BOS for w in state):
                    self.starts.append(state)

    def generate(self, seed: str | None = None, max_tokens: int = 40) -> str:
        if seed:
            starts = [
                s
                for s in self.chain
                if seed in s and s[0] != BOS
            ]
            if starts:
                state = random.choice(starts)
                out = [w for w in state if w != BOS]
            else:
                state = random.choice(self.starts)
                out = []
        else:
            state = random.choice(self.starts)
            out = []
        for _ in range(max_tokens):
            nxts = self.chain.get(state)
            if not nxts:
                break
            nxt = random.choice(nxts)
            if nxt == EOS:
                break
            out.append(nxt)
            state = tuple(list(state[1:]) + [nxt])
        return "".join(out).strip()


def longest_common_substring_len(a: str, b: str) -> int:
    """生成文と元文の最長共通部分文字列の長さ (転載近似チェック用)。"""
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    best = 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def _symbol_ratio(text: str) -> float:
    if not text:
        return 1.0
    symbolish = sum(
        1
        for ch in text
        if not ("\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff" or ch.isalnum())
    )
    return symbolish / len(text)


_END_PARTICLES = ("に", "を", "が", "は", "の", "で", "と", "へ", "も", "や")


def is_acceptable(text: str, model: MarkovModel, max_overlap: int = 13) -> bool:
    if not (8 <= len(text) <= 70):
        return False
    if any(ng in text for ng in NG_WORDS):
        return False
    if "http" in text or ">>" in text:
        return False
    if _symbol_ratio(text) > 0.35:
        return False
    if text.endswith(_END_PARTICLES):
        return False  # 助詞で終わる文は途切れ感が強いので棄却
    # 元文そのまま / 長い引用は棄却
    for src in model.source_lines:
        if text == src:
            return False
        if len(src) >= 8 and longest_common_substring_len(text, src) >= max_overlap:
            return False
    return True


def generate_acceptable(
    model: MarkovModel, seed: str | None = None, tries: int = 60
) -> str:
    for _ in range(tries):
        cand = model.generate(seed=seed)
        if is_acceptable(cand, model):
            return cand
    return ""


# ---------------------------------------------------------------------------
# コーパス読み込み
# ---------------------------------------------------------------------------
def load_corpus(patterns: list[str]) -> list[str]:
    texts: list[str] = []
    for pat in patterns:
        for path in sorted(glob.glob(pat)):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                        texts.append(str(row.get("text", "")))
                    except json.JSONDecodeError:
                        texts.append(line)
    return [t for t in texts if t.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description="Markov text generator")
    ap.add_argument(
        "--corpus",
        nargs="+",
        default=["tools/corpus/*.jsonl"],
        help="コーパス jsonl (glob可)",
    )
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--seed", default=None, help="この単語を含む状態から生成開始")
    ap.add_argument("--order", type=int, default=2)
    args = ap.parse_args()

    texts = load_corpus(args.corpus)
    if not texts:
        print("コーパスが空です", file=sys.stderr)
        return 1
    model = MarkovModel(order=args.order)
    model.train(texts)
    print(f"# corpus lines: {len(texts)}", file=sys.stderr)
    for _ in range(args.count):
        s = generate_acceptable(model, seed=args.seed)
        print(s if s else "(生成失敗: フィルタを通過しませんでした)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
