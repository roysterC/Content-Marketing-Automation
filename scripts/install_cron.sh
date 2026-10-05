#!/usr/bin/env bash
# Install (or update) the weekday morning cron job. Idempotent: replaces any older
# content-agent line, including the previous `content-agent run` one.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CRON_LINE="0 7 * * 1-5 cd $REPO_DIR && PATH=$HOME/.local/bin:\$PATH .venv/bin/content-agent daily >> logs/run.log 2>&1"

mkdir -p "$REPO_DIR/logs"
( crontab -l 2>/dev/null | grep -v 'content-agent \(run\|daily\)' || true; echo "$CRON_LINE" ) | crontab -
echo "Cron: $(crontab -l | grep 'content-agent daily')"
