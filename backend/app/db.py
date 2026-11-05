# floppy.io — MySQL 接続 (PyMySQL)
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import pymysql
from pymysql.constants import FIELD_TYPE
from pymysql.converters import conversions
from pymysql.cursors import DictCursor

from .config import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER


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


@contextmanager
def cursor() -> Iterator[DictCursor]:
    connection = connect()
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
