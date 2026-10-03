"""Command line entry point: `content-agent <command>`."""

import logging
from pathlib import Path
from typing import Annotated

import typer

from content_agent import db

app = typer.Typer(help="Phase 1 content pipeline: research -> draft -> visuals -> approval.")


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


@app.command()
def idea(
    sector: Annotated[
        str | None, typer.Option(help="Business type, e.g. 'nail salons'. Random if omitted")
    ] = None,
    send: Annotated[bool, typer.Option(help="Send it to Telegram when ready")] = True,
) -> None:
    """Have Claude come up with an automation idea (web-checked) with an infographic."""
    from content_agent.drafting.idea import generate_idea

    ids = generate_idea(sector)
    typer.echo(f"Created drafts {ids}")
    if send:
        from content_agent.approval.telegram_bot import send_pending

        typer.echo(f"Sent {send_pending()} drafts for review")


@app.command()
def team(
    sector: Annotated[
        str | None, typer.Option(help="Business type, e.g. 'barbers'. Random if omitted")
    ] = None,
    send: Annotated[bool, typer.Option(help="Send it to Telegram when ready")] = True,
) -> None:
    """Have Claude build a "Your <business>'s AI Team" org-chart post."""
    from content_agent.drafting.team import generate_team

    ids = generate_team(sector)
    typer.echo(f"Created drafts {ids}")
    if send:
        from content_agent.approval.telegram_bot import send_pending

        typer.echo(f"Sent {send_pending()} drafts for review")


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
def bot() -> None:
    """Run the Telegram bot that handles Approve / Edit / Reject (long-running)."""
    from content_agent.approval.telegram_bot import run_bot

    run_bot()


@app.command()
def run(draft_limit: int = 3) -> None:
    """Full Phase 1 pass: ingest -> score -> draft -> render -> send for review."""
    ingest()
    score()
    draft(draft_limit)
    render()
    review()


if __name__ == "__main__":
    app()
