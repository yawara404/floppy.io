#!/bin/sh
#
# floppy.io — コマンドラインからデータベースを操作する
#
# 使い方:
#   ./tools/db.sh                          # 対話シェル（SQL を直接入力）
#   ./tools/db.sh "SELECT * FROM users;"   # 1 クエリだけ実行
#   ./tools/db.sh < database/schema.sql    # SQL ファイルを流し込む
#   ./tools/db.sh -e "SHOW TABLES;"        # mysql のオプションを直接指定
#
# 接続情報は backend/.env / 環境変数 (FLOPPY_DB_*) と同じ。
# 既定: 127.0.0.1:3306 / floppy_io / floppy / floppy
#
# mysql クライアントは PATH 上のものを使う（MYSQL_BIN で上書き可能）。

MYSQL="${MYSQL_BIN:-mysql}"
DB_HOST="${FLOPPY_DB_HOST:-127.0.0.1}"
DB_PORT="${FLOPPY_DB_PORT:-3306}"
DB_USER="${FLOPPY_DB_USER:-floppy}"
DB_PASS="${FLOPPY_DB_PASS:-floppy}"
DB_NAME="${FLOPPY_DB_NAME:-floppy_io}"

if ! command -v "$MYSQL" >/dev/null 2>&1; then
    echo "mysql クライアントが見つかりません: $MYSQL" >&2
    echo "MySQL をインストールするか、MYSQL_BIN でパスを指定してください。" >&2
    exit 1
fi

# パスワードをコマンドライン履歴に残さない
run_mysql() {
    MYSQL_PWD="$DB_PASS" "$MYSQL" \
        -u "$DB_USER" \
        -h "$DB_HOST" \
        -P "$DB_PORT" \
        --default-character-set=utf8mb4 \
        "$DB_NAME" \
        "$@"
}

# 引数なし → 対話シェル
if [ $# -eq 0 ]; then
    run_mysql
    exit $?
fi

# 先頭がオプション (-) なら mysql にそのまま渡す
case "$1" in
    -*)
        run_mysql "$@"
        exit $?
        ;;
esac

# それ以外は SQL 文として実行する
run_mysql -e "$*"
