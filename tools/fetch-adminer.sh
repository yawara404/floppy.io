#!/bin/sh
#
# floppy.io — Adminer（DB 管理画面）を取得 / 更新する
#
#   ./tools/fetch-adminer.sh
#
# backend/db/adminer.php はサードパーティ製（Adminer 本体）なので、
# リポジトリにコミットしたくない場合は .gitignore で除外し、
# このスクリプトで取得してください。

set -e

DEST="$(dirname "$0")/../backend/db/adminer.php"
URL="${ADMINER_URL:-https://www.adminer.org/latest.php}"

if [ -f "$DEST" ]; then
    echo "既存の adminer.php を上書きします: $DEST"
fi

mkdir -p "$(dirname "$DEST")"
curl -fsSL --max-time 120 -o "$DEST.tmp" "$URL"
mv "$DEST.tmp" "$DEST"

echo "取得しました: $DEST"
head -c 200 "$DEST" | grep -o 'Adminer - Compact database management' >/dev/null 2>&1 \
    && echo "（Adminer 本体を確認）" \
    || echo "警告: Adminer 本体ではない可能性があります"
