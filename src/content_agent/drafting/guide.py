"""Setup guides: an 8-page PDF on how to set up ONE automation, for one business type.

    make_guide("missed-call text-back", "nail salons")  -> research, write, check, render
    rerender()                                          -> redraw the latest saved guide

Each guide goes deeper on what a post is about, so someone who comments GUIDE on a
missed-calls post gets the missed-calls set-up guide. Steps:

1. Claude researches on the web (which tools this business type uses, and whether they
   really have the feature) and writes the guide.
2. Fact-check: anything stated as fact must be backed by the research notes.
3. Review: a separate call checks it against REVIEW_SYSTEM's checklist (can an owner act
   on every step, are the templates usable, no prices, ...).
4. Render with the text-fit check. Content is saved as JSON next to the PDF, so a new
   booking link or template tweak doesn't need another Claude call.

Problems from 2 and 3 are flagged in Telegram, not auto-fixed: Roy makes the call.
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from content_agent.config import CONFIG_DIR, OUTPUT_DIR
from content_agent.drafting.draft import RESEARCH_NOTES
from content_agent.drafting.factcheck import SCHEMA as CHECK_SCHEMA
from content_agent.drafting.factcheck import factcheck
from content_agent.drafting.fit import render_guide_fitted
from content_agent.funnel import load_funnel
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
Task: write a free set-up guide for {sector} on ONE automation: {topic}.

Roy sends this PDF to owners who comment on his post about it, so it goes deeper on that
one thing. It must be genuinely useful on its own: an owner could follow it and have the
automation running without ever calling Roy. Most won't want to, and the last page offers
to do it for them.
{context}
Research first (web search), and list what you checked, with URLs, in research_notes:
- How {sector} usually take bookings and which booking systems and phone set-ups they
  commonly use in the UK.
- Which of those tools really offer what this guide needs. Name a product in `routes`
  only if you confirmed on its own website or help pages that it has the feature;
  otherwise describe the category ("your booking system", "a business phone app").

What goes in:
- cost: a sum the reader redoes with their own numbers. rows multiply together into
  result_example; use modest example values and work the product out correctly. Only put
  REAL statistics in stats, with their source URL, or leave it empty.
- how: the flow, and the messages the customer would see on their phone. Use a made-up
  business name.
- routes: 2-3 ways to set it up, simplest first, exactly one recommended.
- steps: concrete instructions in order. Each says exactly what to do and where (which
  setting, which page), not "configure your system".
- templates: messages ready to send, with [placeholders] for the parts to swap.
- mistakes and signals: specific to this automation, not generic advice.

Never mention prices, costs or fees for tools, plans or Roy's services. The only money in
the guide is the reader's own lost bookings in the cost section."""

REVIEW_SYSTEM = """\
You review free set-up guides that a small-business automation consultant sends to
business owners. You get the guide's topic and its content as JSON. Check it against
this list and report each problem:
- Actionable: could a busy, non-technical owner do every step without asking anyone?
  Flag vague steps ("set up the integration") and steps that skip something needed.
- Templates: are the messages ready to send, natural, and under ~160 characters?
- On topic: is every page about this one automation for this business type?
- Sum: do the cost rows multiply to result_example, with modest example values?
- Honesty: no invented results, clients or testimonials; statistics have a source URL.
- No prices for tools, plans or services anywhere (the reader's lost bookings are fine).
- Consistent: steps, routes and templates agree with each other.

Put the part of the guide in `claim` (e.g. "steps[3]"), what's wrong in `problem` and a
concrete fix in `suggestion`. verdict is "pass" when nothing needs changing, otherwise
"needs_attention"."""


@dataclass(frozen=True)
class GuideResult:
    pdf: Path
    cover: Path
    content: Path
    factcheck: dict
    review: dict


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "guide"


def checked_label(today: date | None = None) -> str:
    """When the tools were checked, as printed in the guide, e.g. 'October 2026'."""
    return (today or datetime.now(UTC).date()).strftime("%B %Y")


def parse_request(text: str) -> tuple[str, str]:
    """'missed-call text-back for nail salons' -> (topic, sector)."""
    topic, sep, sector = text.strip().rpartition(" for ")
    if not sep or not topic.strip() or not sector.strip():
        raise ValueError("Say what and for whom, e.g. 'missed-call text-back for nail salons'")
    return topic.strip(), sector.strip()


def system_prompt() -> str:
    voice = (CONFIG_DIR / "brand_voice.md").read_text()
    return (
        f"{AUDIENCE}\n\n<brand_voice>\n{voice}\n</brand_voice>\n\n{STYLE_RULES}\n\n"
        "You're writing a short, practical PDF guide, not a social post: no hooks, no "
        "hashtags, no emoji. Keep every field within the word limits in the schema; the "
        "design has a fixed space for each one."
    )


def review(guide: dict, topic: str, sector: str) -> dict:
    prompt = (
        f"Topic: {topic}, for {sector}\n\n"
        f"<guide>\n{json.dumps(guide, indent=2, ensure_ascii=False)}\n</guide>"
    )
    return ask_json(system=REVIEW_SYSTEM, prompt=prompt, schema=CHECK_SCHEMA, effort="medium")


def _stem(topic: str, sector: str) -> Path:
    return GUIDES_DIR / f"{slug(sector)}--{slug(topic)}"


def _render(guide: dict, stem: Path, checked: str) -> tuple[Path, dict]:
    return render_guide_fitted(guide, GUIDE, stem, checked, load_funnel().booking_url)


def _result(stem: Path, saved: dict, pdf: Path) -> GuideResult:
    return GuideResult(
        pdf=pdf,
        cover=stem.parent / f"{stem.name}-cover.png",
        content=stem.with_suffix(".json"),
        factcheck=saved.get("factcheck") or {},
        review=saved.get("review") or {},
    )


def make_guide(topic: str, sector: str, context: str = "") -> GuideResult:
    """Research, write, check and render a setup guide. `context` is optional extra
    material, e.g. the post the guide goes with."""
    stem = _stem(topic, sector)
    log.info("Writing guide: %s for %s", topic, sector)
    if context:
        context = f"\nThe post it goes with (go deeper, don't repeat it):\n{context}\n"
    result = ask_json(
        system=system_prompt(),
        prompt=TASK.format(topic=topic, sector=sector, context=context),
        schema=SCHEMA,
        effort="high",
        web=True,
    )
    notes = result.pop("research_notes")
    checks = factcheck(
        {"guide": result},
        "No source article: this guide was written by Claude.\n"
        "The cost section's example numbers are fine as long as they're labelled as "
        "examples; flag anything stated as fact that isn't backed by these research "
        "notes:\n\n" + notes,
    )
    verdict = review(result, topic, sector)
    checked = checked_label()
    pdf, result = _render(result, stem, checked)
    saved = {
        "topic": topic,
        "sector": sector,
        "checked": checked,
        "guide": result,
        "research_notes": notes,
        "factcheck": checks,
        "review": verdict,
    }
    stem.with_suffix(".json").write_text(json.dumps(saved, indent=2, ensure_ascii=False))
    log.info("Guide ready: %s", pdf)
    return _result(stem, saved, pdf)


def latest() -> Path | None:
    saved = sorted(GUIDES_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    return saved[-1] if saved else None


def rerender(content: Path | None = None) -> GuideResult:
    """Redraw a saved guide (the latest by default) without asking Claude again."""
    content = content or latest()
    if not content or not content.exists():
        raise FileNotFoundError("No saved guide yet; make one first")
    saved = json.loads(content.read_text())
    stem = content.with_suffix("")
    pdf, saved["guide"] = _render(saved["guide"], stem, saved["checked"])
    content.write_text(json.dumps(saved, indent=2, ensure_ascii=False))
    return _result(stem, saved, pdf)
