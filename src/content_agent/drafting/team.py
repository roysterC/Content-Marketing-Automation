"""Generate a "Your <business>'s AI Team" org-chart post.

Claude lays out the everyday jobs a business type could hand to automations, grouped
into departments like a real staff chart, and writes the matching posts and carousel.
Rendered with visuals/templates/orgchart.html.
"""

import logging

from sqlalchemy import select

from content_agent.db import Item, session
from content_agent.drafting.draft import SCHEMA as DRAFT_SCHEMA
from content_agent.drafting.draft import _system_prompt
from content_agent.drafting.factcheck import factcheck
from content_agent.drafting.idea import _pick_sector, store_visual_post
from content_agent.llm import ask_json
from content_agent.visuals.icons import ICON_NAMES
from content_agent.visuals.render import render_orgchart_html

log = logging.getLogger(__name__)

TEAM_SOURCE = "Claude team chart"


def _str(desc: str) -> dict:
    return {"type": "string", "description": desc}


ICON = {"type": "string", "enum": ICON_NAMES}

ORGCHART = {
    "type": "object",
    "properties": {
        "title_before": _str("Headline text before the accent word(s), e.g. \"Your Salon's \""),
        "title_accent": _str("1-2 accent-coloured words, e.g. 'AI Team'"),
        "title_after": _str("Headline text after the accent, often ''"),
        "subtitle": _str("One line with the count, e.g. '12 automations, organised like real staff'"),
        "root_label": _str("Tiny label above the root, e.g. 'The owner'"),
        "root_name": _str("Root box name, e.g. 'Your salon' (max ~3 words)"),
        "root_icon": ICON,
        "departments": {
            "type": "array",
            "description": "4 departments (3-5 allowed), each a real area of the business",
            "items": {
                "type": "object",
                "properties": {
                    "name": _str("1-2 words, e.g. 'Front desk'"),
                    "icon": ICON,
                    "roles": {
                        "type": "array",
                        "description": "3 automations (2-4 allowed); same count in every department",
                        "items": {
                            "type": "object",
                            "properties": {
                                "icon": ICON,
                                "name": _str("The automation, 1-3 words, e.g. 'Reminders'"),
                                "nickname": _str("A friendly job title, 1-3 words, e.g. 'No-Show Guard'"),
                                "does": _str("What it does, 3-6 plain words"),
                            },
                            "required": ["icon", "name", "nickname", "does"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "icon", "roles"],
                "additionalProperties": False,
            },
        },
        "cta": _str("Short call to action, max ~7 words, e.g. 'DM me \"TEAM\" for the full breakdown'"),
    },
    "required": [
        "title_before", "title_accent", "title_after", "subtitle", "root_label",
        "root_name", "root_icon", "departments", "cta",
    ],
    "additionalProperties": False,
}  # fmt: skip

SCHEMA = {
    **DRAFT_SCHEMA,
    "properties": {
        **DRAFT_SCHEMA["properties"],
        "orgchart": ORGCHART,
        "research_notes": _str(
            "What you checked on the web and the URLs you relied on, so the fact-checker "
            "and Roy can verify. Plain text."
        ),
    },
    "required": [*DRAFT_SCHEMA["required"], "orgchart", "research_notes"],
}

TEAM_TASK = """\
Task: an "AI team" org chart for {sector}: the everyday jobs this kind of business could
hand to simple automations, organised like a real staff chart.

- Pick 4 departments that match how {sector} actually run (e.g. front desk, bookings,
  marketing, admin; rename them to fit the business).
- 3 automations per department, 12 in total. Each one is a specific, recurring job owners
  do by hand today, and buildable with ordinary tools (booking system, phone, SMS or
  WhatsApp, email, forms). No futuristic or vague items ("AI strategy", "smart insights").
- Give each a friendly job-title nickname ("No-Show Guard", "Diary Filler") so it reads
  like staff, and say in 3-6 plain words what it does.
- Use web search briefly to check the jobs are realistic for {sector} today. Don't name
  specific software products.
- No numbers or claims on the chart itself.

Write the LinkedIn post, Facebook post and carousel about this "team" as usual. The
carousel can walk through the departments (e.g. a grid slide per department or two).
Pillar: workflow."""


def _recent_sectors(db) -> list[str]:
    return list(
        db.scalars(
            select(Item.business_type)
            .where(Item.source == TEAM_SOURCE)
            .order_by(Item.fetched_at.desc())
            .limit(5)
        )
    )


def generate_team(sector: str | None = None) -> list[int]:
    """Create one AI-team org chart post. Returns draft ids."""
    with session() as db:
        sector = (sector or _pick_sector(_recent_sectors(db))).strip()
        log.info("Generating AI team chart for %s", sector)
        result = ask_json(
            system=_system_prompt(),
            prompt=TEAM_TASK.format(sector=sector),
            schema=SCHEMA,
            effort="high",
            web=True,
        )
        checks = factcheck(
            {k: result[k] for k in ("linkedin", "facebook", "carousel", "orgchart")},
            "No source article: this org chart was written by Claude.\n"
            "Flag anything stated as fact that isn't backed by these research notes:\n\n"
            + result["research_notes"],
        )
        chart = result["orgchart"]
        title = f"{chart['title_before']}{chart['title_accent']}{chart['title_after']}".strip()
        ids = store_visual_post(
            db,
            result=result,
            checks=checks,
            sector=sector,
            title=title,
            source=TEAM_SOURCE,
            kind="team",
            poster_key="orgchart",
            poster_schema=ORGCHART,
            make_html=render_orgchart_html,
        )
        log.info("Team chart ready: %s (%s), drafts %s", title, sector, ids)
        return ids
