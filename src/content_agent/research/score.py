"""Score new items for relevance to the target reader, in batches to keep cost down."""

import logging

from sqlalchemy import select

from content_agent.db import Item, session
from content_agent.llm import ask_json
from content_agent.prompts import AUDIENCE

log = logging.getLogger(__name__)

BATCH_SIZE = 20

SYSTEM = f"""\
You triage research items for a content pipeline.

{AUDIENCE}

For each item, decide whether it could seed a genuinely useful post for this reader.
Score 0-10:
- 9-10: a concrete, recurring operational pain (e.g. missed calls, no-shows, admin overload)
  in an appointment-based or other SMB, where an automation clearly helps.
- 6-8: relevant to SMB owners and could be turned into a workflow or industry post.
- 3-5: loosely related; would need a stretch to be useful.
- 0-2: irrelevant, consumer chatter, memes, hiring posts, pure tech news with no SMB angle.

AI release news only scores high if it changes what a small business can practically do.

pillar must be "workflow" or "industry" (proof and offer posts come from Roy, not research),
or "skip" when the score is below 5. angle is one sentence: the post you'd write from it.
"""

SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "score": {"type": "integer"},
                    "business_type": {"type": "string"},
                    "pillar": {"type": "string", "enum": ["workflow", "industry", "skip"]},
                    "angle": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["id", "score", "business_type", "pillar", "angle", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}


def _format(items: list[Item]) -> str:
    parts = [
        f"<item id={i.id} source={i.source!r} category={i.category}>\n"
        f"Title: {i.title}\n{i.summary}\n</item>"
        for i in items
    ]
    return "Score these items:\n\n" + "\n\n".join(parts)


def score_new(limit: int = 200) -> int:
    """Score up to `limit` unscored items. Returns the number scored."""
    with session() as db:
        items = list(
            db.scalars(select(Item).where(Item.status == "new").order_by(Item.id).limit(limit))
        )
        by_id = {i.id: i for i in items}
        for start in range(0, len(items), BATCH_SIZE):
            batch = items[start : start + BATCH_SIZE]
            result = ask_json(system=SYSTEM, prompt=_format(batch), schema=SCHEMA, effort="low")
            for r in result["results"]:
                item = by_id.get(r["id"])
                if item is None:
                    continue
                item.relevance_score = max(0, min(10, r["score"]))
                item.business_type = r["business_type"]
                item.pillar = r["pillar"]
                item.angle = r["angle"]
                item.score_reason = r["reason"]
                item.status = "scored" if r["pillar"] != "skip" else "discarded"
            db.commit()
            log.info("Scored %d items", len(batch))
        return len(items)
