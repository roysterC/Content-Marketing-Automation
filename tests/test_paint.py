"""Painted-image prompts, the Telegram flow around them, and the image check."""

import asyncio
import json
import subprocess
from types import SimpleNamespace

import pytest
from PIL import Image
from sqlalchemy import create_engine

from content_agent import db, llm
from content_agent.approval import telegram_bot as tb
from content_agent.drafting import imagecheck
from content_agent.visuals import paint

IDEA = {
    "eyebrow": "Automation idea",
    "sector": "Nail salons",
    "title": "Turn missed calls into bookings",
    "problem": "You're mid-manicure, the phone rings, and by the time you're free the "
    "caller has booked somewhere else.",
    "steps": [
        {"icon": "missed-call", "title": "Call goes unanswered", "detail": "Your phone "
         "line spots the missed call straight away, even mid-appointment."},
        {"icon": "message", "title": "Instant text back", "detail": "The caller gets a "
         "friendly text within seconds with your booking link."},
        {"icon": "calendar", "title": "They pick a slot", "detail": "They choose a free "
         "time in your booking system without waiting for you."},
        {"icon": "bell", "title": "Reminder the day before", "detail": "An automatic "
         "reminder cuts no-shows and lets them rebook easily."},
        {"icon": "star", "title": "Review request after", "detail": "A thank-you text asks "
         "happy clients for a Google review."},
    ],
    "impact": [
        {"icon": "pound", "value": "~£300", "label": "a week in rescued bookings"},
        {"icon": "clock", "value": "~2 hrs", "label": "less time on the phone"},
        {"icon": "check", "value": "24/7", "label": "every caller gets a reply"},
    ],
    "impact_note": "Illustrative estimates for a typical salon",
    "scene": "a nail technician mid-manicure while the salon phone rings on the front desk",
    "cta": 'DM me "CALLS" to see it working',
}  # fmt: skip

CHART = {
    "title_before": "Your Barbershop's ",
    "title_accent": "AI Team",
    "title_after": "",
    "subtitle": "12 automations, organised like real staff",
    "root_label": "The owner",
    "root_name": "Your barbershop",
    "root_icon": "user",
    "departments": [
        {
            "name": f"Department {d}",
            "icon": "phone",
            "roles": [
                {"icon": "message", "name": f"Job {d}{r}", "nickname": "Missed-Call Hero",
                 "does": "texts back callers you missed"}
                for r in range(4)
            ],
        }
        for d in range(5)
    ],
    "cta": 'DM me "TEAM" for the full breakdown',
}  # fmt: skip


@pytest.mark.parametrize("style", paint.style_names())
def test_infographic_prompt_quotes_every_piece_of_copy(style):
    prompt = paint.build_prompt("infographic", IDEA, style)
    for text in [IDEA["title"], IDEA["problem"], IDEA["impact_note"], IDEA["cta"]]:
        assert f"“{text}”" in prompt
    for step in IDEA["steps"]:
        assert f"“{step['title']}”" in prompt and f"“{step['detail']}”" in prompt
    for stat in IDEA["impact"]:
        assert f"“{stat['value']}”" in prompt and f"“{stat['label']}”" in prompt
    assert IDEA["scene"] in prompt and "4:5" in prompt
    assert "“Roy · Automation for busy small businesses”" in prompt
    assert paint.load_styles()["styles"][style]["look"] in prompt  # style repeated verbatim


@pytest.mark.parametrize("style", paint.style_names())
def test_largest_prompts_fit_in_one_telegram_message(style):
    # The biggest visuals the schemas allow: 5 steps / 3 outcomes, 5 departments x 4 roles.
    assert len(paint.build_prompt("infographic", IDEA, style)) < tb.TELEGRAM_LIMIT
    assert len(paint.build_prompt("orgchart", CHART, style)) < tb.TELEGRAM_LIMIT


def test_orgchart_prompt_has_accent_and_every_card():
    prompt = paint.build_prompt("orgchart", CHART)
    assert "“Your Barbershop's AI Team”" in prompt and "words “AI Team”\n   in amber" in prompt
    assert prompt.count("“Missed-Call Hero”") == 20


def test_active_style_is_default_and_unknown_style_errors():
    active = paint.load_styles()["active"]
    assert paint.build_prompt("infographic", IDEA) == paint.build_prompt(
        "infographic", IDEA, active
    )
    with pytest.raises(ValueError, match="Unknown art style"):
        paint.build_prompt("infographic", IDEA, "crayon")


def test_vignette_falls_back_to_icon_name():
    assert paint.vignette("phone") == "a ringing phone"
    assert paint.vignette("new-thing") == "new thing"


# --- Telegram ---


class FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kw):
        self.sent.append(("message", text, kw))
        return SimpleNamespace(message_id=len(self.sent))

    async def send_document(self, chat_id, document, **kw):
        self.sent.append(("document", str(document), kw))


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(db, "_engine", engine)
    monkeypatch.setattr(tb, "OUTPUT_DIR", tmp_path)
    db.init_db()
    return engine


def _pair(session, visual=True):
    v = {"kind": "infographic", "data": IDEA} if visual else None
    li = db.Draft(platform="linkedin", pillar="workflow", group_id="g1", hook="h", body="LI",
                  visual=v)  # fmt: skip
    fb = db.Draft(platform="facebook", pillar="workflow", group_id="g1", hook="h", body="FB",
                  visual=v)  # fmt: skip
    session.add_all([li, fb])
    session.commit()
    return li, fb


def test_linkedin_draft_is_followed_by_steps_then_the_bare_prompt(temp_db):
    with db.session() as s:
        li, fb = _pair(s)
        bot = FakeBot()
        asyncio.run(tb._send_draft(bot, 1, li))
        texts = [t for k, t, _ in bot.sent if k == "message"]
        assert tb.PAINT_RE.match(texts[-2]).group(1) == str(li.id)
        assert texts[-1] == tb.paint_prompt(li)

        bot = FakeBot()
        asyncio.run(tb._send_draft(bot, 1, fb))  # the pair shares one image: no second prompt
        assert not any(tb.PAINT_RE.match(t) for k, t, _ in bot.sent if k == "message")


def test_no_prompt_without_a_visual_or_when_editing(temp_db):
    with db.session() as s:
        li, _ = _pair(s, visual=False)
        bot = FakeBot()
        asyncio.run(tb._send_draft(bot, 1, li))
        assert len(bot.sent) == 1  # just the draft

        li.visual = {"kind": "infographic", "data": IDEA}
        bot = FakeBot()
        asyncio.run(tb._send_draft(bot, 1, li, with_prompt=False))
        assert len(bot.sent) == 1


def test_paint_target_by_steps_reply_prompt_reply_or_latest(temp_db):
    with db.session() as s:
        old, _ = _pair(s)
        latest = db.Draft(platform="linkedin", pillar="workflow", group_id="g2", hook="h",
                          body="b", visual={"kind": "orgchart", "data": CHART})  # fmt: skip
        s.add(latest)
        s.commit()
        assert tb.paint_target(s, tb.PAINT_STEPS.format(id=old.id)).id == old.id
        style = paint.style_names()[1]
        assert tb.paint_target(s, tb.paint_prompt(old, style)).id == old.id
        assert tb.paint_target(s, None).id == latest.id
        assert tb.paint_target(s, "some other message").id == latest.id


def test_kits_prefer_the_painted_image(temp_db, tmp_path):
    painted = tmp_path / "painted.png"
    painted.write_bytes(b"png")
    pdf = tmp_path / "c.pdf"
    pdf.write_bytes(b"%PDF")
    fb = db.Draft(id=8, platform="facebook", hook="h", body="FB", painted_path=str(painted))
    bot = FakeBot()
    asyncio.run(tb.send_kit(bot, 1, fb))
    assert ("document", str(painted)) in [(k, t) for k, t, _ in bot.sent]

    li = db.Draft(id=9, platform="linkedin", hook="h", body="LI", carousel_path=str(pdf),
                  painted_path=str(painted))  # fmt: skip
    bot = FakeBot()
    asyncio.run(tb.send_kit(bot, 1, li))
    docs = [(t, kw.get("caption")) for k, t, kw in bot.sent if k == "document"]
    assert docs[0][0] == str(pdf) and docs[1][0] == str(painted)


def test_on_image_saves_for_the_pair_and_reports_the_check(temp_db, monkeypatch, tmp_path):
    monkeypatch.setattr(
        imagecheck, "check_image", lambda path, prompt: {"verdict": "ok", "issues": []}
    )
    replies = []

    class TgFile:
        async def download_to_drive(self, path):
            Image.new("RGB", (8, 10)).save(path)

    async def get_file(file_id):
        return TgFile()

    async def reply_text(text, **kw):
        replies.append(text)

    with db.session() as s:
        li, _ = _pair(s)
        li_id = li.id
    msg = SimpleNamespace(
        photo=(),
        document=SimpleNamespace(file_id="f", file_name="Gemini_Image.PNG"),
        reply_to_message=SimpleNamespace(text=tb.PAINT_STEPS.format(id=li_id)),
        reply_text=reply_text,
    )
    update = SimpleNamespace(message=msg)
    context = SimpleNamespace(bot=SimpleNamespace(get_file=get_file))
    asyncio.run(tb.on_image(update, context))

    with db.session() as s:
        paths = {d.painted_path for d in s.query(db.Draft).filter_by(group_id="g1")}
    assert paths == {str(tmp_path / "painted" / "g1.png")}
    assert "Saved as the image for" in replies[0] and replies[-1].startswith("✅")


# --- image check and image input to Claude ---


def test_check_image_sends_a_shrunk_jpeg(monkeypatch, tmp_path):
    big = tmp_path / "big.png"
    Image.new("RGBA", (2160, 2700)).save(big)
    seen = {}

    def fake_ask_json(**kw):
        (image,) = kw["images"]
        with Image.open(image) as im:
            seen.update(size=im.size, format=im.format)
        return {"verdict": "needs_attention", "issues": [{"text": "Boking", "problem": "typo"}]}

    monkeypatch.setattr(imagecheck, "ask_json", fake_ask_json)
    result = imagecheck.check_image(big, "prompt with “Booking”")
    assert max(seen["size"]) == imagecheck.MAX_EDGE and seen["format"] == "JPEG"
    assert "Boking: typo" in imagecheck.format_check(result)


def test_claude_code_backend_reads_images_with_the_read_tool_only(monkeypatch, tmp_path):
    image = tmp_path / "x.PNG"
    image.write_bytes(b"png")
    seen = {}

    def run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        copied = [line for line in kw["input"].splitlines() if line.endswith(".png")]
        seen["copied_exists"] = all(__import__("os").path.exists(p) for p in copied)
        out = json.dumps({"is_error": False, "structured_output": {"ok": True}})
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(subprocess, "run", run)
    llm.ask_json(system="s", prompt="look", schema={}, images=[image])
    cmd = seen["cmd"]
    assert cmd[cmd.index("--tools") + 1] == "Read"
    assert cmd[cmd.index("--allowedTools") + 1] == "Read"
    assert "Read tool" in seen["input"] and seen["copied_exists"]


def test_api_backend_sends_image_blocks_before_the_text(monkeypatch, tmp_path):
    image = tmp_path / "x.jpg"
    image.write_bytes(b"jpg")
    seen = {}

    class Messages:
        def create(self, **kw):
            seen.update(kw)
            return SimpleNamespace(
                usage=SimpleNamespace(input_tokens=1, cache_read_input_tokens=0, output_tokens=1),
                model="m",
                stop_reason="end_turn",
                content=[SimpleNamespace(type="text", text='{"ok": true}')],
            )

    monkeypatch.setattr(
        llm, "_client", lambda: SimpleNamespace(beta=SimpleNamespace(messages=Messages()))
    )
    monkeypatch.setattr(llm, "get_settings", lambda: SimpleNamespace(
        llm_backend="api", claude_model="m"))  # fmt: skip
    assert llm.ask_json(system="s", prompt="look", schema={}, images=[image]) == {"ok": True}
    image_block, text_block = seen["messages"][0]["content"]
    assert image_block["source"]["media_type"] == "image/jpeg"
    assert text_block == {"type": "text", "text": "look"}


def test_oversized_prompt_goes_as_a_file(monkeypatch):
    monkeypatch.setattr(tb, "paint_prompt", lambda d, style=None: "x" * (tb.TELEGRAM_LIMIT + 1))
    bot = FakeBot()
    asyncio.run(tb.send_paint_prompt(bot, 1, db.Draft(id=3)))
    (_, steps, _), (kind, _, kw) = bot.sent
    assert tb.PAINT_RE.match(steps) and kind == "document"
    assert kw["filename"] == "gemini-prompt-3.txt"


def test_paint_command_resends_a_prompt_in_another_style(temp_db):
    with db.session() as s:
        li, fb = _pair(s)
    bot = FakeBot()
    replies = []

    async def reply_text(text, **kw):
        replies.append(text)

    def update():
        return SimpleNamespace(
            message=SimpleNamespace(reply_text=reply_text),
            effective_chat=SimpleNamespace(id=1),
        )

    context = SimpleNamespace(bot=bot, args=[f"#{fb.id}", "Watercolour"])
    asyncio.run(tb.on_paint(update(), context))
    assert bot.sent[-1][1] == tb.paint_prompt(li, "watercolour")  # FB id -> its LI pair

    asyncio.run(tb.on_paint(update(), SimpleNamespace(bot=bot, args=["crayon"])))
    assert replies[-1].startswith("Art styles:")
