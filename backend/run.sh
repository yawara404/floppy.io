#!/usr/bin/env bash
# floppy.io — Python API 開発サーバー
#
#   ./run.sh                 # :8000 で起動 (ファイル変更で自動リロード)
#   PORT=8001 ./run.sh       # ポートを変える
#
# ポートが埋まっている / 起動に失敗した原因を分かるようにし、
# ログを backend/logs/api.log にも残す（「鯖落ち」の事後調査用）。
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
LOG_DIR="${LOG_DIR:-$PWD/logs}"
LOG_FILE="$LOG_DIR/api.log"

if [ ! -d .venv ]; then
  echo "→ .venv を作成します"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -f .venv/.installed ]; then
  echo "→ 依存パッケージをインストールします"
  pip install --upgrade pip
  pip install -r requirements.txt
  touch .venv/.installed
fi

mkdir -p "$LOG_DIR"

# ポートが塞がっていると uvicorn は "Address already in use" で即終了する。
# 原因が分かるように、使用中のプロセスを表示して止める。
if command -v lsof >/dev/null 2>&1 &&
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✗ ポート $PORT は既に使用中です:" >&2
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
  echo "" >&2
  echo "  別ポートで起動する場合:" >&2
  echo "    PORT=8001 ./run.sh" >&2
  echo "    cd ../frontend && FLOPPY_API_PORT=8001 npm run dev" >&2
  exit 1
fi

echo "→ API: http://127.0.0.1:$PORT"
echo "→ ログ: $LOG_FILE"

# 標準出力 / 標準エラーを画面とログの両方に出す
exec > >(tee -a "$LOG_FILE") 2>&1

exec uvicorn app.main:app \
  --host 127.0.0.1 \
  --port "$PORT" \
  --reload \
  --proxy-headers \
  --forwarded-allow-ips 127.0.0.1

