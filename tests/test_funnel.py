"""Lead funnel: config, CTAs added to posts, DM text in the kit, the guide renderer."""

import asyncio
import json

import pytest
from conftest import FakeBot

from content_agent import funnel as funnel_mod
from content_agent import generate
from content_agent.approval import telegram_bot as tb
from content_agent.db import Draft
from content_agent.drafting import guide
from content_agent.formats import FORMATS
from content_agent.visuals.render import guide_page_labels, render_guide_html

LIVE = funnel_mod.Funnel(
    guide_title="The 5 automations every salon should run",
    guide_subtitle="sub",
    guide_sector="salons",
    guide_url="https://drive.example/guide",
    keyword="GUIDE",
    booking_url="https://cal.example/roy",
    for_sectors=("nail salons", "barbers"),
)


def _result():
    return {
        "linkedin": {"hook": "h", "body": "h\n\nPost.", "first_comment": "https://source"},
        "facebook": {"hook": "h", "body": "h\n\nShort post."},
    }


def test_shipped_funnel_is_not_live_until_a_link_is_added():
    f = funnel_mod.load_funnel()
    assert not f.live and f.keyword == "GUIDE"
    assert "nail salons" in f.for_sectors
    assert not f.offers_guide("nail salons")


def test_guide_cta_only_for_the_sectors_it_suits():
    assert LIVE.offers_guide("Nail Salons ")
    assert not LIVE.offers_guide("plumbers and electricians")


def test_apply_adds_missing_ctas_without_duplicating():
    r = LIVE.apply(_result())
    assert r["linkedin"]["first_comment"].startswith(LIVE.linkedin_comment())
    assert r["linkedin"]["first_comment"].endswith("https://source")
    assert "first comment" in r["linkedin"]["body"]
    assert "https://" not in r["linkedin"]["body"]  # links stay out of the LinkedIn body
    assert "Comment GUIDE" in r["facebook"]["body"]
    again = LIVE.apply(json.loads(json.dumps(r)))
    assert again == r


def test_prompt_gets_cta_instructions_only_when_live_and_relevant():
    idea = FORMATS["idea"]
    assert "Call to action" in generate.build_prompt(idea, "barbers", "", LIVE)
    assert "Call to action" not in generate.build_prompt(idea, "plumbers", "", LIVE)
    off = funnel_mod.Funnel(**{**LIVE.__dict__, "guide_url": ""})
    assert "Call to action" not in generate.build_prompt(idea, "barbers", "", off)


def test_offer_needs_the_guide(monkeypatch):
    monkeypatch.setattr(generate, "load_funnel", lambda: LIVE)
    monkeypatch.setattr(generate, "guide_outline", lambda f: "")
    with pytest.raises(RuntimeError, match="content-agent guide"):
        generate.generate("offer")


def test_dm_text_has_guide_and_booking_links():
    text = LIVE.dm_text()
    assert LIVE.guide_url in text and LIVE.booking_url in text


def test_kit_adds_dm_text_for_posts_that_promote_the_guide(monkeypatch):
    monkeypatch.setattr(tb, "load_funnel", lambda: LIVE)
    bot = FakeBot()
    d = Draft(id=8, platform="facebook", hook="h", body="Comment GUIDE for the guide")
    asyncio.run(tb.send_kit(bot, 1, d))
    texts = [t for k, t, _ in bot.sent if k == "message"]
    assert LIVE.dm_text() in texts and any("comments GUIDE" in t for t in texts)

    bot = FakeBot()
    asyncio.run(tb.send_kit(bot, 1, Draft(id=9, platform="facebook", hook="h", body="No ask")))
    assert LIVE.dm_text() not in [t for k, t, _ in bot.sent if k == "message"]


SAMPLE = {
    "title": "The 5 automations every salon should run",
    "subtitle": "Stop losing bookings",
    "sector_label": "Salon owners",
    "intro": {"headline": "Why", "body": "Because.", "stats": []},
    "automations": [
        {
            "icon": "phone",
            "name": f"Automation {i}",
            "nickname": "Helper",
            "problem": "A problem.",
            "steps": [{"icon": "check", "title": "Step", "detail": "Detail"}] * 3,
            "needs": ["A thing", "Another"],
            "time_saved": "~1 hr/wk",
            "time_assumption": "If you do X",
            "effort": "Quick win",
        }
        for i in range(1, 6)
    ],
    "start_here": {"headline": "Start", "advice": "Do the first one."},
    "cta": {"headline": "Want help?", "body": "Book a call."},
}


def test_guide_html_has_a_page_per_label_and_qr_only_with_booking_link():
    html = render_guide_html(SAMPLE, "https://cal.example/roy")
    assert html.count('<section class="page') == len(guide_page_labels(SAMPLE)) == 9
    assert "<svg" in html.split("Next step")[1] and 'href="https://cal.example/roy"' in html
    assert "cal.example" not in render_guide_html(SAMPLE, "")


def test_guide_outline_reads_saved_content(monkeypatch, tmp_path):
    monkeypatch.setattr(guide, "GUIDES_DIR", tmp_path)
    assert guide.outline(LIVE) == ""
    (tmp_path / f"{guide.slug(LIVE.guide_title)}.json").write_text(json.dumps({"guide": SAMPLE}))
    text = guide.outline(LIVE)
    assert "5. Automation 5 (Quick win, ~1 hr/wk; If you do X)" in text
