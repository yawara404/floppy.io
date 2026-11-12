#!/bin/bash
# floppy.io — 5chコレクタ実行スクリプト
#
# 使い方:
#   ./tools/collector_5ch.sh                          # VIP板・新着8スレ → tools/corpus/news4vip.jsonl
#   ./tools/collector_5ch.sh --threads 20
#   ./tools/collector_5ch.sh --strategy top --threads 5 --out tools/corpus/news4vip_top.jsonl

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Python仮想環境が見つかりません: $VENV_PYTHON" >&2
    exit 1
fi

cd "$ROOT_DIR"
exec "$VENV_PYTHON" "$SCRIPT_DIR/collector_5ch.py" "$@"
