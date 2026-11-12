"""floppy.io — SQL の小さな共通ヘルパー"""

from __future__ import annotations

import re


def like_escape(value: str) -> str:
    """LIKE 検索のワイルドカード（% _ \\）を文字として扱えるようにする"""
    return re.sub(r"([\\%_])", r"\\\1", str(value))
