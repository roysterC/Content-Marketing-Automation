"""Render carousel slides from an HTML template to a LinkedIn-ready PDF (+ PNG cover).

HTML templates keep every visual on-brand and editable with plain CSS; Playwright's
headless Chromium turns them into the PDF LinkedIn takes for document posts.
"""

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright
from sqlalchemy import select

from content_agent.config import OUTPUT_DIR, get_settings
from content_agent.db import Draft, session
from content_agent.visuals.icons import icon

log = logging.getLogger(__name__)

TEMPLATES = Path(__file__).parent / "templates"
SLIDE_W, SLIDE_H = 1080, 1350

AUTHOR = "Roy"
TAGLINE = "Automation for busy small businesses"

_env = Environment(loader=FileSystemLoader(TEMPLATES), autoescape=select_autoescape(["html"]))
_env.globals["icon"] = icon


def render_html(slides: list[dict], template: str = "carousel.html") -> str:
    return _env.get_template(template).render(slides=slides, author=AUTHOR, tagline=TAGLINE)


def render_idea_html(idea: dict) -> str:
    return _env.get_template("idea.html").render(idea=idea, author=AUTHOR, tagline=TAGLINE)


def render_orgchart_html(chart: dict) -> str:
    return _env.get_template("orgchart.html").render(chart=chart, author=AUTHOR, tagline=TAGLINE)


def poster_path(draft_id: int) -> Path:
    """Where a draft's single-image visual (infographic or org chart) is saved."""
    return OUTPUT_DIR / "posters" / f"draft-{draft_id}.png"


def render_png(html: str, out_path: Path) -> float:
    """Screenshot a single 1080x1350 page. Returns the text scale the template had to
    use to fit (1.0 = no shrinking)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=get_settings().chromium_path or None)
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.set_content(html, wait_until="networkidle")
        page.wait_for_selector("body[data-ready]", state="attached", timeout=15000)
        page.screenshot(path=str(out_path))
        scale = float(page.evaluate("document.body.dataset.scale || 1"))
        browser.close()
    return scale


def render_carousel(slides: list[dict], out_stem: Path) -> tuple[Path, list[float]]:
    """Write <out_stem>.pdf (all slides) and <out_stem>-cover.png. Returns the PDF path
    and each slide's text scale (1.0 = no shrinking needed)."""
    out_stem.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(slides)
    pdf_path = out_stem.with_suffix(".pdf")
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=get_settings().chromium_path or None)
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.set_content(html, wait_until="networkidle")
        page.wait_for_selector("body[data-ready]", state="attached", timeout=15000)
        page.screenshot(path=str(out_stem.parent / f"{out_stem.name}-cover.png"))
        page.pdf(
            path=str(pdf_path),
            width=f"{SLIDE_W}px",
            height=f"{SLIDE_H}px",
            print_background=True,
        )
        scales = page.eval_on_selector_all(
            "section.slide", "els => els.map(e => parseFloat(e.dataset.scale || 1))"
        )
        browser.close()
    return pdf_path, scales


def render_pending() -> int:
    """Render carousels for LinkedIn drafts that have slides but no file yet."""
    with session() as db:
        drafts = list(
            db.scalars(
                select(Draft).where(
                    Draft.platform == "linkedin",
                    Draft.carousel.is_not(None),
                    Draft.carousel_path.is_(None),
                )
            )
        )
        for d in drafts:
            if not d.carousel:
                continue
            from content_agent.drafting.fit import render_carousel_fitted

            path, d.carousel = render_carousel_fitted(
                d.carousel, OUTPUT_DIR / "carousels" / f"draft-{d.id}"
            )
            d.carousel_path = str(path)
            db.commit()
            log.info("Rendered %s", path)
        return len(drafts)
