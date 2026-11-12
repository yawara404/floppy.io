#!/bin/bash
# floppy.io — 全コーパス自動スクレイピング & 収集スクリプト
#
# 使い方:
#   ./tools/collector_all.sh            # VIP板 + 古のボカロネタをまとめて収集・更新
#   ./tools/collector_all.sh --threads 15

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Python仮想環境が見つかりません: $VENV_PYTHON" >&2
    exit 1
fi

cd "$ROOT_DIR"

echo "=== 1/2 古のボカロネタ・名フレーズ コーパス更新 ==="
"$VENV_PYTHON" "$SCRIPT_DIR/collector_vocalo.py"

echo ""
echo "=== 2/2 5ch (ニュー速VIP) スレッド・レス収集 ==="
# 外部通信を行うためエラー時は既存コーパスを維持
"$VENV_PYTHON" "$SCRIPT_DIR/collector_5ch.py" --threads 10 || echo "⚠ 5chからの収集はスキップされました（既存のコーパスを継続使用します）"

echo ""
echo "=== コーパス統計 ==="
wc -l "$SCRIPT_DIR"/corpus/*.jsonl
echo "コーパス更新完了！"

