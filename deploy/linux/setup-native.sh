#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
mkdir -p runtime/ui-data/logs

cat <<'MSG'

Native setup complete.
Start UI:
  set -a
  source .env
  set +a
  .venv/bin/gunicorn -w 2 -b 0.0.0.0:${PORT:-8068} app.app:app

Install autostart:
  sudo APP_DIR=/opt/local-llm-vm-console ./deploy/linux/install-systemd.sh

Open:
  http://127.0.0.1:8068
MSG
