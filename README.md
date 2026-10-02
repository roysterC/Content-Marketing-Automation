# Content-Marketing-Automation

Phase 1 of the content agent described in [`CLAUDE.md`](CLAUDE.md): it finds post ideas,
drafts LinkedIn and Facebook posts, renders carousels, and sends everything to Telegram
for approval. Nothing gets published automatically. You approve a post, then post it yourself.

```
RSS / Reddit feeds ──► ingest ──► score (Claude) ──► draft + fact-check (Claude)
                                                          │
            Telegram  ◄── review ◄── render carousel PDF ◄┘
       Approve / Edit / Reject
```

## Setup

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
playwright install --with-deps chromium     # or set CHROMIUM_PATH in .env
cp .env.example .env                         # then fill it in
```

Claude access: by default this uses your Claude Pro or Max plan through the
[Claude Code](https://code.claude.com) CLI. You don't need an API key.
1. Install Claude Code, then open a new terminal and check that `claude --version` works:
   - macOS, Linux, WSL: `curl -fsSL https://claude.ai/install.sh | bash`
   - Windows PowerShell: `irm https://claude.ai/install.ps1 | iex`
   - If you get `claude: command not found`, add `~/.local/bin` to your PATH:
     `echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc`
2. On your own machine, run `claude` once and log in.
   On a VPS with no browser, run `claude setup-token` on any machine. It prints a token
   that lasts one year. Put it in `.env` as `CLAUDE_CODE_OAUTH_TOKEN=...`.

If you'd rather pay per token, set `LLM_BACKEND=api` and `ANTHROPIC_API_KEY`.

Telegram bot setup:
1. Message [@BotFather](https://t.me/BotFather) and send `/newbot`. Put the token in `TELEGRAM_BOT_TOKEN`.
2. Send your new bot any message, then open `https://api.telegram.org/bot<TOKEN>/getUpdates`
   and copy `message.chat.id` into `TELEGRAM_CHAT_ID`.

## Commands

| Command | What it does |
|---|---|
| `content-agent ingest` | Fetch the feeds in `config/sources.yaml` and store new items, skipping duplicates |
| `content-agent score` | Claude scores each new item 0–10 for your target reader and suggests an angle |
| `content-agent draft --limit 3` | Draft LinkedIn, Facebook and carousel versions of the top ideas, then fact-check them |
| `content-agent brief notes.txt --pillar proof` | Draft a post from your own notes (case studies, offers). Only facts in your notes are used |
| `content-agent render` | Render the carousel PDFs (LinkedIn document posts) and cover PNGs into `output/` |
| `content-agent review` | Send pending drafts to Telegram with Approve / Edit / Reject buttons |
| `content-agent bot` | Long-running process that handles the button presses and edits (`/pending` resends drafts) |
| `content-agent run` | ingest → score → draft → render → review in one go |

How approval works: **Approve** marks the draft as ready to post. **Reject** discards it.
**Edit** asks you to reply with the new text, then sends the updated draft back for approval.
The fact-check results appear on each draft. Nothing is auto-rejected, so the final call is yours.

## Running it on a VPS

SSH in from your own computer's terminal rather than the provider's web console, so that
copy and paste work. Then run:

```bash
git clone -b claude/focused-goldberg-w0p7ka https://github.com/roysterc/content-marketing-automation.git ~/Content-Marketing-Automation
cd ~/Content-Marketing-Automation && bash scripts/setup_vps.sh
```

The script installs everything (system packages, Claude Code, Python env, Chromium), creates
`.env`, installs a systemd service for the Telegram bot and adds the weekday cron job.
It finishes by printing the steps that need you: `claude setup-token` and the Telegram settings.
It's safe to re-run. What it sets up:

- a systemd service, `content-agent-bot`, that keeps the Telegram buttons working
- a cron job that runs `content-agent run` on weekdays at 07:00 server time, so drafts arrive before the working day

### Automatic deploys from GitHub

`.github/workflows/deploy.yml` runs the tests on every push and pull request. On a push to
`main`, it then copies the code to the VPS with rsync, installs dependencies and restarts
the bot. Your `.env`, database, rendered files and logs on the server are never touched.
Everything else matches `main`, so edit config files such as `brand_voice.md` and
`examples/` in the repo, not on the server.

One-time setup:

1. **Create a key just for deploys** on your own computer, so you aren't handing your
   personal SSH key to GitHub:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/content_agent_deploy -N "" -C "github-deploy"
   ssh-copy-id -i ~/.ssh/content_agent_deploy.pub YOUR_USER@YOUR_VPS_IP
   ```
2. **Get the server's fingerprint**, so GitHub can check it's talking to your real server:
   ```bash
   ssh-keyscan -p 22 YOUR_VPS_IP
   ```
3. **Add the repository secrets** under GitHub → Settings → Secrets and variables → Actions:

   | Secret | Value |
   |---|---|
   | `VPS_HOST` | the server's IP address or hostname |
   | `VPS_USER` | the SSH user, e.g. `root` |
   | `VPS_SSH_KEY` | the entire contents of `~/.ssh/content_agent_deploy`, the private key |
   | `VPS_KNOWN_HOSTS` | the full output of the `ssh-keyscan` command |
   | `VPS_PORT` | optional; only needed if SSH isn't on port 22 |

4. **Run `scripts/setup_vps.sh` once by hand** on the server, as shown above. Later deploys
   only update and restart. If you deploy as a user other than root, that user needs
   passwordless sudo for `systemctl restart content-agent-bot`.

To redeploy without pushing, go to the Actions tab → **Test and deploy** → **Run workflow**.

## What to customise

- `config/sources.yaml`: research feeds. Any RSS/Atom URL works.
- `config/brand_voice.md`: tone and format rules sent with every draft.
- `config/examples/`: 10–20 example posts in the style you want. This has the biggest effect on draft quality.
- `src/content_agent/prompts.py`: the audience description and hard rules, such as never inventing numbers.
- `src/content_agent/visuals/templates/carousel.html`: carousel design. Edit the CSS variables at the top to change the brand colours.

## Cost and usage notes

- **On your plan (default):** there's no per-token bill. Each run uses part of your plan's
  usage limits, which are shared with your normal Claude and Claude Code use. A typical run
  is one scoring call per 20 items plus two calls per drafted idea. If a scheduled run
  hits your limit, the calls fail and the next run picks up where it stopped.
- The `total_cost_usd` figure in Claude Code's output is an estimate of the API price.
  You aren't charged it on a subscription.
- Scoring runs at low effort, so it's the light step. Drafting and fact-checking run at higher effort.
  `--limit` caps how many ideas get drafted each run.
- The default model is `CLAUDE_MODEL=claude-opus-5-5`. You can change it in `.env`.

## Development

```bash
pytest          # offline tests: no API, network or Telegram calls
ruff check src tests && ruff format src tests
```

Data lives in SQLite at `data/content_agent.db` by default. To use Postgres or Supabase,
point `DATABASE_URL` at it and install the extra with `pip install -e '.[postgres]'`.
