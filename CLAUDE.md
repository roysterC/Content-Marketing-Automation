# AI Content Agent — Project Brief

## Purpose
Automate a social media presence (LinkedIn + Facebook) that wins **clients for Roy's AI automation services business**. This is a services/lead-gen account, NOT an audience-first account. Success = booked discovery calls from business owners, not follower count.

- Not restricted to one vertical. **Initial client focus:** appointment-based businesses that rely heavily on phone bookings — nail salons, hair salons/barbers, beauty clinics and similar (core pain: missed calls = missed bookings, staff tied up on the phone, no-shows).
- Content scope is broader: any industry where automation delivers high value (e.g. travel agencies, trades, clinics, professional services) is fair game for posts.
- Reader: busy small-business owner who cares about saved hours, missed leads and staff cost — not about AI itself
- Owner: Roy, UK-based software engineer (comfortable with Python/TS, cost-conscious, prefers understanding the "why" behind design decisions)

## Content strategy
- Lead with business problems; AI stays in the background. Plain language, no jargon ("RAG", "agentic").
- Pillars (approx. mix):
  - Workflow breakdowns: "how a salon / [business type] could automate X" (~40%)
  - Proof: case studies, before/after numbers, screen recordings of automations running (~30%)
  - Industry problem posts tied to AI news only where it matters to SMBs (~20%)
  - Direct offer / lead magnet posts (~10%)
- Lower volume, higher depth. Every post is a sales asset.
- LinkedIn: post from Roy's **personal profile** (not a company page). Strong 2-line hook. External links go in the **first comment**, not the post body. Carousels (PDF document posts) are a priority format.
- Facebook: shorter, more conversational variant. Never cross-post identical copy.

## Pipeline
1. **Pick + research** — each weekday morning the generator picks a content format at random
   (weights in `config/formats.yaml`: currently 75% `idea`, 25% `team`) and a business type
   (weighted towards the initial focus, avoiding recently used ones). Claude researches the
   topic with live web search. RSS feeds are no longer part of the daily run (Reddit removed
   as too noisy); `ingest`/`score`/`draft` remain as manual extras.
2. **Draft** — Claude writes the whole package: LinkedIn + Facebook drafts, the format's
   single-image visual and a carousel, using a brand-voice file + 10–20 example posts.
   One package per morning (lower volume, higher depth).
3. **Visuals** — primarily HTML templates rendered to PNG/PDF via Playwright (branded, consistent carousels/diagrams). For a painted look, every package also gets a Gemini (Nano Banana) prompt for its single-image visual: Roy makes the image in the free Gemini app and sends it back to the bot, which proofreads its text against the approved copy (`visuals/paint.py`, art style in `config/art_style.yaml`).
4. **Human review gate** — drafts sent to Slack or Telegram with Approve / Edit / Reject. Nothing publishes without approval.
5. **Publish** — Roy posts by hand from a Telegram **posting kit** (no paid scheduler: Roy
   ruled out any cost). Direct publishing through the free official APIs (Facebook Page via
   the Graph API, LinkedIn via self-serve "Share on LinkedIn", Instagram optional) is
   **deferred**; revisit only if manual posting becomes a chore. The kit stays the fallback.
6. **Engage** — Facebook: comment-keyword → DM lead magnet via Messenger tooling (e.g. ManyChat). LinkedIn: agent **drafts** replies/DMs for Roy to send manually.
7. **Lead funnel** — lead magnet → landing page w/ email capture → short nurture sequence → Cal.com booking → CRM.
8. **Analytics** — weekly metric pull, tag posts by pillar/hook/format, feed top performers back into drafting prompts.

## Design standard (applies to every visual)
- Every design must look **professional and visually pleasing**: infographic first, never a
  wall of text. Think diagrams, numbered flows, big-number stats, before/after comparisons,
  icon card grids and checklists, not title-plus-paragraph slides.
- One consistent brand system across all visuals: the shared colour tokens, Inter, the line
  icons in `src/content_agent/visuals/icons.py`, generous spacing, and the author footer.
- Carousels use the layout system in `visuals/templates/carousel.html` (cover, steps,
  stats, compare, checklist, grid, insight, cta). The cover comes first and the CTA last,
  every slide in between is a visual layout, at least three different layouts per carousel,
  and at most one text-led "insight" slide.
- Text must fit its space. Templates shrink text to fit; keep copy within the word limits in
  `prompts.py` (`DESIGN_RULES`).
- Any new template must meet the same bar. Render it and check it before it ships.

## Hard constraints
- **No automated LinkedIn actions** beyond posting (no auto DMs, connection requests, comments, likes) — ToS violation, ban risk.
- Facebook Messenger automation must stay within Meta messaging policy.
- No fabricated case studies, testimonials or metrics. Proof content must come from real work Roy supplies.
- Fact-check pass on any claim about AI products/releases before it reaches the review gate.
- Keep running costs low; prefer self-hosted / free tiers where reasonable.

## Proposed stack
- Python service on a small VPS, cron for scheduling (n8n self-hosted is an acceptable alternative)
- Postgres / Supabase: sources, content queue, post status, metrics
- Claude (via Claude Code CLI on Roy's plan, or the API) for scoring, drafting, fact-check
- Playwright for template rendering
- Slack or Telegram bot for approvals
- Scheduler API for publishing
- MailerLite or ConvertKit, Cal.com, ManyChat (Facebook)

## Build order
1. **Phase 1 (start here):** research ingest → drafting → visual templates → Slack/Telegram approval. Roy posts manually; judge quality.
2. **Phase 2:** publishing. Done as manual posting from a Telegram posting kit; API
   automation deferred.
3. **Phase 3:** lead magnet, landing page, email nurture, Facebook comment-to-DM.
4. **Phase 4:** analytics feedback loop (once ~30 posts of data exist).

## Status (update as phases progress)
- **Phase 1: built and running on the VPS.** One morning generator (`content-agent daily`,
  `src/content_agent/generate.py`) over a format registry (`src/content_agent/formats/`:
  `idea`, `team`), web research, fact-check, single-image visual + infographic-first
  carousel with a text-fit check, Telegram approval (`/daily`, `/idea`, `/team`,
  `/pending`), `brief` for Roy's own material, weekday 07:00 cron, auto-deploy from `main`.
  Still open: Roy's example posts and brand-voice edits; SQLite (not Postgres) is fine for
  now. Next format candidate: "industry problem" with its own poster.
  Painted images: semi-manual via the free Gemini app (prompt in Telegram → Roy replies
  with the image → Claude text check → used in the kit). Art style: **`painterly`**
  (Roy's pick); the prompt fixes the design system and leaves layout to Nano Banana.
- **Phase 2: complete (manual posting).** Approve → copyable post text, attachment
  (carousel PDF with its LinkedIn document title, or the infographic), first comment, and a
  ✅ Posted button (records `posted_at` and an optional `post_url`); 12:00 weekday
  reminders. Direct API publishing deferred (findings: Facebook Page = easiest, token doesn't
  expire; LinkedIn self-serve = 60-day logins with no auto-refresh, PDF documents unproven,
  no engagement stats for self-serve apps; Instagram = needs publicly hosted JPEGs).
- **Phase 3: not started.**
- **Phase 4: not started.** Needs ~30 published posts.
- Content quality is improved iteratively alongside every phase (prompts, templates,
  examples, feedback from Roy's edits and rejections).

## Decisions made
- Approvals: **Telegram** (free, works well on a phone, simple bot API)
- Orchestration: **Python service + cron** (code lives in `src/content_agent/`, see README)
- Claude access: **Roy's Claude Pro/Max plan via the Claude Code CLI** (`claude -p`, `LLM_BACKEND=claude_code`) to avoid API costs; the pay-per-token API backend stays available (`LLM_BACKEND=api`)

- Content generation: **one shared pipeline over pluggable formats**; one package per weekday
  morning; format chosen by weighted random (75% idea / 25% team); feeds out of the daily run

- Publishing: **no paid scheduler; Roy posts manually from the posting kit.** API automation
  deferred

- Painted images: **Gemini app by hand (free), not an image API.** The app has no API and
  scripting it breaks Google's terms; the paid API (~£2–4/month for Nano Banana 2) is the
  upgrade path if the manual step becomes a chore. Research: `docs/research/infographic-image-tools.md`

## Open decisions
- If API publishing is revisited: whether the LinkedIn first comment may be posted through
  the API (Roy's own comment on his own post, but "no automated comments" is a hard rule),
  and whether Instagram is in scope
- First lead magnet topic (candidate: "The 5 automations every salon should run to stop losing bookings to missed calls, with time saved for each")
- Brand voice examples — Roy to supply
