#!/bin/bash
# floppy.io — Bot 実行スクリプト
#
# 使い方:
#   ./tools/bot.sh setup                # Botアカウント作成 & 初期化
#   ./tools/bot.sh reply                # 新着投稿へ1回自動返信
#   ./tools/bot.sh reply --bot hagumeta
#   ./tools/bot.sh reply --bot heisei_vipper
#   ./tools/bot.sh post --bot hagumeta  # 独り言（自律投稿）
#   ./tools/bot.sh post --bot heisei_vipper
#   ./tools/bot.sh watch                # 常駐監視モード（自動返信ループ）
#   ./tools/bot.sh status               # 状態確認

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Python仮想環境が見つかりません: $VENV_PYTHON" >&2
    exit 1
fi

exec "$VENV_PYTHON" "$SCRIPT_DIR/bot.py" "$@"
