"""Posting kit and Posted flow, against a fake Telegram bot and a temporary database."""

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from content_agent import db
from content_agent.approval import telegram_bot as tb


class FakeBot:
    def __init__(self):
        self.sent = []  # (kind, text_or_path, kwargs)

    async def send_message(self, chat_id, text, **kw):
        self.sent.append(("message", text, kw))
        return SimpleNamespace(message_id=len(self.sent))

    async def send_document(self, chat_id, document, **kw):
        self.sent.append(("document", str(document), kw))


@pytest.fixture
def temp_db(monkeypatch, tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setattr(db, "_engine", engine)
    db.init_db()
    return engine


def _linkedin_draft(tmp_path, **kw):
    pdf = tmp_path / "carousel.pdf"
    pdf.write_bytes(b"%PDF")
    base = {
        "id": 5,
        "platform": "linkedin",
        "pillar": "workflow",
        "group_id": "g",
        "hook": "Every missed call\nis a missed booking",
        "body": "Every missed call\nis a missed booking\n\nFull post text.",
        "first_comment": "https://example.com/source",
        "carousel": [{"layout": "cover", "title": "Stop losing bookings"}],
        "carousel_path": str(pdf),
    }
    return db.Draft(**{**base, **kw})


def test_linkedin_kit_sends_clean_copyable_pieces_in_order(tmp_path):
    bot = FakeBot()
    asyncio.run(tb.send_kit(bot, 1, _linkedin_draft(tmp_path)))
    kinds = [k for k, _, _ in bot.sent]
    assert kinds == ["message", "message", "document", "message", "message"]
    steps, body, pdf, comment, done = bot.sent
    assert "LinkedIn kit for #5" in steps[1]
    assert body[1] == "Every missed call\nis a missed booking\n\nFull post text."  # text only
    assert pdf[1].endswith("carousel.pdf") and pdf[2]["caption"] == "Stop losing bookings"
    assert comment[1] == "https://example.com/source"
    assert "posted:5" in str(done[2]["reply_markup"].to_dict())


def test_facebook_kit_has_text_and_no_first_comment(tmp_path):
    bot = FakeBot()
    d = db.Draft(id=6, platform="facebook", pillar="workflow", hook="h", body="FB text")
    asyncio.run(tb.send_kit(bot, 1, d))
    texts = [t for k, t, _ in bot.sent if k == "message"]
    assert "FB text" in texts and not any("example.com" in t for t in texts)


def test_document_title_falls_back_to_hook():
    d = db.Draft(id=7, platform="linkedin", hook="First line\nsecond", carousel=None)
    assert tb.document_title(d) == "First line"


def _button(data, chat_id="42"):
    edits = []

    async def answer():
        return None

    async def edit_markup(markup):
        edits.append(markup)

    query = SimpleNamespace(
        data=data,
        message=SimpleNamespace(chat_id=chat_id),
        answer=answer,
        edit_message_reply_markup=edit_markup,
    )
    return SimpleNamespace(callback_query=query), edits


def test_approve_sends_kit_and_posted_records_status_and_link(monkeypatch, tmp_path, temp_db):
    monkeypatch.setattr(tb, "get_settings", lambda: SimpleNamespace(telegram_chat_id="42"))
    with db.session() as s:
        s.add(_linkedin_draft(tmp_path, id=None, status="sent"))
        s.commit()
        draft_id = s.query(db.Draft).one().id

    bot = FakeBot()
    context = SimpleNamespace(bot=bot)
    update, _ = _button(f"approve:{draft_id}")
    asyncio.run(tb.on_button(update, context))
    with db.session() as s:
        assert s.get(db.Draft, draft_id).status == "approved"
    assert any("LinkedIn kit" in t for k, t, _ in bot.sent if k == "message")

    update, _ = _button(f"posted:{draft_id}")
    asyncio.run(tb.on_button(update, context))
    prompt = bot.sent[-1][1]
    assert prompt == tb.LINK_PROMPT.format(id=draft_id)

    replies = []

    async def reply_text(text):
        replies.append(text)

    msg = SimpleNamespace(
        text=" https://www.linkedin.com/feed/update/urn:li:share:1 ",
        reply_to_message=SimpleNamespace(text=prompt),
        reply_text=reply_text,
        chat_id=42,
    )
    asyncio.run(tb.on_reply(SimpleNamespace(message=msg), context))
    with db.session() as s:
        d = s.get(db.Draft, draft_id)
        assert d.status == "posted" and d.posted_at is not None
        assert d.post_url == "https://www.linkedin.com/feed/update/urn:li:share:1"
    assert replies == [f"Saved the link for #{draft_id}."]


def test_buttons_from_other_chats_are_ignored(monkeypatch, tmp_path, temp_db):
    monkeypatch.setattr(tb, "get_settings", lambda: SimpleNamespace(telegram_chat_id="42"))
    with db.session() as s:
        s.add(_linkedin_draft(tmp_path, id=None, status="sent"))
        s.commit()
        draft_id = s.query(db.Draft).one().id
    update, _ = _button(f"approve:{draft_id}", chat_id="999")
    asyncio.run(tb.on_button(update, SimpleNamespace(bot=FakeBot())))
    with db.session() as s:
        assert s.get(db.Draft, draft_id).status == "sent"
