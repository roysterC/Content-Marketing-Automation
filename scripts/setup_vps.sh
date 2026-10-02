#!/usr/bin/env bash
# One-shot VPS setup for the content agent (Ubuntu 24.04+ / Debian 12+).
#
# Run from inside the cloned repo:
#   bash scripts/setup_vps.sh
#
# Safe to re-run: every step skips work that's already done.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

say() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

say "System packages"
$SUDO apt-get update -qq
$SUDO apt-get install -y -qq git curl python3 python3-venv python3-pip >/dev/null

if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))'; then
  echo "Python 3.11+ is required (found $(python3 --version)). Use Ubuntu 24.04+ or Debian 12+." >&2
  exit 1
fi

say "Claude Code CLI"
export PATH="$HOME/.local/bin:$PATH"
if ! command -v claude >/dev/null; then
  curl -fsSL https://claude.ai/install.sh | bash
fi
if ! grep -q '.local/bin' "$HOME/.bashrc" 2>/dev/null; then
  # shellcheck disable=SC2016  # written literally so it expands at login
  echo 'export PATH="$HOME/.local/bin:$PATH"' >>"$HOME/.bashrc"
fi
claude --version

say "Python environment"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -e .

say "Chromium for carousel rendering"
$SUDO .venv/bin/playwright install-deps chromium >/dev/null
.venv/bin/playwright install chromium

say "Config"
if [ ! -f .env ]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env from .env.example"
else
  echo ".env already exists - left unchanged"
fi
mkdir -p logs

say "Telegram bot service (systemd)"
SERVICE=/etc/systemd/system/content-agent-bot.service
$SUDO tee "$SERVICE" >/dev/null <<EOF
[Unit]
Description=Content agent Telegram approval bot
After=network-online.target
Wants=network-online.target

[Service]
User=$(id -un)
WorkingDirectory=$REPO_DIR
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=$REPO_DIR/.venv/bin/content-agent bot
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
$SUDO systemctl daemon-reload
echo "Installed $SERVICE (not started yet - needs Telegram settings in .env)"

say "Daily cron job (weekdays 07:00 server time)"
CRON_LINE="0 7 * * 1-5 cd $REPO_DIR && PATH=$HOME/.local/bin:\$PATH .venv/bin/content-agent run >> logs/run.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'content-agent run' || true; echo "$CRON_LINE" ) | crontab -
crontab -l | grep 'content-agent run'

cat <<EOF

$(say "Done. Remaining steps (need you):")
1. Get a Claude token for your Pro/Max plan:
     claude setup-token
   Copy the URL into your browser, approve, paste the code back, then put the
   printed token in .env as CLAUDE_CODE_OAUTH_TOKEN=...

2. Fill in TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env:
     nano $REPO_DIR/.env

3. Test a small run:
     cd $REPO_DIR && .venv/bin/content-agent ingest && .venv/bin/content-agent score --limit 20

4. Start the approval bot:
     $SUDO systemctl enable --now content-agent-bot
     journalctl -u content-agent-bot -f      # watch its log
EOF
