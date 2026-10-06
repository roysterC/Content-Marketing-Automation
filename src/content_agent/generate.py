"""The morning generator: pick a format and business type, research, write, render.

    daily()                -> what the weekday cron runs (format picked at random)
    generate("team", ...)  -> one specific format on demand (CLI `make`, Telegram /team)

Every format goes through the same steps, so they behave identically:
pick business type -> Claude researches (web) and writes the whole package -> fact-check
-> save as an Item + LinkedIn/Facebook drafts -> render the single-image visual and the
carousel with the text-fit check -> (optionally) send to Telegram.
"""

import logging
import random
import uuid
from dataclasses import dataclass

import yaml
from sqlalchemy import select

from content_agent.config import CONFIG_DIR, OUTPUT_DIR
from content_agent.db import Item, session
from content_agent.drafting.draft import _save, _system_prompt, share_poster
from content_agent.drafting.factcheck import factcheck
from content_agent.drafting.fit import render_carousel_fitted, render_poster_fitted
from content_agent.formats import FORMATS, Format
from content_agent.llm import ask_json
from content_agent.research.fetch import title_hash
from content_agent.visuals.render import poster_path

log = logging.getLogger(__name__)

RECENT_IN_PROMPT = 30  # past titles shown to Claude so it doesn't repeat itself


@dataclass(frozen=True)
class Settings:
    posts_per_day: int
    format_weights: dict[str, float]
    sector_weights: dict[str, float]
    avoid_recent_sectors: int


def load_settings(path=CONFIG_DIR / "formats.yaml") -> Settings:
    data = yaml.safe_load(path.read_text())
    weights = {k: float(v) for k, v in data["formats"].items()}
    unknown = set(weights) - set(FORMATS)
    if unknown:
        raise ValueError(f"Unknown formats in {path.name}: {', '.join(sorted(unknown))}")
    return Settings(
        posts_per_day=int(data.get("posts_per_day", 1)),
        format_weights=weights,
        sector_weights={k: float(v) for k, v in data["sectors"].items()},
        avoid_recent_sectors=int(data.get("avoid_recent_sectors", 3)),
    )


def pick_format(settings: Settings, rng=random) -> Format:
    names = [n for n, w in settings.format_weights.items() if w > 0]
    weights = [settings.format_weights[n] for n in names]
    return FORMATS[rng.choices(names, weights=weights)[0]]


def pick_sector(settings: Settings, recent_sectors: list[str], rng=random) -> str:
    avoid = set(recent_sectors[: settings.avoid_recent_sectors])
    pool = {s: w for s, w in settings.sector_weights.items() if s not in avoid and w > 0}
    pool = pool or settings.sector_weights  # every sector was recent: allow repeats
    return rng.choices(list(pool), weights=list(pool.values()))[0]


def _recent(db, category: str | None = None) -> list[Item]:
    """Most recent generated posts, newest first (all formats, or one)."""
    categories = [category] if category else list(FORMATS)
    return list(
        db.scalars(
            select(Item)
            .where(Item.category.in_(categories))
            .order_by(Item.fetched_at.desc())
            .limit(RECENT_IN_PROMPT)
        )
    )


def _store_and_render(db, fmt: Format, sector: str, result: dict, checks: dict) -> list[int]:
    title = fmt.title(result)
    item = Item(
        url=f"{fmt.name}:{uuid.uuid4()}",
        title=title[:500],
        title_hash=title_hash(f"{fmt.name} {title}"),
        summary=result["research_notes"][:2000],
        source=f"Claude {fmt.label}",
        category=fmt.name,
        business_type=sector,
        pillar="workflow",
        status="drafted",
    )
    db.add(item)
    drafts = _save(db, result, "workflow", item, checks)
    db.flush()

    linkedin = drafts[0]
    visual = render_poster_fitted(
        fmt.render_visual,
        result[fmt.visual_key],
        fmt.visual_schema,
        poster_path(linkedin.id),
        fmt.visual_key,
    )
    share_poster(drafts, fmt.visual_key, visual)
    path, linkedin.carousel = render_carousel_fitted(
        result["carousel"], OUTPUT_DIR / "carousels" / f"draft-{linkedin.id}"
    )
    linkedin.carousel_path = str(path)
    db.commit()
    log.info("%s ready: %s (%s), drafts %s", fmt.label, title, sector, [d.id for d in drafts])
    return [d.id for d in drafts]


def generate(format_name: str, sector: str | None = None) -> list[int]:
    """Make one post package in the given format. Returns its draft ids."""
    fmt = FORMATS[format_name]
    with session() as db:
        if not sector:
            sector = pick_sector(load_settings(), [i.business_type or "" for i in _recent(db)])
        sector = sector.strip()
        recent = _recent(db, fmt.name)
        recent_list = "\n".join(f"  - {i.title} ({i.business_type})" for i in recent)
        log.info("Generating %s for %s", fmt.label, sector)
        result = ask_json(
            system=_system_prompt(),
            prompt=fmt.task.format(sector=sector, recent=recent_list or "  (none yet)"),
            schema=fmt.schema,
            effort="high",
            web=True,
        )
        checks = factcheck(
            {k: result[k] for k in ("linkedin", "facebook", "carousel", fmt.visual_key)},
            f"No source article: this {fmt.label} was written by Claude.\n"
            "Treat clearly-labelled illustrative estimates as fine; flag anything stated "
            "as fact that isn't backed by these research notes:\n\n" + result["research_notes"],
        )
        return _store_and_render(db, fmt, sector, result, checks)


def daily() -> list[int]:
    """The morning run: `posts_per_day` packages, each in a randomly weighted format."""
    settings = load_settings()
    ids: list[int] = []
    for _ in range(settings.posts_per_day):
        fmt = pick_format(settings)
        log.info("Today's format: %s", fmt.label)
        ids += generate(fmt.name)
    return ids
