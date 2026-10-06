"""Command line entry point: `content-agent <command>`."""

import logging
from pathlib import Path
from typing import Annotated

import typer

from content_agent import db

app = typer.Typer(
    help="Content agent. Daily use: `daily` (cron) and `make`. The feed tools (ingest, "
    "score, draft) are manual extras and no longer part of the morning run."
)


@app.callback()
def main(verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    db.init_db()


@app.command()
def ingest(
    source: Annotated[str | None, typer.Option(help="Only fetch the source with this name")] = None,
) -> None:
    """Fetch research sources and store new items."""
    from content_agent.research.fetch import ingest as run

    typer.echo(f"Added {run(source)} new items")


@app.command()
def score(limit: int = 200) -> None:
    """Score unscored items for relevance with Claude."""
    from content_agent.research.score import score_new

    typer.echo(f"Scored {score_new(limit)} items")


@app.command()
def draft(limit: Annotated[int, typer.Option(help="Max ideas to draft this run")] = 3) -> None:
    """Draft LinkedIn + Facebook posts for the top-scoring items."""
    from content_agent.drafting.draft import draft_top_items

    typer.echo(f"Drafted {draft_top_items(limit)} ideas")


@app.command()
def brief(
    notes: Annotated[Path, typer.Argument(help="Text file with your notes/facts for the post")],
    pillar: Annotated[str, typer.Option(help="workflow | proof | industry | offer")] = "proof",
    business_type: Annotated[str, typer.Option(help="Who the post is for")] = "salon owners",
) -> None:
    """Draft a post from your own notes (case studies, offers). Only your facts are used."""
    from content_agent.drafting.draft import draft_from_brief

    ids = draft_from_brief(notes.read_text(), pillar, business_type)
    typer.echo(f"Created drafts {ids}")


def _send(ids: list[int]) -> None:
    from content_agent.approval.telegram_bot import send_pending

    typer.echo(f"Created drafts {ids}; sent {send_pending()} drafts for review")


@app.command()
def daily(
    send: Annotated[bool, typer.Option(help="Send to Telegram when ready")] = True,
) -> None:
    """The morning run: picks a format at random (weights in config/formats.yaml),
    researches it and builds the post package. This is what the weekday cron runs."""
    from content_agent.generate import daily as run_daily

    ids = run_daily()
    if send:
        _send(ids)
    else:
        typer.echo(f"Created drafts {ids}")


@app.command()
def make(
    format_name: Annotated[str, typer.Argument(metavar="FORMAT", help="idea or team")],
    sector: Annotated[
        str | None, typer.Option(help="Business type, e.g. 'barbers'. Random if omitted")
    ] = None,
    send: Annotated[bool, typer.Option(help="Send to Telegram when ready")] = True,
) -> None:
    """Build one post package in a specific format, e.g. `make team --sector barbers`."""
    from content_agent.formats import FORMATS
    from content_agent.generate import generate

    if format_name not in FORMATS:
        raise typer.BadParameter(f"choose one of: {', '.join(FORMATS)}")
    ids = generate(format_name, sector)
    if send:
        _send(ids)
    else:
        typer.echo(f"Created drafts {ids}")


@app.command()
def render() -> None:
    """Render carousel PDFs for drafts that need them."""
    from content_agent.visuals.render import render_pending

    typer.echo(f"Rendered {render_pending()} carousels")


@app.command()
def review() -> None:
    """Send pending drafts to Telegram for approval."""
    from content_agent.approval.telegram_bot import send_pending

    typer.echo(f"Sent {send_pending()} drafts for review")


@app.command()
def remind() -> None:
    """Nudge in Telegram about approved drafts not yet marked posted (weekday cron)."""
    from content_agent.approval.telegram_bot import send_reminders

    typer.echo(f"Reminded about {send_reminders()} drafts")


@app.command()
def paint(
    draft_id: Annotated[int, typer.Argument(help="Draft whose visual to paint")],
    style: Annotated[
        str | None, typer.Option(help="Art style from config/art_style.yaml (default: active)")
    ] = None,
) -> None:
    """Print the Gemini (Nano Banana) prompt for a draft's painted image."""
    from content_agent.approval.telegram_bot import paint_prompt
    from content_agent.db import Draft, session

    with session() as db:
        d = db.get(Draft, draft_id)
        prompt = paint_prompt(d, style) if d else None
    if not prompt:
        raise typer.BadParameter(f"draft {draft_id} has no visual to paint")
    typer.echo(prompt)


@app.command()
def bot() -> None:
    """Run the Telegram bot that handles Approve / Edit / Reject (long-running)."""
    from content_agent.approval.telegram_bot import run_bot

    run_bot()


@app.command(hidden=True)
def run() -> None:
    """Old name for `daily`, kept so an un-updated cron line still works."""
    daily(send=True)


if __name__ == "__main__":
    app()
