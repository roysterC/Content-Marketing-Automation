"""Text-fit check: catch visuals that only fit because the template shrank the text.

Every template shrinks its text until the content fits the canvas, and reports the
scale it ended up at. Below MIN_SCALE the text is too small to read comfortably on a
phone, so the flagged parts go back to Claude (a cheap, low-effort call) to be
shortened, and the visual is rendered once more. No extra call when everything fits.
"""

import json
import logging
from collections.abc import Callable
from pathlib import Path

from content_agent.drafting.draft import SCHEMA as DRAFT_SCHEMA
from content_agent.llm import LLMError, ask_json
from content_agent.visuals.render import (
    GUIDE_PAGES,
    render_carousel,
    render_guide,
    render_guide_html,
    render_png,
)

log = logging.getLogger(__name__)

MIN_SCALE = 0.85

CAROUSEL_SCHEMA = {
    "type": "object",
    "properties": {"slides": DRAFT_SCHEMA["properties"]["carousel"]},
    "required": ["slides"],
    "additionalProperties": False,
}

TIGHTEN_SYSTEM = """\
You edit the text of social media infographics so it fits its design at a readable size.
You get the content as JSON plus a list of the parts that are too long. For each flagged
part, cut its wording by roughly a third: shorter phrases, fewer filler words, and drop
list items beyond the minimum if needed. Keep the meaning, the plain UK-English voice,
the layout, the icons and every number exactly as they are. Leave unflagged parts
unchanged. Return the complete JSON in the same shape."""


def fit_problems(scales: list[float], labels: list[str]) -> list[str]:
    return [
        f"{label}: text had to shrink to {scale:.0%} to fit"
        for scale, label in zip(scales, labels, strict=True)
        if scale < MIN_SCALE
    ]


def tighten(data: dict, schema: dict, problems: list[str]) -> dict:
    prompt = (
        "Too long:\n"
        + "\n".join(f"- {p}" for p in problems)
        + f"\n\nContent:\n{json.dumps(data, indent=2, ensure_ascii=False)}"
    )
    return ask_json(system=TIGHTEN_SYSTEM, prompt=prompt, schema=schema, effort="low")


def render_carousel_fitted(slides: list[dict], out_stem: Path) -> tuple[Path, list[dict]]:
    """Render a carousel, shortening and re-rendering slides that are too cramped.
    Returns the PDF path and the (possibly shortened) slides to store."""
    path, scales = render_carousel(slides, out_stem)
    labels = [f"slide {i} ({s.get('layout', 'text')})" for i, s in enumerate(slides, 1)]
    problems = fit_problems(scales, labels)
    if not problems:
        return path, slides
    log.info("Carousel too cramped, shortening: %s", "; ".join(problems))
    try:
        slides = tighten({"slides": slides}, CAROUSEL_SCHEMA, problems)["slides"]
    except LLMError as e:
        log.warning("Couldn't shorten carousel (%s); keeping the shrunk version", e)
        return path, slides
    path, scales = render_carousel(slides, out_stem)
    log.info("Carousel re-rendered; smallest text scale now %.0f%%", min(scales) * 100)
    return path, slides


def render_poster_fitted(
    make_html: Callable[[dict], str], data: dict, schema: dict, out_path: Path, label: str
) -> dict:
    """Render a single-image visual, shortening and re-rendering it if too cramped.
    Returns the (possibly shortened) content."""
    problems = fit_problems([render_png(make_html(data), out_path)], [label])
    if not problems:
        return data
    log.info("%s too cramped, shortening", label)
    try:
        data = tighten(data, schema, problems)
    except LLMError as e:
        log.warning("Couldn't shorten %s (%s); keeping the shrunk version", label, e)
        return data
    scale = render_png(make_html(data), out_path)
    log.info("%s re-rendered; text scale now %.0f%%", label, scale * 100)
    return data


def render_guide_fitted(
    guide: dict, schema: dict, out_stem: Path, checked: str, booking_url: str = ""
) -> tuple[Path, dict]:
    """Render the guide PDF, shortening and re-rendering pages that are too cramped.
    Returns the PDF path and the (possibly shortened) guide content."""

    def render(g: dict) -> tuple[Path, list[float]]:
        return render_guide(render_guide_html(g, checked, booking_url), out_stem)

    path, scales = render(guide)
    problems = fit_problems(scales, GUIDE_PAGES)
    if not problems:
        return path, guide
    log.info("Guide too cramped, shortening: %s", "; ".join(problems))
    try:
        guide = tighten(guide, schema, problems)
    except LLMError as e:
        log.warning("Couldn't shorten the guide (%s); keeping the shrunk version", e)
        return path, guide
    path, scales = render(guide)
    log.info("Guide re-rendered; smallest text scale now %.0f%%", min(scales) * 100)
    return path, guide
