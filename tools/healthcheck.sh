#!/bin/sh
# floppy.io — 死活監視 / 自動復旧トリガー
#
#   ./tools/healthcheck.sh                     # 既定: http://127.0.0.1:8000/api/health
#   ./tools/healthcheck.sh http://127.0.0.1:8001/api/health
#   ./tools/healthcheck.sh --restart           # 異常なら FLOPPY_RESTART_CMD を実行
#
# 終了コード: 0 = 正常 / 1 = 異常 / 2 = 使い方の誤り
#
# cron で 5 分ごとに監視する例:
#   */5 * * * * cd /path/to/floppy_io && ./tools/healthcheck.sh >> logs/health.log 2>&1
set -u

URL="${FLOPPY_HEALTH_URL:-http://127.0.0.1:${PORT:-8000}/api/health}"
RESTART=0

for arg in "$@"; do
  case "$arg" in
    --restart) RESTART=1 ;;
    http://* | https://*) URL="$arg" ;;
    -h | --help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "使い方: $0 [--restart] [health-url]" >&2
      exit 2
      ;;
  esac
done

if ! command -v curl >/dev/null 2>&1; then
  echo "✗ curl が見つかりません" >&2
  exit 2
fi

body=$(curl -fsS -m 5 "$URL" 2>/dev/null)
status=$?

if [ "$status" -eq 0 ]; then
  echo "OK   $URL"
  echo "$body"
  exit 0
fi

echo "NG   $URL (curl exit $status)" >&2

if [ "$RESTART" -eq 1 ]; then
  if [ -n "${FLOPPY_RESTART_CMD:-}" ]; then
    echo "→ 再起動します: $FLOPPY_RESTART_CMD" >&2
    sh -c "$FLOPPY_RESTART_CMD" || true
  else
    echo "→ FLOPPY_RESTART_CMD が未設定のため再起動しません" >&2
  fi
fi

exit 1
