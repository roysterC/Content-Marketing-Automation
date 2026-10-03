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


def render_png(html: str, out_path: Path) -> Path:
    """Screenshot a single 1080x1350 page (templates that set data-ready when laid out)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=get_settings().chromium_path or None)
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        page.set_content(html, wait_until="networkidle")
        page.wait_for_selector("body[data-ready]", state="attached", timeout=15000)
        page.screenshot(path=str(out_path))
        browser.close()
    return out_path


def render_carousel(slides: list[dict], out_stem: Path) -> Path:
    """Write <out_stem>.pdf (all slides) and <out_stem>-cover.png. Returns the PDF path."""
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
        browser.close()
    return pdf_path


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
            path = render_carousel(d.carousel, OUTPUT_DIR / "carousels" / f"draft-{d.id}")
            d.carousel_path = str(path)
            db.commit()
            log.info("Rendered %s", path)
        return len(drafts)
