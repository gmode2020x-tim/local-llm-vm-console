#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/local-llm-vm-console}"
sudo mkdir -p "$APP_DIR"
sudo rsync -a --delete --exclude runtime --exclude .git ./ "$APP_DIR/"
sudo cp "$APP_DIR/deploy/linux/local-llm-ui.service" /etc/systemd/system/local-llm-ui.service
sudo systemctl daemon-reload
sudo systemctl enable --now local-llm-ui.service
sudo systemctl status --no-pager local-llm-ui.service
