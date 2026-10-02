"""Offline tests: no network, no Claude calls, no Telegram."""

from content_agent.approval.telegram_bot import EDIT_PROMPT, EDIT_RE, format_draft
from content_agent.db import Draft
from content_agent.research.fetch import clean_text, load_sources, title_hash
from content_agent.visuals.render import render_html


def test_sources_load():
    sources = load_sources()
    assert sources
    assert all(s.url.startswith("https://") for s in sources)
    assert any(s.category == "salons" for s in sources)


def test_title_hash_ignores_case_and_punctuation():
    assert title_hash("Missed calls cost salons £££!") == title_hash("missed  calls cost salons")


def test_clean_text_strips_html():
    assert clean_text("<p>Hello &amp; <b>welcome</b></p>") == "Hello & welcome"


def test_carousel_html_has_one_section_per_slide_and_escapes():
    slides = [
        {"title": "Missed calls = missed bookings", "body": "Hook"},
        {"title": "Step 1", "body": "<script>x</script>"},
        {"title": "Want this?", "body": "DM me"},
    ]
    html = render_html(slides)
    assert html.count('<section class="slide') == 3
    assert "<script>x</script>" not in html
    assert "Swipe" in html


def test_format_draft_flags_factcheck_issues():
    d = Draft(
        id=7,
        platform="linkedin",
        pillar="workflow",
        hook="h",
        body="Post body",
        first_comment="https://example.com",
        factcheck={
            "verdict": "needs_attention",
            "issues": [{"claim": "saves 10h", "problem": "not in source", "suggestion": ""}],
        },
    )
    text = format_draft(d)
    assert "#7 · LinkedIn" in text
    assert "First comment" in text
    assert "saves 10h" in text


def test_edit_prompt_round_trips_draft_id():
    assert EDIT_RE.match(EDIT_PROMPT.format(id=42)).group(1) == "42"


def test_idea_infographic_html_renders_steps_and_escapes():
    from content_agent.visuals.render import render_idea_html

    idea = {
        "sector": "Nail salons",
        "title": "Turn missed calls into bookings",
        "problem": "<b>Phones</b> ring mid-set.",
        "steps": [{"title": f"Step {n}", "detail": "Detail"} for n in range(1, 5)],
        "impact": [{"value": "~2 hrs", "label": "a week back"}, {"value": "24/7", "label": "x"}],
        "impact_note": "Illustrative estimates.",
        "cta": "DM me CALLS",
    }
    html = render_idea_html(idea)
    assert html.count('class="step"') == 4
    assert "--cols: 2" in html
    assert "<b>Phones</b>" not in html


def test_format_draft_labels_claude_ideas():
    from content_agent.db import Item

    item = Item(url="idea:abc", title="t", source="Claude idea", business_type="barbers")
    d = Draft(id=3, platform="facebook", pillar="workflow", hook="h", body="b", item=item)
    assert "Claude's own idea (barbers)" in format_draft(d)
