"""Shared prompt text. Kept in one place so scoring and drafting agree on the reader."""

AUDIENCE = """\
Roy is a UK-based software engineer who sells AI automation services to small businesses.
His social posts exist to win clients (booked discovery calls), not followers.

Who reads the posts: busy small-business owners. They care about hours saved, missed
leads/bookings and staff cost - not about AI itself.

Initial client focus: appointment-based businesses that take lots of bookings by phone -
nail salons, hair salons, barbers, beauty clinics and similar. Their pains: missed calls
become missed bookings, staff are pulled off clients to answer the phone, no-shows,
manual reminders, rebooking, reviews.

Content can also cover any other industry where automation delivers clear, high value
(travel agencies, trades, clinics, professional services, etc.), as long as a small
business owner would recognise the problem.

Content pillars:
- workflow: "how a <business type> could automate X" breakdowns (~40%)
- proof: case studies / before-after numbers from Roy's real work (~30%; Roy supplies these)
- industry: an industry problem, tied to AI news only where it matters to SMBs (~20%)
- offer: direct offer / lead magnet (~10%; Roy triggers these)
"""

STYLE_RULES = """\
- Lead with the business problem. AI stays in the background.
- Plain language. Never use jargon like "RAG", "agentic", "LLM", "workflow orchestration".
- Never invent case studies, testimonials, client names, statistics or results. Only use
  numbers that appear in the source material or Roy's brief. If you want a number you
  don't have, describe the effect qualitatively or phrase it as an example calculation
  that is clearly labelled as one (e.g. "if you miss 5 calls a day...").
- Every post is a sales asset: end with a low-friction call to action.
- UK English spelling.
"""

DESIGN_RULES = """\
Every visual must look professional and visually pleasing: infographic first, never a
wall of text. Each carousel slide picks a `layout`:
- cover: the hook. `title` = hook (max ~9 words), `body` = one-line subhead, `kicker` =
  short audience label (e.g. "Salon owners"), `icon` = the main theme.
- steps: a numbered flow. 3-5 `points`, each with `icon`, `title` (max ~5 words) and
  `detail` (max ~12 words).
- stats: big numbers. 2-4 `points` with `value` (max ~7 characters, e.g. "~2 hrs",
  "24/7", "0"), `title` (max ~6 words) and `icon`. Put the "illustrative estimates" note in
  `body` unless the numbers came from Roy or a cited source.
- compare: before vs after. `before` and `after` lists of 3-4 items (max ~7 words each);
  `before_label` / `after_label` default to "Today" / "Automated".
- checklist: 3-5 `points` with `title` and an optional short `detail`.
- grid: 4 or 6 icon cards. Each point has `icon`, `title` (a role or job, 1-3 words),
  `value` (a short tagline) and `detail` (max ~10 words). Good for "your AI front desk
  team" style overviews.
- insight: one big statement (`title`, max ~12 words) plus an optional `body` line. At
  most one per carousel.
- cta: the last slide. `title` = the ask, `body` = what they get, `kicker` = the exact
  action (e.g. 'DM me "CALLS"'), `icon`.
Slide 1 is always cover and the last slide is always cta. Every slide in between should
be steps, stats, compare, checklist or grid; use at least three different layouts.
Choose `icon` names only from: {icons}. Use "" for unused text fields and [] for unused lists.
"""
