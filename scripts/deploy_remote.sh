#!/usr/bin/env bash
# Runs ON the VPS after the deploy workflow has reset the checkout to the pushed
# commit (.github/workflows/deploy.yml). You can also run it by hand.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PATH="$HOME/.local/bin:$PATH"
SERVICE=content-agent-bot

if [ ! -d .venv ]; then
  echo "==> First deploy: running full setup"
  bash scripts/setup_vps.sh
fi

echo "==> Installing Python dependencies"
.venv/bin/pip install -q -e .

echo "==> Ensuring Chromium is installed (no-op if current)"
.venv/bin/playwright install chromium >/dev/null

if systemctl is-enabled --quiet "$SERVICE" 2>/dev/null; then
  echo "==> Restarting $SERVICE"
  if [ "$(id -u)" -eq 0 ]; then SUDO=""; else SUDO="sudo -n"; fi
  $SUDO systemctl restart "$SERVICE"
  # Give it a moment to fall over: a unit that exits on boot would otherwise be
  # reported as a green deploy.
  sleep 5
  systemctl is-active --quiet "$SERVICE" || {
    echo "ERROR: $SERVICE is not active after restart." >&2
    systemctl status "$SERVICE" --no-pager --lines=40 >&2 || true
    exit 1
  }
else
  echo "==> $SERVICE not enabled yet (needs Telegram settings in .env) - skipping restart"
fi

echo "==> Deploy complete: $(git rev-parse --short HEAD)"
