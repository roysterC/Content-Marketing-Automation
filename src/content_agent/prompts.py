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
