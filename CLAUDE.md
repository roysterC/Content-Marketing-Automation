# AI Content Agent — Project Brief

## Purpose
Automate a social media presence (LinkedIn + Facebook) that wins **clients for Roy's AI automation services business**. This is a services/lead-gen account, NOT an audience-first account. Success = booked discovery calls from business owners, not follower count.

- Primary target vertical: travel agencies (more verticals may be added later, e.g. trades)
- Reader: busy small-business owner who cares about saved hours, missed leads and staff cost — not about AI itself
- Owner: Roy, UK-based software engineer (comfortable with Python/TS, cost-conscious, prefers understanding the "why" behind design decisions)

## Content strategy
- Lead with business problems; AI stays in the background. Plain language, no jargon ("RAG", "agentic").
- Pillars (approx. mix):
  - Workflow breakdowns: "how a travel agency could automate X" (~40%)
  - Proof: case studies, before/after numbers, screen recordings of automations running (~30%)
  - Industry problem posts tied to AI news only where it matters to SMBs (~20%)
  - Direct offer / lead magnet posts (~10%)
- Lower volume, higher depth. Every post is a sales asset.
- LinkedIn: post from Roy's **personal profile** (not a company page). Strong 2-line hook. External links go in the **first comment**, not the post body. Carousels (PDF document posts) are a priority format.
- Facebook: shorter, more conversational variant. Never cross-post identical copy.

## Pipeline
1. **Research** — ingest industry sources for target verticals (trade publications, subreddits, forums, RSS) plus relevant AI releases. LLM scores relevance to the target reader and dedupes. Store in DB.
2. **Draft** — Claude writes per-platform drafts using a brand-voice file + 10–20 example posts.
3. **Visuals** — primarily HTML templates rendered to PNG/PDF via Playwright (branded, consistent carousels/diagrams). Image model only for occasional hero images.
4. **Human review gate** — drafts sent to Slack or Telegram with Approve / Edit / Reject. Nothing publishes without approval.
5. **Publish** — via a scheduler's API (Buffer / Publer / Metricool) initially; direct Meta Graph / LinkedIn APIs only if outgrown.
6. **Engage** — Facebook: comment-keyword → DM lead magnet via Messenger tooling (e.g. ManyChat). LinkedIn: agent **drafts** replies/DMs for Roy to send manually.
7. **Lead funnel** — lead magnet → landing page w/ email capture → short nurture sequence → Cal.com booking → CRM.
8. **Analytics** — weekly metric pull, tag posts by pillar/hook/format, feed top performers back into drafting prompts.

## Hard constraints
- **No automated LinkedIn actions** beyond posting (no auto DMs, connection requests, comments, likes) — ToS violation, ban risk.
- Facebook Messenger automation must stay within Meta messaging policy.
- No fabricated case studies, testimonials or metrics. Proof content must come from real work Roy supplies.
- Fact-check pass on any claim about AI products/releases before it reaches the review gate.
- Keep running costs low; prefer self-hosted / free tiers where reasonable.

## Proposed stack
- Python service on a small VPS, cron for scheduling (n8n self-hosted is an acceptable alternative)
- Postgres / Supabase: sources, content queue, post status, metrics
- Claude API for scoring, drafting, fact-check
- Playwright for template rendering
- Slack or Telegram bot for approvals
- Scheduler API for publishing
- MailerLite or ConvertKit, Cal.com, ManyChat (Facebook)

## Build order
1. **Phase 1 (start here):** research ingest → drafting → visual templates → Slack/Telegram approval. Roy posts manually; judge quality.
2. **Phase 2:** automated publishing via scheduler API.
3. **Phase 3:** lead magnet, landing page, email nurture, Facebook comment-to-DM.
4. **Phase 4:** analytics feedback loop (once ~30 posts of data exist).

## Open decisions
- Slack vs Telegram for approvals
- Python service vs n8n for orchestration
- Which scheduler (Buffer / Publer / Metricool)
- First lead magnet topic (candidate: "The 5 automations every travel agency should run, with time saved for each")
- Brand voice examples — Roy to supply
