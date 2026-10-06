"""Offer: a post whose whole job is getting people to ask for the free guide.

Only used once the guide is live (config/funnel.yaml has its link), and only for the
business types the guide suits. Written from the saved guide, so it never promises
anything the PDF doesn't contain.
"""

from content_agent.formats import Format
from content_agent.visuals.render import render_idea_html
from content_agent.visuals.schemas import INFOGRAPHIC

TASK = """\
Task: a direct-offer post for {sector} promoting Roy's free guide.

The guide (this is everything in it; don't promise anything else):
{guide_outline}

- Lead with the owner's problem (missed calls, empty slots, time on the phone), not the
  guide. The guide is the answer at the end.
- Give real value in the post itself: e.g. name the quickest win from the guide and how
  it works, so the post is worth reading even if they never ask for the guide.
- Time figures come from the guide and are estimates; say so, with the assumption.
- Vary the angle from these recent offer posts:
{recent}

The infographic is a preview of the guide: eyebrow "Free guide", the title, the problem,
the automations as steps (name + one-line detail), and 2-3 impact figures taken from the
guide's estimates (impact_note says they're estimates). Its cta asks people to comment
{keyword} (Facebook) or see the first comment (LinkedIn); keep it short enough to suit
both, e.g. "Comment {keyword} for the free guide".
The carousel teases the guide: the problem, a few of the automations, where to start,
and a cta slide for the guide.
Pillar: offer. No research needed beyond what's above, but don't add new statistics."""

OFFER = Format(
    name="offer",
    label="guide offer",
    task=TASK,
    visual_key="infographic",
    visual_schema=INFOGRAPHIC,
    render_visual=render_idea_html,
    title=lambda result: result["infographic"]["title"],
    pillar="offer",
    promotes_guide=True,
)
