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
# 接続情報は backend/config/database.php と同じ（root / root / floppy_io）。
# MAMP / MAMP PRO の MySQL は TCP を無効化していることがあるため、
# 既定では unix ソケット経由で接続する。
#
# 環境変数で上書きできる:
#   FLOPPY_DB_SOCKET=/path/to/mysql.sock ./tools/db.sh "SHOW TABLES;"
#   FLOPPY_DB_HOST=127.0.0.1 FLOPPY_DB_PORT=3306 ./tools/db.sh -e "SHOW TABLES;"

MYSQL="${MYSQL_BIN:-/Applications/MAMP/Library/bin/mysql80/bin/mysql}"
SOCKET="${FLOPPY_DB_SOCKET:-/Applications/MAMP/tmp/mysql/mysql.sock}"
DB_USER="${FLOPPY_DB_USER:-root}"
DB_PASS="${FLOPPY_DB_PASS:-root}"
DB_NAME="${FLOPPY_DB_NAME:-floppy_io}"

if [ ! -x "$MYSQL" ]; then
    echo "mysql コマンドが見つかりません: $MYSQL" >&2
    echo "MYSQL_BIN 環境変数で指定してください。" >&2
    exit 1
fi

# 接続オプションを付けて mysql を実行する
mysql_run() {
    if [ -S "$SOCKET" ]; then
        "$MYSQL" -u "$DB_USER" -p"$DB_PASS" --socket="$SOCKET" "$@"
    else
        "$MYSQL" -u "$DB_USER" -p"$DB_PASS" \
            -h "${FLOPPY_DB_HOST:-127.0.0.1}" -P "${FLOPPY_DB_PORT:-3306}" "$@"
    fi
}

# 引数なし → 対話シェル
if [ $# -eq 0 ]; then
    mysql_run "$DB_NAME"
    exit $?
fi

# 先頭がオプション (-) なら mysql にそのまま渡す（DB 名は先に付ける）
case "$1" in
    -*)
        mysql_run "$DB_NAME" "$@"
        exit $?
        ;;
esac

# それ以外は SQL 文として実行する
QUERY="$*"
mysql_run "$DB_NAME" -e "$QUERY"
exit $?
