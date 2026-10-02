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
1. Install Claude Code (`npm install -g @anthropic-ai/claude-code`, or see the docs).
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

```cron
# Weekdays 07:00: research + drafts land in Telegram before the working day
0 7 * * 1-5  cd /opt/content-agent && .venv/bin/content-agent run >> logs/run.log 2>&1
```

Keep `content-agent bot` running under systemd (or `tmux`) so the buttons work.

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
