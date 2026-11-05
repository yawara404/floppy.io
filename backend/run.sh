#!/usr/bin/env bash
# floppy.io — Python API 開発サーバー
set -euo pipefail

cd "$(dirname "$0")"

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

exec uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}" --reload
