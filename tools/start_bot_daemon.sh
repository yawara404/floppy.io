#!/bin/bash
# floppy.io — Bot 常駐デーモン起動 / 停止スクリプト
#
# 使い方:
#   ./tools/start_bot_daemon.sh start   # バックグラウンドで常駐開始
#   ./tools/start_bot_daemon.sh stop    # 常駐停止
#   ./tools/start_bot_daemon.sh restart # 再起動
#   ./tools/start_bot_daemon.sh status  # 状態確認

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$ROOT_DIR/backend/.venv/bin/python"
PID_FILE="$SCRIPT_DIR/bot_daemon.pid"
LOG_FILE="$ROOT_DIR/backend/logs/bot_daemon.log"

mkdir -p "$ROOT_DIR/backend/logs"

start() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Bot は既に起動しています (PID: $(cat "$PID_FILE"))。"
    return 0
  fi

  echo "Bot デーモンを起動します..."
  nohup "$VENV_PYTHON" "$SCRIPT_DIR/bot.py" watch --interval 20 --soliloquy-interval 90 > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "Bot デーモンを起動しました (PID: $(cat "$PID_FILE"))。"
}

stop() {
  if [ -f "$PID_FILE" ]; then
    PID="$(cat "$PID_FILE")"
    if kill -0 "$PID" 2>/dev/null; then
      echo "Bot デーモン (PID: $PID) を停止します..."
      kill "$PID" 2>/dev/null || true
      rm -f "$PID_FILE"
      echo "停止しました。"
      return 0
    fi
    rm -f "$PID_FILE"
  fi
  echo "Bot デーモンは起動していません。"
}

status() {
  if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Bot デーモンは実行中です (PID: $(cat "$PID_FILE"))。"
  else
    echo "Bot デーモンは停止しています。"
  fi
}

case "${1:-status}" in
  start)
    start
    ;;
  stop)
    stop
    ;;
  restart)
    stop
    sleep 1
    start
    ;;
  status)
    status
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
    ;;
esac
