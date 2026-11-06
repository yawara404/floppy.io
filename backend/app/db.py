# floppy.io — MySQL 接続 (PyMySQL)
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Iterator

import pymysql
from pymysql.constants import FIELD_TYPE
from pymysql.converters import conversions
from pymysql.cursors import DictCursor

from .config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

# MySQL の再起動中など「接続自体に失敗した」ときだけ 1 回だけ再試行する。
# クエリ送信後のリトライは二重書き込みの恐れがあるため行わない。
_RETRYABLE_CONNECT_ERRNO = 2003  # CR_CONN_HOST_ERROR: Can't connect to MySQL server
_CONNECT_RETRY_DELAY_SECONDS = 0.3


def _to_text(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", "replace")
    return str(value)


# フロントエンドは "YYYY-MM-DD HH:MM:SS" をそのまま表示する
_CONV = conversions.copy()
_CONV[FIELD_TYPE.DATETIME] = _to_text
_CONV[FIELD_TYPE.TIMESTAMP] = _to_text


def connect() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        conv=_CONV,
        connect_timeout=5,
        read_timeout=15,
        write_timeout=15,
    )


def _connect_with_retry() -> pymysql.connections.Connection:
    try:
        return connect()
    except pymysql.err.OperationalError as exc:
        if not exc.args or exc.args[0] != _RETRYABLE_CONNECT_ERRNO:
            raise
        # MySQL の再起動直後など。少し待って 1 回だけやり直す。
        time.sleep(_CONNECT_RETRY_DELAY_SECONDS)
        return connect()


@contextmanager
def cursor() -> Iterator[DictCursor]:
    connection = _connect_with_retry()
    try:
        with connection.cursor() as cur:
            yield cur
    finally:
        connection.close()


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall())


def execute(sql: str, params: tuple[Any, ...] = ()) -> int:
    with cursor() as cur:
        cur.execute(sql, params)
        return int(cur.lastrowid or 0)
