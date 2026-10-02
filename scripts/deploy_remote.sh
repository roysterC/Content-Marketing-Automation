#!/usr/bin/env bash
# Runs ON the VPS after GitHub Actions has synced the code. Called by
# .github/workflows/deploy.yml; you can also run it by hand after a manual sync.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."
export PATH="$HOME/.local/bin:$PATH"

if [ ! -d .venv ]; then
  echo "First deploy: running full setup"
  bash scripts/setup_vps.sh
fi

echo "Installing Python dependencies"
.venv/bin/pip install -q -e .

echo "Ensuring Chromium is installed (no-op if current)"
.venv/bin/playwright install chromium >/dev/null

if systemctl is-enabled --quiet content-agent-bot 2>/dev/null; then
  echo "Restarting approval bot"
  if [ "$(id -u)" -eq 0 ]; then
    systemctl restart content-agent-bot
  else
    sudo -n systemctl restart content-agent-bot
  fi
  systemctl is-active content-agent-bot
else
  echo "Approval bot service not enabled yet - skipping restart"
fi

echo "Deployed $(cat .deployed-sha 2>/dev/null || echo 'unknown version')"
