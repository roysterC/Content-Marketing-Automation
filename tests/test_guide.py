"""Setup guides: schema, request parsing, template, the make/rerender flow (Claude faked)."""

import asyncio
import json
from datetime import date
from pathlib import Path

import pytest
from conftest import FakeBot

from content_agent.approval import telegram_bot as tb
from content_agent.drafting import guide
from content_agent.funnel import load_funnel
from content_agent.visuals.render import GUIDE_PAGES, render_guide_html
from content_agent.visuals.schemas import GUIDE

SAMPLE = json.loads((Path(__file__).parent / "fixtures" / "setup_guide.json").read_text())


def _conforms(value, schema, path="guide"):
    """Small structural check: required keys present, no extras, enums respected."""
    if schema.get("type") == "object":
        assert set(value) == set(schema["required"]) == set(schema["properties"]), path
        for k, sub in schema["properties"].items():
            _conforms(value[k], sub, f"{path}.{k}")
    elif schema.get("type") == "array":
        for i, item in enumerate(value):
            _conforms(item, schema["items"], f"{path}[{i}]")
    elif "enum" in schema:
        assert value in schema["enum"], path


def test_sample_matches_schema():
    _conforms(SAMPLE, GUIDE)


def _field_names(schema):
    for name, sub in schema.get("properties", {}).items():
        yield name
        yield from _field_names(sub)
    if "items" in schema:
        yield from _field_names(schema["items"])


def test_schema_has_no_price_fields():
    names = set(_field_names(GUIDE))
    assert "cost" in names  # the reader's lost bookings, which is fine
    assert not {n for n in names if any(w in n for w in ("price", "fee", "running"))}


def test_parse_request():
    assert guide.parse_request("missed-call text-back for nail salons") == (
        "missed-call text-back",
        "nail salons",
    )
    assert guide.parse_request("reminders for clients for barbers") == (
        "reminders for clients",
        "barbers",
    )
    with pytest.raises(ValueError):
        guide.parse_request("missed calls")


def test_checked_label():
    assert guide.checked_label(date(2026, 10, 6)) == "October 2026"


def test_template_renders_every_page_with_escaped_highlights():
    g = json.loads(json.dumps(SAMPLE))
    g["templates"][0]["message"] = "Hi <script>x</script> book here: [your link]"
    html = render_guide_html(g, "October 2026", "https://cal.example/roy")
    assert html.count('<section class="page') == len(GUIDE_PAGES) == 8
    assert "<b>your link</b>" in html and "<script>x" not in html
    assert "Tools checked October 2026" in html
    assert 'href="https://cal.example/roy"' in html and "<svg" in html.split("Book a free")[1]
    assert "cal.example" not in render_guide_html(SAMPLE, "October 2026")


def test_make_guide_checks_saves_and_rerenders(monkeypatch, tmp_path):
    monkeypatch.setattr(guide, "GUIDES_DIR", tmp_path)
    monkeypatch.setattr(
        guide, "ask_json", lambda **kw: {**json.loads(json.dumps(SAMPLE)), "research_notes": "n"}
    )
    monkeypatch.setattr(guide, "factcheck", lambda drafts, src: {"verdict": "pass", "issues": []})
    issue = {"claim": "steps[2]", "problem": "vague", "suggestion": "say which setting"}
    monkeypatch.setattr(
        guide, "review", lambda g, t, s: {"verdict": "needs_attention", "issues": [issue]}
    )
    rendered = []

    def fake_render(g, stem, checked):
        rendered.append(checked)
        pdf = stem.with_suffix(".pdf")
        pdf.write_bytes(b"%PDF")
        return pdf, g

    monkeypatch.setattr(guide, "_render", fake_render)
    r = guide.make_guide("missed-call text-back", "nail salons")
    assert r.pdf.name == "nail-salons--missed-call-text-back.pdf"
    saved = json.loads(r.content.read_text())
    assert saved["research_notes"] == "n" and "research_notes" not in saved["guide"]
    assert saved["checked"] == rendered[0]
    assert r.review["issues"] == [issue]

    again = guide.rerender()
    assert again.content == r.content and rendered == [saved["checked"]] * 2


def test_guide_summary_lists_both_checks():
    text = tb.guide_summary(
        "missed-call text-back",
        "nail salons",
        {"verdict": "pass", "issues": []},
        {
            "verdict": "needs_attention",
            "issues": [{"claim": "steps[2]", "problem": "vague", "suggestion": "name it"}],
        },
    )
    assert "✅ Fact-check passed" in text
    assert "⚠️ Guide review" in text and "steps[2]: vague → name it" in text


def test_send_guide_sends_pdf_cover_and_summary(tmp_path):
    content = tmp_path / "g.json"
    content.write_text(json.dumps({"topic": "t", "sector": "s"}))
    (tmp_path / "g.pdf").write_bytes(b"%PDF")
    (tmp_path / "g-cover.png").write_bytes(b"png")
    result = guide.GuideResult(
        tmp_path / "g.pdf", tmp_path / "g-cover.png", content, {}, {"verdict": "pass"}
    )
    bot = FakeBot()
    asyncio.run(tb._send_guide(bot, 1, result))
    assert [k for k, _, _ in bot.sent] == ["document", "document", "message"]
    assert "Set-up guide: t, for s" in bot.sent[-1][1]


def test_funnel_defaults():
    f = load_funnel()
    assert f.keyword == "GUIDE" and f.booking_url == ""
