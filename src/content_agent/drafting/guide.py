"""The lead-magnet guide: a multi-page PDF people get by commenting the keyword.

    make_guide()    -> Claude researches (web) and writes it, fact-check, render the PDF
    rerender()      -> render the saved content again (e.g. after adding booking_url)

The content is saved as JSON next to the PDF, so changing the booking link or the
template doesn't need another Claude call. Roy reviews the PDF in Telegram, uploads it
(e.g. Google Drive) and pastes the link into config/funnel.yaml; until then posts don't
mention it.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from content_agent.config import CONFIG_DIR, OUTPUT_DIR
from content_agent.drafting.draft import RESEARCH_NOTES
from content_agent.drafting.factcheck import factcheck
from content_agent.drafting.fit import render_guide_fitted
from content_agent.funnel import Funnel, load_funnel
from content_agent.llm import ask_json
from content_agent.prompts import AUDIENCE, STYLE_RULES
from content_agent.visuals.schemas import GUIDE

log = logging.getLogger(__name__)

GUIDES_DIR = OUTPUT_DIR / "guides"

SCHEMA = {
    **GUIDE,
    "properties": {**GUIDE["properties"], "research_notes": RESEARCH_NOTES},
    "required": [*GUIDE["required"], "research_notes"],
}

TASK = """\
Task: write a free guide for {sector}: "{title}" ({subtitle}).

It's the lead magnet behind Roy's posts: an owner comments a keyword, Roy sends them this
PDF. It must be genuinely useful on its own (they could act on it without ever calling
Roy), and leave them thinking "I'd rather someone set this up for me".

The 5 automations:
- Concrete, recurring jobs owners of this business type really do by hand today, with
  the phone/booking pain first (missed calls, no-shows, rebooking, reminders, reviews...).
- Ordered from the quickest win to the most involved, with an honest effort label.
- Buildable now with ordinary tools (their booking system, phone line, SMS/WhatsApp,
  email, Google). Say "your booking system" rather than naming products, unless you've
  checked on the web that a product does what you say.
- Steps are what happens, in order, from the customer's side and the salon's side.

Numbers:
- time_saved is an illustrative estimate for a typical small business. Keep it modest,
  and show the working in time_assumption so the reader can redo it with their numbers.
- intro.stats only holds REAL statistics you found on the web, each with its source URL.
  No stat is better than a shaky one. Never invent clients, results or testimonials.

Before writing, use web search to check how this kind of business usually takes bookings
and that the building blocks exist. List what you checked and the URLs in research_notes.
"""


def system_prompt() -> str:
    voice = (CONFIG_DIR / "brand_voice.md").read_text()
    return (
        f"{AUDIENCE}\n\n<brand_voice>\n{voice}\n</brand_voice>\n\n{STYLE_RULES}\n\n"
        "You're writing a short, practical PDF guide, not a social post: no hooks, no "
        "hashtags, no emoji. Keep every field within the word limits in the schema; the "
        "design has a fixed space for each one."
    )


@dataclass(frozen=True)
class GuideResult:
    pdf: Path
    cover: Path
    content: Path
    factcheck: dict


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "guide"


def _paths(funnel: Funnel) -> tuple[Path, Path, Path]:
    stem = GUIDES_DIR / slug(funnel.guide_title)
    return stem, stem.with_suffix(".json"), stem.parent / f"{stem.name}-cover.png"


def _render(guide: dict, funnel: Funnel) -> tuple[Path, dict]:
    stem, _, _ = _paths(funnel)
    return render_guide_fitted(guide, GUIDE, stem, funnel.booking_url)


def make_guide(funnel: Funnel | None = None) -> GuideResult:
    """Research, write, fact-check and render the guide in config/funnel.yaml."""
    funnel = funnel or load_funnel()
    _, content, cover = _paths(funnel)
    log.info("Writing guide: %s", funnel.guide_title)
    result = ask_json(
        system=system_prompt(),
        prompt=TASK.format(
            sector=funnel.guide_sector, title=funnel.guide_title, subtitle=funnel.guide_subtitle
        ),
        schema=SCHEMA,
        effort="high",
        web=True,
    )
    notes = result.pop("research_notes")
    checks = factcheck(
        {"guide": result},
        "No source article: this guide was written by Claude.\n"
        "Treat clearly-labelled time estimates with their working shown as fine; flag "
        "anything stated as fact that isn't backed by these research notes:\n\n" + notes,
    )
    pdf, result = _render(result, funnel)
    content.write_text(
        json.dumps(
            {"guide": result, "research_notes": notes, "factcheck": checks},
            indent=2,
            ensure_ascii=False,
        )
    )
    log.info("Guide ready: %s", pdf)
    return GuideResult(pdf, cover, content, checks)


def rerender(funnel: Funnel | None = None) -> GuideResult:
    """Render the saved guide again, without asking Claude for new content."""
    funnel = funnel or load_funnel()
    _, content, cover = _paths(funnel)
    if not content.exists():
        raise FileNotFoundError(f"No saved guide at {content}; run `content-agent guide` first")
    saved = json.loads(content.read_text())
    pdf, saved["guide"] = _render(saved["guide"], funnel)
    content.write_text(json.dumps(saved, indent=2, ensure_ascii=False))
    return GuideResult(pdf, cover, content, saved.get("factcheck") or {})


def outline(funnel: Funnel | None = None) -> str:
    """What's in the saved guide, for posts that promote it ("" if there's none yet).
    Offer posts are written from this, so they only promise what the guide contains."""
    funnel = funnel or load_funnel()
    _, content, _ = _paths(funnel)
    if not content.exists():
        return ""
    g = json.loads(content.read_text())["guide"]
    lines = [f"{g['title']}: {g['subtitle']}"]
    for i, a in enumerate(g["automations"], 1):
        lines.append(
            f"{i}. {a['name']} ({a['effort']}, {a['time_saved']}; {a['time_assumption']}): "
            f"{a['problem']}"
        )
    lines.append(f"Where to start: {g['start_here']['advice']}")
    return "\n".join(lines)
