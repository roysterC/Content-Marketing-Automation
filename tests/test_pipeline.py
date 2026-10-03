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


def _slide(layout, **kw):
    base = {
        "layout": layout,
        "kicker": "",
        "title": f"{layout} title",
        "body": "",
        "icon": "",
        "points": [],
        "before_label": "",
        "after_label": "",
        "before": [],
        "after": [],
    }
    return {**base, **kw}


def test_carousel_renders_every_layout_with_icons_and_escapes():
    point = {"icon": "phone", "title": "Point", "detail": "<script>x</script>", "value": "24/7"}
    slides = [
        _slide("cover", kicker="Salon owners", icon="missed-call"),
        _slide("steps", points=[point] * 3),
        _slide("stats", points=[point] * 2),
        _slide("compare", before=["a", "b"], after=["c", "d"]),
        _slide("checklist", points=[point] * 3),
        _slide("grid", points=[point] * 4),
        _slide("insight"),
        _slide("cta", kicker='DM me "CALLS"', icon="message"),
    ]
    html = render_html(slides)
    assert html.count('<section class="slide') == 8
    for layout in ("cover", "steps", "stats", "compare", "checklist", "grid", "insight", "cta"):
        assert f"layout-{layout}" in html
    assert html.count('class="step"') == 3
    assert "<svg" in html
    assert "<script>x</script>" not in html


def test_carousel_still_renders_old_title_body_slides():
    html = render_html([{"title": "Old slide", "body": "Saved before layouts existed"}])
    assert "layout-text" in html and "Old slide" in html


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


def test_schema_and_prompt_share_the_icon_set():
    from content_agent.drafting.draft import SCHEMA, _system_prompt
    from content_agent.visuals.icons import ICON_NAMES, icon

    slide = SCHEMA["properties"]["carousel"]["items"]
    assert set(slide["properties"]["icon"]["enum"]) == {"", *ICON_NAMES}
    assert "infographic first" in _system_prompt()
    assert "<svg" in icon("not-an-icon")  # unknown names fall back, never crash
