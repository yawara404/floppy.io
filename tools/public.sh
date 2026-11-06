#!/usr/bin/env bash
# floppy.io — 公開サイト (https://fdd.wawa-app.me/floppy.io/) の起動 / 停止
#
#   ./tools/public.sh setup     # Cloudflare Tunnel と DNS を用意する (初回だけ)
#   ./tools/public.sh start     # API(:8001) + ゲートウェイ(:8899) + トンネル
#   ./tools/public.sh ensure    # 落ちているものだけ起こす (launchd / cron 用)
#   ./tools/public.sh status
#   ./tools/public.sh stop
#
# 構成:
#   ブラウザ → Cloudflare (fdd.wawa-app.me) → トンネル floppy
#            → http://127.0.0.1:8899 (tools/public_gateway.py)
#               ├── /floppy.io/          … frontend/dist (静的)
#               ├── /floppy.io/api/...   … http://127.0.0.1:8001 (FastAPI)
#               └── /floppy.io/uploads/  … http://127.0.0.1:8001 (FastAPI)
#
# ポート 8000 が他プロジェクトと衝突するため、API は 8001 で動かす。
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8001}"
WEB_PORT="${WEB_PORT:-8899}"
TUNNEL_NAME="${TUNNEL_NAME:-floppy}"
HOSTNAME_PUBLIC="${HOSTNAME_PUBLIC:-fdd.wawa-app.me}"
CONFIG="$HOME/.cloudflared/${TUNNEL_NAME}.yml"

LOG_DIR="$ROOT/logs"
mkdir -p "$LOG_DIR"

API_LOG="$ROOT/backend/logs/api.log"   # backend/serve.sh が書く
GATEWAY_LOG="$LOG_DIR/gateway.log"
GATEWAY_PID="$LOG_DIR/gateway.pid"
TUNNEL_LOG="$LOG_DIR/tunnel.log"
TUNNEL_PID="$LOG_DIR/tunnel.pid"

port_busy() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

pid_alive() {
  [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null
}

setup() {
  if ! command -v cloudflared >/dev/null 2>&1; then
    echo "✗ cloudflared がありません (brew install cloudflared)" >&2
    return 1
  fi

  if ! cloudflared tunnel list 2>/dev/null | awk 'NR>1 {print $2}' | grep -qx "$TUNNEL_NAME"; then
    echo "→ トンネル $TUNNEL_NAME を作成します"
    cloudflared tunnel create "$TUNNEL_NAME" || return 1
  fi

  local uuid
  uuid="$(cloudflared tunnel list 2>/dev/null | awk -v n="$TUNNEL_NAME" '$2==n {print $1; exit}')"
  if [ -z "$uuid" ]; then
    echo "✗ トンネル $TUNNEL_NAME の ID を取得できませんでした" >&2
    return 1
  fi

  if [ ! -f "$CONFIG" ]; then
    cat >"$CONFIG" <<YAML
# floppy.io — Cloudflare Tunnel 設定
# 公開URL: https://${HOSTNAME_PUBLIC}/floppy.io/
# 起動 / 停止は floppy_io リポジトリの ./tools/public.sh を使う。
tunnel: ${TUNNEL_NAME}
credentials-file: ${HOME}/.cloudflared/${uuid}.json

ingress:
  - hostname: ${HOSTNAME_PUBLIC}
    service: http://127.0.0.1:${WEB_PORT}
  - service: http_status:404
YAML
    echo "→ $CONFIG を作成しました"
  fi

  echo "→ DNS ルートを設定します ($HOSTNAME_PUBLIC)"
  # --config を明示しないと既定 (~/.cloudflared/config.yml = 別トンネル) を
  # 参照して、別トンネル向けの CNAME が作られてしまう。
  if ! cloudflared tunnel --config "$CONFIG" route dns "$TUNNEL_NAME" "$HOSTNAME_PUBLIC" 2>/dev/null; then
    echo "  → 既存レコードがあるため上書きします"
    cloudflared tunnel --config "$CONFIG" route dns --overwrite-dns \
      "$TUNNEL_NAME" "$HOSTNAME_PUBLIC"
  fi
}

start_api() {
  if port_busy "$API_PORT"; then
    echo "  API      : :$API_PORT は既に起動済み"
    return 0
  fi
  (cd backend && PORT="$API_PORT" nohup ./serve.sh >>"$LOG_DIR/api-supervisor.log" 2>&1 &)
  sleep 4
  if port_busy "$API_PORT"; then
    echo "  API      : :$API_PORT 起動 (自動再起動あり, ログ: $API_LOG)"
  else
    echo "  API      : ✗ 起動に失敗しました ($LOG_DIR/api-supervisor.log)"
    return 1
  fi
}

start_gateway() {
  if port_busy "$WEB_PORT"; then
    echo "  ゲートウェイ: :$WEB_PORT は既に起動済み"
    return 0
  fi
  nohup backend/.venv/bin/python tools/public_gateway.py >>"$GATEWAY_LOG" 2>&1 &
  echo $! >"$GATEWAY_PID"
  sleep 2
  if port_busy "$WEB_PORT"; then
    echo "  ゲートウェイ: :$WEB_PORT 起動 (ログ: $GATEWAY_LOG)"
  else
    echo "  ゲートウェイ: ✗ 起動に失敗しました ($GATEWAY_LOG)"
    return 1
  fi
}

start_tunnel() {
  if pid_alive "$TUNNEL_PID"; then
    echo "  トンネル  : 既に起動済み (PID $(cat "$TUNNEL_PID"))"
    return 0
  fi
  if [ ! -f "$CONFIG" ]; then
    echo "  トンネル  : ✗ $CONFIG がありません。先に ./tools/public.sh setup を実行してください"
    return 1
  fi
  nohup cloudflared tunnel --config "$CONFIG" run "$TUNNEL_NAME" >>"$TUNNEL_LOG" 2>&1 &
  echo $! >"$TUNNEL_PID"
  sleep 5
  if pid_alive "$TUNNEL_PID"; then
    echo "  トンネル  : $TUNNEL_NAME 起動 (ログ: $TUNNEL_LOG)"
  else
    echo "  トンネル  : ✗ 起動に失敗しました ($TUNNEL_LOG)"
    return 1
  fi
}

stop_all() {
  if pid_alive "$TUNNEL_PID"; then
    kill "$(cat "$TUNNEL_PID")" 2>/dev/null && echo "  トンネル  : 停止"
    rm -f "$TUNNEL_PID"
  fi
  if pid_alive "$GATEWAY_PID"; then
    kill "$(cat "$GATEWAY_PID")" 2>/dev/null && echo "  ゲートウェイ: 停止"
    rm -f "$GATEWAY_PID"
  fi
  if [ -f backend/logs/api.pid ] && kill -0 "$(cat backend/logs/api.pid)" 2>/dev/null; then
    kill "$(cat backend/logs/api.pid)" 2>/dev/null && echo "  API      : 停止"
  fi
  return 0
}

status() {
  echo "== floppy.io public status =="
  printf '  API (:%-4s)      : ' "$API_PORT"
  if curl -fsS -m 3 "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
    echo "OK"
  else
    echo "NG"
  fi
  printf '  ゲートウェイ (:%-4s): ' "$WEB_PORT"
  if curl -fsS -m 3 "http://127.0.0.1:$WEB_PORT/floppy.io/" >/dev/null 2>&1; then
    echo "OK"
  else
    echo "NG"
  fi
  printf '  トンネル (%s)    : ' "$TUNNEL_NAME"
  if pid_alive "$TUNNEL_PID"; then
    echo "OK (PID $(cat "$TUNNEL_PID"))"
  else
    echo "NG"
  fi
  printf '  公開URL           : '
  if curl -fsS -m 8 -o /dev/null "https://$HOSTNAME_PUBLIC/floppy.io/api/health" 2>/dev/null; then
    echo "OK  https://$HOSTNAME_PUBLIC/floppy.io/"
  else
    echo "NG  https://$HOSTNAME_PUBLIC/floppy.io/"
  fi
}

case "${1:-status}" in
  setup) setup ;;
  start)
    echo "→ floppy.io 公開サーバーを起動します"
    start_api && start_gateway && start_tunnel
    echo "→ https://$HOSTNAME_PUBLIC/floppy.io/"
    ;;
  ensure)
    # 落ちているものだけ起こす（launchd から 1 分ごとに呼ばれる想定。出力は静かに保つ）
    start_api >/dev/null 2>&1
    start_gateway >/dev/null 2>&1
    start_tunnel >/dev/null 2>&1
    exit 0
    ;;
  stop) stop_all ;;
  restart)
    stop_all
    sleep 1
    start_api && start_gateway && start_tunnel
    ;;
  status) status ;;
  *)
    sed -n '2,10p' "$0"
    exit 2
    ;;
esac
