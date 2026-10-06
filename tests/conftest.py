"""Shared test helpers."""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine

from content_agent import db


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
