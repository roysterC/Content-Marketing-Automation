#!/usr/bin/env bash
# Install (or update) the weekday cron jobs. Idempotent: replaces any older
# content-agent lines, including the previous `content-agent run` one.
#   07:00 weekdays  make the day's post package
#   12:00 weekdays  nudge about approved posts not yet marked as posted
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="cd $REPO_DIR && PATH=$HOME/.local/bin:\$PATH .venv/bin/content-agent"
DAILY_LINE="0 7 * * 1-5 $RUN daily >> logs/run.log 2>&1"
REMIND_LINE="0 12 * * 1-5 $RUN remind >> logs/run.log 2>&1"

mkdir -p "$REPO_DIR/logs"
(
  crontab -l 2>/dev/null | grep -v 'content-agent \(run\|daily\|remind\)' || true
  echo "$DAILY_LINE"
  echo "$REMIND_LINE"
) | crontab -
echo "Cron:"
crontab -l | grep 'content-agent'
