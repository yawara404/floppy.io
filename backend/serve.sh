#!/usr/bin/env bash
# floppy.io — API を「落ちても自動で復帰」させる supervisor
#
#   ./serve.sh               # :8000 で起動し、異常終了したら自動で再起動
#   PORT=8001 ./serve.sh     # ポートを変える
#   RESTART_DELAY=5 ./serve.sh
#
# 停止: 表示された PID に SIGTERM (kill <PID>)
# 常駐させる場合は launchd / systemd と併用する（deploy/ を参照）。
set -uo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
LOG_DIR="${LOG_DIR:-$PWD/logs}"
LOG_FILE="$LOG_DIR/api.log"
PID_FILE="$LOG_DIR/api.pid"
RESTART_DELAY="${RESTART_DELAY:-3}"

if [ ! -d .venv ]; then
  echo "✗ .venv がありません。先に ./run.sh を実行してください。" >&2
  exit 1
fi

# shellcheck disable=SC1091
source .venv/bin/activate

mkdir -p "$LOG_DIR"

# 二重起動を防ぐ
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "✗ 既に起動しています (PID $(cat "$PID_FILE"))。" >&2
  echo "  停止するには: kill $(cat "$PID_FILE")" >&2
  exit 1
fi

if command -v lsof >/dev/null 2>&1 &&
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "✗ ポート $PORT は既に使用中です:" >&2
  lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >&2 || true
  echo "  PORT=8001 ./serve.sh のように別ポートで起動できます。" >&2
  exit 1
fi

echo $$ >"$PID_FILE"

child=""
cleanup() {
  if [ -n "$child" ] && kill -0 "$child" 2>/dev/null; then
    kill "$child" 2>/dev/null
    wait "$child" 2>/dev/null
  fi
  rm -f "$PID_FILE"
  echo ""
  echo "→ supervisor stopped"
  exit 0
}
trap cleanup INT TERM

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >>"$LOG_FILE"
}

echo "→ supervisor started (pid $$, port $PORT)"
echo "→ ログ: $LOG_FILE"
echo "→ 停止: kill $$"

log "supervisor started (pid $$, port $PORT)"

while true; do
  log "starting uvicorn on 127.0.0.1:$PORT"
  uvicorn app.main:app \
    --host 127.0.0.1 \
    --port "$PORT" \
    --proxy-headers \
    --forwarded-allow-ips 127.0.0.1 >>"$LOG_FILE" 2>&1 &
  child=$!

  wait "$child"
  code=$?
  child=""

  # 意図的な停止 (SIGTERM) でなければ、少し待って自動で復帰する
  log "uvicorn exited (code $code) — restarting in ${RESTART_DELAY}s"
  sleep "$RESTART_DELAY" &
  wait $!
done
