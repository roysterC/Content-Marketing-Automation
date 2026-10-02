"""Pull RSS/Atom feeds into the items table, skipping anything already seen."""

import hashlib
import html
import logging
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from time import struct_time

import feedparser
import yaml
from sqlalchemy import select

from content_agent.config import CONFIG_DIR
from content_agent.db import Item, session

log = logging.getLogger(__name__)

# Reddit blocks the default Python user agent.
USER_AGENT = "content-agent/0.1 (research feed reader)"
MAX_SUMMARY_CHARS = 2000
MAX_ITEMS_PER_SOURCE = 30  # some feeds return their whole archive
DELAY_BETWEEN_SOURCES = 3  # seconds; Reddit returns 429 if hit back-to-back
RATE_LIMIT_RETRY_DELAY = 30


@dataclass
class Source:
    name: str
    url: str
    category: str


def load_sources(path=CONFIG_DIR / "sources.yaml") -> list[Source]:
    data = yaml.safe_load(path.read_text())
    return [Source(**s) for s in data["sources"]]


def title_hash(title: str) -> str:
    """Normalise a title so the same story from two feeds dedupes."""
    norm = re.sub(r"[^a-z0-9 ]", "", title.lower())
    norm = re.sub(r"\s+", " ", norm).strip()
    return hashlib.sha256(norm.encode()).hexdigest()


def clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:MAX_SUMMARY_CHARS]


def _to_dt(value: struct_time | None) -> datetime | None:
    return datetime(*value[:6], tzinfo=UTC) if value else None


def fetch_source(source: Source) -> list[Item]:
    feed = feedparser.parse(source.url, agent=USER_AGENT)
    if feed.get("status") == 429:
        time.sleep(RATE_LIMIT_RETRY_DELAY)
        feed = feedparser.parse(source.url, agent=USER_AGENT)
    if not feed.entries:
        log.warning(
            "No entries from %s (HTTP %s) %s",
            source.name,
            feed.get("status"),
            feed.get("bozo_exception", ""),
        )
        return []
    items = []
    for entry in feed.entries[:MAX_ITEMS_PER_SOURCE]:
        url = entry.get("link")
        title = clean_text(entry.get("title", ""))
        if not url or not title:
            continue
        items.append(
            Item(
                url=url,
                title=title[:500],
                title_hash=title_hash(title),
                summary=clean_text(entry.get("summary", "")),
                source=source.name,
                category=source.category,
                published_at=_to_dt(entry.get("published_parsed") or entry.get("updated_parsed")),
            )
        )
    return items


def ingest(only: str | None = None) -> int:
    """Fetch every source and store new items. Returns the number added."""
    added = 0
    with session() as db:
        seen_urls = set(db.scalars(select(Item.url)))
        seen_titles = set(db.scalars(select(Item.title_hash)))
        sources = [s for s in load_sources() if not only or s.name == only]
        for n, source in enumerate(sources):
            if n:
                time.sleep(DELAY_BETWEEN_SOURCES)
            fetched = fetch_source(source)
            new = 0
            for item in fetched:
                if item.url in seen_urls or item.title_hash in seen_titles:
                    continue
                seen_urls.add(item.url)
                seen_titles.add(item.title_hash)
                db.add(item)
                new += 1
            log.info("%s: %d fetched, %d new", source.name, len(fetched), new)
            added += new
        db.commit()
    return added
