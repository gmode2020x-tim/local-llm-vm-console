#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/local-llm-vm-console}"
sudo mkdir -p "$APP_DIR"
sudo rsync -a --delete --exclude runtime --exclude .git --exclude .venv ./ "$APP_DIR/"
if [ ! -f "$APP_DIR/.env" ]; then
  sudo cp "$APP_DIR/.env.example" "$APP_DIR/.env"
fi
sudo python3 -m venv "$APP_DIR/.venv"
sudo "$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
sudo "$APP_DIR/.venv/bin/python" -m pip install -r "$APP_DIR/requirements.txt"
sudo mkdir -p "$APP_DIR/runtime/ui-data/logs"
sudo cp "$APP_DIR/deploy/linux/local-llm-ui.service" /etc/systemd/system/local-llm-ui.service
sudo systemctl daemon-reload
sudo systemctl enable --now local-llm-ui.service
sudo systemctl status --no-pager local-llm-ui.service
