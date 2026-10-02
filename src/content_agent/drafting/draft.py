"""Turn a scored item (or a brief from Roy) into LinkedIn + Facebook drafts."""

import logging
import uuid

from sqlalchemy import select

from content_agent.config import CONFIG_DIR, get_settings
from content_agent.db import Draft, Item, session
from content_agent.drafting.factcheck import factcheck
from content_agent.llm import ask_json
from content_agent.prompts import AUDIENCE, STYLE_RULES

log = logging.getLogger(__name__)

PILLARS = ("workflow", "proof", "industry", "offer")

SCHEMA = {
    "type": "object",
    "properties": {
        "linkedin": {
            "type": "object",
            "properties": {
                "hook": {"type": "string"},
                "body": {"type": "string"},
                "first_comment": {"type": "string"},
            },
            "required": ["hook", "body", "first_comment"],
            "additionalProperties": False,
        },
        "facebook": {
            "type": "object",
            "properties": {
                "hook": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["hook", "body"],
            "additionalProperties": False,
        },
        "carousel": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["title", "body"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["linkedin", "facebook", "carousel"],
    "additionalProperties": False,
}


def _system_prompt() -> str:
    voice = (CONFIG_DIR / "brand_voice.md").read_text()
    examples = sorted(
        p for p in (CONFIG_DIR / "examples").glob("*.md") if p.name.lower() != "readme.md"
    )
    example_text = (
        "\n\n".join(
            f"<example file={p.name!r}>\n{p.read_text().strip()}\n</example>" for p in examples
        )
        or "(No example posts supplied yet - follow the brand voice guide.)"
    )

    return f"""\
You write social media drafts for Roy. Roy reviews every draft before anything is posted.

{AUDIENCE}

<brand_voice>
{voice}
</brand_voice>

<example_posts>
{example_text}
</example_posts>

Rules:
{STYLE_RULES}

Output, for one idea:
- linkedin: `hook` is the first two lines exactly as they will appear (they must work on
  their own before "see more"). `body` is the full post text INCLUDING the hook at the top.
  No URLs in the body. `first_comment` holds the source link or other links, or "" if none.
- facebook: a shorter, more conversational variant with different wording. `body` includes
  the hook. Never copy the LinkedIn text.
- carousel: 5-8 slides for a LinkedIn PDF carousel. Slide 1 is the hook; the last slide is
  the call to action. Each slide: a short title (max ~8 words) and body (max ~35 words).
"""


def _prompt_for_item(item: Item, pillar: str) -> str:
    return f"""\
Pillar: {pillar}
Business type to write for: {item.business_type or "small business owners"}
Suggested angle: {item.angle or "(your call)"}

Source material ({item.source}):
Title: {item.title}
URL: {item.url}
{item.summary}

Use the source as inspiration for a real problem. Don't summarise the source; write the
post Roy would write about the problem it reveals."""


def _prompt_for_brief(brief: str, pillar: str, business_type: str) -> str:
    return f"""\
Pillar: {pillar}
Business type to write for: {business_type}

Roy's brief (the ONLY source of facts, numbers and client details you may use):
{brief}"""


def _save(db, result: dict, pillar: str, item: Item | None, checks: dict) -> list[Draft]:
    group = str(uuid.uuid4())
    li, fb = result["linkedin"], result["facebook"]
    drafts = [
        Draft(
            item=item,
            group_id=group,
            platform="linkedin",
            pillar=pillar,
            hook=li["hook"],
            body=li["body"],
            first_comment=li["first_comment"] or None,
            carousel=result["carousel"],
            factcheck=checks,
        ),
        Draft(
            item=item,
            group_id=group,
            platform="facebook",
            pillar=pillar,
            hook=fb["hook"],
            body=fb["body"],
            factcheck=checks,
        ),
    ]
    db.add_all(drafts)
    return drafts


def _generate(prompt: str, source_text: str) -> tuple[dict, dict]:
    result = ask_json(system=_system_prompt(), prompt=prompt, schema=SCHEMA, effort="high")
    checks = factcheck(result, source_text)
    return result, checks


def draft_top_items(limit: int = 3) -> int:
    """Draft posts for the highest-scoring undrafted items. Returns groups created."""
    min_score = get_settings().min_relevance_score
    with session() as db:
        items = list(
            db.scalars(
                select(Item)
                .where(Item.status == "scored", Item.relevance_score >= min_score)
                .order_by(Item.relevance_score.desc(), Item.fetched_at.desc())
                .limit(limit)
            )
        )
        for item in items:
            pillar = item.pillar if item.pillar in PILLARS else "workflow"
            source_text = f"{item.title}\n{item.url}\n{item.summary}"
            result, checks = _generate(_prompt_for_item(item, pillar), source_text)
            _save(db, result, pillar, item, checks)
            item.status = "drafted"
            db.commit()
            log.info("Drafted item %d (%s)", item.id, item.title[:60])
        return len(items)


def draft_from_brief(brief: str, pillar: str, business_type: str) -> list[int]:
    """Draft from Roy's own notes - used for proof and offer posts. Returns draft ids."""
    if pillar not in PILLARS:
        raise ValueError(f"pillar must be one of {PILLARS}")
    result, checks = _generate(_prompt_for_brief(brief, pillar, business_type), brief)
    with session() as db:
        drafts = _save(db, result, pillar, None, checks)
        db.commit()
        return [d.id for d in drafts]
