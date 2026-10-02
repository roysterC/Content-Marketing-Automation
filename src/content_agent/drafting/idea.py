"""Generate an "automation idea for <business type>" post from Claude's own knowledge.

Unlike `draft`, there's no research item behind it: Claude picks a concrete automation
for the business type, checks it's practical today with a few web searches, and
returns the post text plus structured content for the infographic. The idea is stored
as an Item (url "idea:<uuid>") so it shows up like any other draft and isn't repeated.
"""

import logging
import random
import uuid

import yaml
from sqlalchemy import select

from content_agent.config import CONFIG_DIR, OUTPUT_DIR
from content_agent.db import Item, session
from content_agent.drafting.draft import SCHEMA as DRAFT_SCHEMA
from content_agent.drafting.draft import _save, _system_prompt
from content_agent.drafting.factcheck import factcheck
from content_agent.llm import ask_json
from content_agent.research.fetch import title_hash
from content_agent.visuals.render import render_carousel, render_idea_html, render_png

log = logging.getLogger(__name__)

IDEA_SOURCE = "Claude idea"
RECENT_IDEAS_IN_PROMPT = 30


def _str(desc: str) -> dict:
    return {"type": "string", "description": desc}


INFOGRAPHIC = {
    "type": "object",
    "properties": {
        "sector": _str("Business type as shown on the graphic, title case, e.g. 'Nail salons'"),
        "title": _str(
            "The idea as an outcome, max ~9 words, e.g. 'Turn missed calls into bookings'"
        ),
        "problem": _str("The pain in the owner's words, 1-2 sentences, max ~30 words"),
        "steps": {
            "type": "array",
            "description": "3-5 steps of how the automation works, in order",
            "items": {
                "type": "object",
                "properties": {
                    "title": _str("Max ~5 words"),
                    "detail": _str("One plain sentence, max ~14 words"),
                },
                "required": ["title", "detail"],
                "additionalProperties": False,
            },
        },
        "impact": {
            "type": "array",
            "description": "2-3 outcomes. Short value (e.g. '~2 hrs', '24/7', '0') and label",
            "items": {
                "type": "object",
                "properties": {
                    "value": _str("Max ~7 characters"),
                    "label": _str("Max ~6 words"),
                },
                "required": ["value", "label"],
                "additionalProperties": False,
            },
        },
        "impact_note": _str("One short line saying the figures are illustrative estimates"),
        "cta": _str("Short call to action, max ~7 words, e.g. 'DM me \"CALLS\" to see it working'"),
    },
    "required": ["sector", "title", "problem", "steps", "impact", "impact_note", "cta"],
    "additionalProperties": False,
}

SCHEMA = {
    **DRAFT_SCHEMA,
    "properties": {
        **DRAFT_SCHEMA["properties"],
        "infographic": INFOGRAPHIC,
        "research_notes": _str(
            "What you checked on the web and the URLs you relied on, so the fact-checker "
            "and Roy can verify. Plain text."
        ),
    },
    "required": [*DRAFT_SCHEMA["required"], "infographic", "research_notes"],
}

IDEA_TASK = """\
Task: come up with ONE concrete automation idea for {sector} and write it up.

What makes a good idea:
- A specific, recurring, annoying job that owners of this business type actually do by
  hand (phones, bookings, reminders, follow-ups, quotes, reviews, admin, rebooking...).
- Buildable today with ordinary tools a small business already has or can cheaply add
  (their booking system, phone line, SMS/WhatsApp, email, Google, forms).
- Easy to picture: an owner should read it and think "I do that every day".
- Different from these ideas already used (don't repeat or lightly reword them):
{recent}

Before writing, use web search to check the idea is realistic now: how this kind of
business usually takes bookings / handles the task, and that the building blocks exist.
Don't name specific software products in the post or graphic unless you've checked
they do what you say; "your booking system" is fine.

Numbers: the impact figures are illustrative estimates for a typical small business, not
claims. Keep them modest and plausible, and say so in impact_note. Only quote a real
statistic if you found it on the web, and then put its source URL in the LinkedIn
first_comment and in research_notes.

Pillar: workflow ("how {sector} could automate X").
Write the LinkedIn post, Facebook post and carousel as usual, plus the `infographic`
content for a single-image summary of the idea."""


def _pick_sector(recent_sectors: list[str]) -> str:
    data = yaml.safe_load((CONFIG_DIR / "idea_sectors.yaml").read_text())
    sectors = data["sectors"]
    fresh = [s for s in sectors if s not in recent_sectors[:3]] or sectors
    return random.choice(fresh)


def _recent_ideas(db) -> list[Item]:
    return list(
        db.scalars(
            select(Item)
            .where(Item.source == IDEA_SOURCE)
            .order_by(Item.fetched_at.desc())
            .limit(RECENT_IDEAS_IN_PROMPT)
        )
    )


def idea_image_path(draft_id: int):
    return OUTPUT_DIR / "ideas" / f"draft-{draft_id}.png"


def generate_idea(sector: str | None = None) -> list[int]:
    """Create one idea (LinkedIn + Facebook drafts, infographic, carousel). Returns draft ids."""
    with session() as db:
        recent = _recent_ideas(db)
        sector = (sector or _pick_sector([i.business_type or "" for i in recent])).strip()
        recent_list = (
            "\n".join(f"  - {i.title} ({i.business_type})" for i in recent) or "  (none yet)"
        )
        prompt = IDEA_TASK.format(
            sector=sector,
            recent=recent_list,
        )
        log.info("Generating idea for %s", sector)
        result = ask_json(
            system=_system_prompt(), prompt=prompt, schema=SCHEMA, effort="high", web=True
        )
        checks = factcheck(
            {k: result[k] for k in ("linkedin", "facebook", "carousel", "infographic")},
            "No source article: this idea was written by Claude.\n"
            "Treat clearly-labelled illustrative estimates as fine; flag anything stated "
            "as fact that isn't backed by these research notes:\n\n" + result["research_notes"],
        )

        title = result["infographic"]["title"]
        item = Item(
            url=f"idea:{uuid.uuid4()}",
            title=title[:500],
            title_hash=title_hash(f"idea {title}"),
            summary=result["research_notes"][:2000],
            source=IDEA_SOURCE,
            category="idea",
            business_type=sector,
            pillar="workflow",
            status="drafted",
        )
        db.add(item)
        drafts = _save(db, result, "workflow", item, checks)
        db.flush()

        linkedin = drafts[0]
        render_png(render_idea_html(result["infographic"]), idea_image_path(linkedin.id))
        linkedin.carousel_path = str(
            render_carousel(result["carousel"], OUTPUT_DIR / "carousels" / f"draft-{linkedin.id}")
        )
        db.commit()
        log.info("Idea ready: %s (%s), drafts %s", title, sector, [d.id for d in drafts])
        return [d.id for d in drafts]
