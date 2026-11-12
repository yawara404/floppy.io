#!/bin/bash
# floppy.io — にゃんぷっぷー3 (マルコフ連鎖bot) 実行スクリプト
#
# 使い方:
#   ./tools/nyanpuppu.sh generate   # 候補文を10個出すだけ
#   ./tools/nyanpuppu.sh post       # マルコフ生成して1件投稿
#
# 分かち書きに Janome を使うと生成が安定します:
#   backend/.venv/bin/pip install janome

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Python仮想環境が見つかりません: $VENV_PYTHON" >&2
    exit 1
fi

cd "$ROOT_DIR"
exec "$VENV_PYTHON" "$SCRIPT_DIR/nyanpuppu.py" "$@"
