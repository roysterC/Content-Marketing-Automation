"""Turn a scored item (or a brief from Roy) into LinkedIn + Facebook drafts."""

import logging
import shutil
import uuid

from sqlalchemy import select

from content_agent.config import CONFIG_DIR, get_settings
from content_agent.db import Draft, Item, session
from content_agent.drafting.factcheck import factcheck
from content_agent.llm import ask_json
from content_agent.prompts import AUDIENCE, DESIGN_RULES, STYLE_RULES
from content_agent.visuals.icons import ICON_NAMES
from content_agent.visuals.schemas import INFOGRAPHIC

log = logging.getLogger(__name__)

PILLARS = ("workflow", "proof", "industry", "offer")
LAYOUTS = ("cover", "steps", "stats", "compare", "checklist", "grid", "insight", "cta")


LINKEDIN = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "body": {"type": "string"},
        "first_comment": {"type": "string"},
    },
    "required": ["hook", "body", "first_comment"],
    "additionalProperties": False,
}

FACEBOOK = {
    "type": "object",
    "properties": {
        "hook": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["hook", "body"],
    "additionalProperties": False,
}

CAROUSEL = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "layout": {"type": "string", "enum": list(LAYOUTS)},
            "kicker": {"type": "string"},
            "title": {"type": "string"},
            "body": {"type": "string"},
            "icon": {"type": "string", "enum": ["", *ICON_NAMES]},
            "points": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "icon": {"type": "string", "enum": ["", *ICON_NAMES]},
                        "title": {"type": "string"},
                        "detail": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "required": ["icon", "title", "detail", "value"],
                    "additionalProperties": False,
                },
            },
            "before_label": {"type": "string"},
            "after_label": {"type": "string"},
            "before": {"type": "array", "items": {"type": "string"}},
            "after": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "layout",
            "kicker",
            "title",
            "body",
            "icon",
            "points",
            "before_label",
            "after_label",
            "before",
            "after",
        ],
        "additionalProperties": False,
    },
}

RESEARCH_NOTES = {
    "type": "string",
    "description": (
        "What you checked on the web and the URLs you relied on, so the fact-checker and "
        "Roy can verify. Plain text."
    ),
}


def post_schema(visual_key: str, visual_schema: dict, research_notes: bool = False) -> dict:
    """Schema for one post package: LinkedIn + Facebook text, a carousel, and one
    single-image visual (the infographic, the org chart, ...)."""
    properties = {
        "linkedin": LINKEDIN,
        "facebook": FACEBOOK,
        "carousel": CAROUSEL,
        visual_key: visual_schema,
    }
    if research_notes:
        properties["research_notes"] = RESEARCH_NOTES
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


# Research-item and brief drafts: the infographic is their single image.
SCHEMA = post_schema("infographic", INFOGRAPHIC)


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
- infographic: a single-image summary (posted with the Facebook version, and usable on
  LinkedIn instead of the carousel): the problem, 3-5 steps of how the fix works, and 2-3
  outcomes. Same voice, number and design rules as the carousel.
- carousel: 6-8 slides for a LinkedIn PDF carousel, designed as infographics:

{DESIGN_RULES.format(icons=", ".join(ICON_NAMES))}"""


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


def share_poster(drafts: list[Draft], kind: str, visual: dict) -> None:
    """Give every draft in a group the image rendered for the LinkedIn draft, and the
    visual's content (for the painted-image prompt)."""
    from content_agent.visuals.render import poster_path

    source = poster_path(drafts[0].id)
    for d in drafts:
        d.visual = {"kind": kind, "data": visual}
        if d is not drafts[0] and source.exists():
            shutil.copyfile(source, poster_path(d.id))


def render_infographic(drafts: list[Draft], result: dict) -> None:
    """Render the group's infographic (with the text-fit check) and share it."""
    from content_agent.drafting.fit import render_poster_fitted
    from content_agent.visuals.render import poster_path, render_idea_html

    visual = render_poster_fitted(
        render_idea_html, result["infographic"], INFOGRAPHIC, poster_path(drafts[0].id),
        "infographic",
    )  # fmt: skip
    share_poster(drafts, "infographic", visual)


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
            drafts = _save(db, result, pillar, item, checks)
            item.status = "drafted"
            db.commit()
            render_infographic(drafts, result)
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
        render_infographic(drafts, result)
        db.commit()
        return [d.id for d in drafts]
