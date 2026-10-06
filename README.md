# Content-Marketing-Automation

Phase 1 of the content agent described in [`CLAUDE.md`](CLAUDE.md). Every weekday morning
it picks a post format at random, researches a topic for a business type on the web,
writes the LinkedIn and Facebook posts, renders a single-image visual and a carousel,
and sends the package to Telegram for approval. Nothing is published automatically: you
approve a post, then post it yourself.

```
07:00 weekdays: content-agent daily
  pick format (75% idea, 25% team)  →  pick business type (not one used recently)
    →  Claude researches (web) + writes posts, visual and carousel
    →  fact-check  →  render visual + carousel (text-fit check)
    →  Telegram: Approve / Edit / Reject
```

Formats live in `src/content_agent/formats/` and their settings in `config/formats.yaml`:
- **idea**: one concrete automation for a business type, shown as an infographic
  (problem → how it works → outcomes).
- **team**: "Your Barbershop's AI Team", the business's everyday jobs as automation "staff"
  on an org chart.

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
| `content-agent daily` | The morning run (what the cron calls): picks a format by the weights in `config/formats.yaml`, builds `posts_per_day` packages and sends them to Telegram |
| `content-agent make idea --sector "nail salons"` | One package in a specific format (`idea` or `team`), on demand. Leave out `--sector` for a weighted random business type |
| `content-agent brief notes.txt --pillar proof` | Draft a post from your own notes (case studies, offers). Only facts in your notes are used |
| `content-agent paint 12 --style watercolour` | Print the Gemini prompt for draft 12's painted image, optionally in another art style |
| `content-agent remind` | Remind you in Telegram about approved drafts not yet marked posted (cron, 12:00 weekdays) |
| `content-agent review` | Send any pending drafts to Telegram with Approve / Edit / Reject buttons |
| `content-agent bot` | Long-running process that handles the button presses, edits and commands |

Manual extras, not part of the morning run: `ingest` → `score` → `draft` → `render` work
from the trade and AI-news feeds in `config/sources.yaml`.

From your phone, the bot takes:
- `/daily`: today's random format.
- `/idea` or `/idea dog groomers`, `/team` or `/team barbers`: a specific format.
- `/pending`: resend drafts you haven't reviewed.
- `/paint`, `/paint 12` or `/paint watercolour`: resend the Gemini prompt for the latest
  draft (or draft 12), optionally in another art style.

Each package takes a few minutes, and the bot keeps handling your buttons meanwhile.

To change the mix, edit `config/formats.yaml` (format weights, business types and their
weights, posts per day) and merge to `main`. To add a format, add a module in
`src/content_agent/formats/` and register it in `FORMATS`; it gets a Telegram command
automatically.

Every visual goes through a text-fit check. The templates shrink text to fit the canvas,
and any visual that needed shrinking below 85% gets its wording shortened by Claude in one
quick extra call, then re-rendered, so text stays readable on a phone.

### Painted images (Gemini, free)

The HTML infographic is clean but flat. For a painted look, each package also comes with
a paste-ready prompt for the Gemini app, where Nano Banana image generation is free (it
has no free API, and scripting the app would break Google's terms, so this step is
manual):
1. Under the LinkedIn draft, the bot sends the steps, then the prompt on its own. Copy it
   into the Gemini app and send.
2. Reply to either message with the image Gemini makes, sent as a file so Telegram doesn't
   compress it. An image sent without a reply goes to the latest draft.
3. The bot saves it for the LinkedIn and Facebook drafts, and Claude proofreads it against
   the approved copy: misspellings, missing text, or any words or numbers the image model
   added. The result comes back as ✅ or ⚠️ with the problems listed.
4. The posting kit then uses it: the Facebook kit attaches it instead of the HTML
   infographic, and the LinkedIn kit offers it as an alternative to the carousel PDF.

The prompt fixes the look and leaves the layout to Nano Banana, so posts vary in
composition without drifting in style:
- **Fixed** (`config/art_style.yaml`, repeated word for word): painting technique,
  background, font, colours, line weight, box style and icon style. There are three
  styles to compare (`gouache`, `watercolour`, `painterly`) and an `active` one.
- **Data**: the exact approved text (headline, problem, steps, figures, call to action,
  signature), so nothing new gets past the fact-check.
- **Free**: layout, composition, hierarchy and illustration. Nano Banana designs those. Sample prompts for all three
are in [`docs/painted-style-samples.md`](docs/painted-style-samples.md). Once you have an
image you like, attach it in Gemini as a style reference with each prompt: that's the
strongest way to keep the look consistent.

How approval works: **Edit** asks you to reply with the new text, then sends the updated
draft back for approval. **Reject** discards it. The fact-check results appear on each draft.
Nothing is auto-rejected, so the final call is yours.

**Approve** sends a posting kit. You post by hand from your phone, in about 2–3 minutes:
1. A short checklist.
2. The post text on its own, so long-press → Copy gets exactly the text.
3. The file to attach. LinkedIn gets the carousel PDF, with the document title LinkedIn
   asks for in its caption. Facebook gets the infographic.
4. LinkedIn only: the first comment on its own.
5. A **✅ Posted** button. Tap it once the post is live, then optionally reply with the
   post's link. That records what went out and when, for the Phase 4 analytics.

At 12:00 on weekdays the bot reminds you about anything approved but not yet marked
posted. Each reminder has a **🔁 Resend kit** button.

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
- cron jobs: `content-agent daily` at 07:00 on weekdays, so drafts arrive before the
  working day, and `content-agent remind` at 12:00. Every deploy re-applies them, so
  changes ship automatically.

### Automatic deploys from GitHub

`.github/workflows/deploy.yml` works the same way as the call-assistant deploy. It runs
the tests on every push and pull request. On a push to `main` it SSHes into the VPS with
`appleboy/ssh-action`, checks out exactly the pushed commit in `~/Content-Marketing-Automation`,
installs dependencies and restarts the bot.

Git-ignored files on the server are never touched: `.env`, `data/`, `output/`, `.venv/` and
`logs/`. Edit everything else in the repo, not on the server. That includes
`config/brand_voice.md` and `config/examples/`; changes made on the server are lost at the
next deploy.

Secrets (GitHub → Settings → Secrets and variables → Actions):

| Secret | Value |
|---|---|
| `VPS_HOST` | the server's IP address or hostname |
| `VPS_USER` | the SSH user, e.g. `root` |
| `VPS_SSH_KEY` | a private key whose public half is in the server's `~/.ssh/authorized_keys` |
| `VPS_PORT` | optional; only needed if SSH isn't on port 22 |

The first deploy runs `scripts/setup_vps.sh` automatically if `.venv` doesn't exist yet.
That needs root, or passwordless sudo for the deploy user. To redeploy without pushing, go to
Actions → **Test and deploy** → **Run workflow**.

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
