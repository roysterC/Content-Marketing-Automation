"""Database models. SQLite locally, Postgres/Supabase in production (same models)."""

from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

from content_agent.config import get_settings


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Item(Base):
    """A piece of research (article, Reddit thread, AI release note)."""

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    title_hash: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))  # e.g. salons, ai_news
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Filled in by the scorer
    # new -> scored -> drafted | discarded
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)
    relevance_score: Mapped[int | None] = mapped_column(Integer)
    business_type: Mapped[str | None] = mapped_column(String(100))
    angle: Mapped[str | None] = mapped_column(Text)
    pillar: Mapped[str | None] = mapped_column(String(30))
    score_reason: Mapped[str | None] = mapped_column(Text)

    drafts: Mapped[list["Draft"]] = relationship(back_populates="item")


class Draft(Base):
    """One platform-specific draft awaiting Roy's approval."""

    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id"))
    group_id: Mapped[str] = mapped_column(String(36), index=True)  # links LI + FB variants
    platform: Mapped[str] = mapped_column(String(20))  # linkedin | facebook
    pillar: Mapped[str] = mapped_column(String(30))
    hook: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    first_comment: Mapped[str | None] = mapped_column(Text)  # LinkedIn: external links go here
    carousel: Mapped[list | None] = mapped_column(JSON)  # list of {title, body} slides
    carousel_path: Mapped[str | None] = mapped_column(String(500))
    factcheck: Mapped[dict | None] = mapped_column(JSON)
    # The single-image visual's content, {"kind": "infographic" | "orgchart", "data": {...}},
    # kept so the painted-image prompt can be rebuilt (e.g. in another art style).
    visual: Mapped[dict | None] = mapped_column(JSON)
    # Painted image Roy made in Gemini and sent back to the bot (shared by the LI/FB pair).
    painted_path: Mapped[str | None] = mapped_column(String(500))

    # pending -> sent -> approved -> posted, or rejected (an edit puts it back to sent)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    telegram_message_id: Mapped[int | None] = mapped_column(Integer)
    # Filled in when Roy taps "Posted" in Telegram (Phase 4 analytics reads these).
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    post_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    item: Mapped[Item | None] = relationship(back_populates="drafts")


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        url = get_settings().database_url
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(url)
    return _engine


def _add_missing_columns(engine) -> None:
    """Tiny migration: add columns that exist in the models but not yet in the database.
    create_all() only creates missing tables, so new nullable columns on existing tables
    (e.g. drafts.posted_at) would otherwise be missing on the VPS."""
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                col_type = column.type.compile(dialect=engine.dialect)
                conn.execute(
                    text(f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {col_type}')
                )


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _add_missing_columns(engine)


def session() -> Session:
    return Session(get_engine(), expire_on_commit=False)
