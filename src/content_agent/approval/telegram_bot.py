"""Telegram approval gate and posting kit.

Every draft gets Approve / Edit / Reject buttons. Approving sends a *posting kit*: the
post text, the file to attach and the first comment as separate messages (so each is a
single long-press -> Copy), then a "Posted" button. Roy posts by hand; tapping Posted
records it (and optionally the post's link) for Phase 4 analytics. Nothing is published
from here.

Entry points:
- send_pending(): push any pending drafts to the chat, then exit (safe to run from cron).
- send_reminders(): nudge about approved drafts not yet marked posted (cron).
- run_bot(): long-running process that handles buttons, replies and commands.
"""

import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from telegram import Bot, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from content_agent.config import get_settings
from content_agent.db import Draft, session
from content_agent.formats import FORMATS

log = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
EDIT_PROMPT = "Edit draft #{id}: reply to this message with the full new post text."
EDIT_RE = re.compile(r"^Edit draft #(\d+):")
LINK_PROMPT = "Posted #{id}. Reply to this message with the post's link (optional)."
LINK_RE = re.compile(r"^Posted #(\d+)\.")


def _settings():
    s = get_settings()
    if not s.telegram_bot_token or not s.telegram_chat_id:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    return s


def format_draft(d: Draft) -> str:
    platform = "LinkedIn" if d.platform == "linkedin" else "Facebook"
    lines = [f"#{d.id} · {platform} · {d.pillar}", "", d.body]
    if d.first_comment:
        lines += ["", "— First comment —", d.first_comment]
    fmt = FORMATS.get(d.item.url.split(":", 1)[0]) if d.item else None
    if fmt:
        lines += ["", f"Source: Claude's own {fmt.label} ({d.item.business_type}), web-checked"]
    elif d.item:
        lines += ["", f"Source: {d.item.source} — {d.item.url}"]
    fc = d.factcheck or {}
    if fc.get("verdict") == "needs_attention":
        lines += ["", "⚠️ Fact-check:"]
        lines += [f"• {i['claim']} — {i['problem']}" for i in fc.get("issues", [])]
    elif fc:
        lines += ["", "✅ Fact-check passed"]
    text = "\n".join(lines)
    if len(text) > TELEGRAM_LIMIT:
        text = text[: TELEGRAM_LIMIT - 20] + "\n…(truncated)"
    return text


def keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve:{draft_id}"),
                InlineKeyboardButton("✏️ Edit", callback_data=f"edit:{draft_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject:{draft_id}"),
            ]
        ]
    )


def _image(d: Draft) -> Path | None:
    from content_agent.config import OUTPUT_DIR
    from content_agent.visuals.render import poster_path

    for image in (poster_path(d.id), OUTPUT_DIR / "ideas" / f"draft-{d.id}.png"):
        if image.exists():  # ideas/ is where images were saved before posters/ existed
            return image
    return None


def _carousel(d: Draft) -> Path | None:
    return Path(d.carousel_path) if d.carousel_path and Path(d.carousel_path).exists() else None


def document_title(d: Draft) -> str:
    """Title LinkedIn asks for when you attach a PDF: the carousel's cover headline."""
    if d.carousel and d.carousel[0].get("title"):
        return d.carousel[0]["title"]
    return d.hook.splitlines()[0][:100] if d.hook else f"Draft {d.id}"


def posted_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Posted", callback_data=f"posted:{draft_id}"),
                InlineKeyboardButton("🔁 Resend kit", callback_data=f"kit:{draft_id}"),
            ]
        ]
    )


async def send_kit(bot: Bot, chat_id, d: Draft) -> None:
    """Everything needed to post by hand, one copyable piece per message."""
    if d.platform == "linkedin":
        carousel, image = _carousel(d), _image(d)
        attach = "the PDF below (title in its caption)" if carousel else "the image below"
        steps = [
            f"📋 LinkedIn kit for #{d.id}",
            "1. Start a post and paste the text from the next message.",
            f"2. Attach {attach}.",
        ]
        if d.first_comment:
            steps.append("3. Once it's live, paste the first comment as a comment.")
        await bot.send_message(chat_id, "\n".join(steps))
        await bot.send_message(chat_id, d.body)
        if carousel:
            await bot.send_document(chat_id, carousel, caption=document_title(d))
        elif image:
            await bot.send_document(chat_id, image)
        if d.first_comment:
            await bot.send_message(chat_id, d.first_comment)
    else:
        await bot.send_message(
            chat_id,
            f"📋 Facebook kit for #{d.id}\n1. Paste the text from the next message.\n"
            "2. Add the image below.",
        )
        await bot.send_message(chat_id, d.body)
        if image := _image(d):
            await bot.send_document(chat_id, image)
    await bot.send_message(
        chat_id, f"Tap Posted once #{d.id} is live.", reply_markup=posted_keyboard(d.id)
    )


async def _send_draft(bot: Bot, chat_id: str, d: Draft) -> int:
    if image := _image(d):
        # As a document, not a photo: Telegram recompresses photos, and this is the
        # full-quality PNG to upload to LinkedIn/Facebook.
        await bot.send_document(chat_id, image, caption=f"Image for draft #{d.id}")
    if carousel := _carousel(d):
        await bot.send_document(chat_id, carousel, caption=f"Carousel for draft #{d.id}")
    msg = await bot.send_message(chat_id, format_draft(d), reply_markup=keyboard(d.id))
    return msg.message_id


async def _send_pending(bot: Bot, chat_id: str, ids: list[int] | None = None) -> int:
    with session() as db:
        query = select(Draft).where(Draft.status == "pending").order_by(Draft.id)
        if ids is not None:
            query = query.where(Draft.id.in_(ids))
        drafts = list(db.scalars(query))
        for d in drafts:
            d.telegram_message_id = await _send_draft(bot, chat_id, d)
            d.status = "sent"
            db.commit()
        return len(drafts)


def send_pending() -> int:
    s = _settings()

    async def main() -> int:
        async with Bot(s.telegram_bot_token) as bot:
            return await _send_pending(bot, s.telegram_chat_id)

    return asyncio.run(main())


def _issues(title: str, checks: dict) -> list[str]:
    if checks.get("verdict") == "needs_attention":
        return ["", f"⚠️ {title}:"] + [
            f"• {i['claim']}: {i['problem']} → {i['suggestion']}" for i in checks.get("issues", [])
        ]
    return ["", f"✅ {title} passed"] if checks else []


def guide_summary(topic: str, sector: str, checks: dict, review: dict) -> str:
    """The message sent with a new guide PDF."""
    lines = [f"📘 Set-up guide: {topic}, for {sector} (PDF and cover above)."]
    lines += _issues("Fact-check", checks) + _issues("Guide review", review)
    text = "\n".join(lines)
    return text if len(text) <= TELEGRAM_LIMIT else text[: TELEGRAM_LIMIT - 20] + "\n…(truncated)"


async def _send_guide(bot: Bot, chat_id, result) -> None:
    saved = json.loads(result.content.read_text())
    await bot.send_document(chat_id, result.pdf)
    if result.cover.exists():
        await bot.send_document(chat_id, result.cover)
    text = guide_summary(saved["topic"], saved["sector"], result.factcheck, result.review)
    await bot.send_message(chat_id, text)


def send_guide(result) -> None:
    s = _settings()

    async def main() -> None:
        async with Bot(s.telegram_bot_token) as bot:
            await _send_guide(bot, s.telegram_chat_id, result)

    asyncio.run(main())


GUIDE_USAGE = (
    "Usage: /guide missed-call text-back for nail salons\n"
    "or /guide rerender to redraw the latest guide (e.g. after adding a booking link)."
)


async def on_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/guide <topic> for <business type>, or /guide rerender."""
    from content_agent.drafting import guide as g

    text = " ".join(context.args).strip()
    if text.lower() == "rerender":
        run, what = g.rerender, "Redrawing the latest guide."
    else:
        try:
            topic, sector = g.parse_request(text)
        except ValueError:
            await update.message.reply_text(GUIDE_USAGE)
            return

        def run():
            return g.make_guide(topic, sector)

        what = f"Writing the {topic} guide for {sector}. This takes 5-10 minutes."
    await update.message.reply_text(what)
    try:
        result = await asyncio.to_thread(run)
    except Exception as e:
        log.exception("Guide failed")
        await update.message.reply_text(f"Guide failed: {e}"[:TELEGRAM_LIMIT])
        return
    await _send_guide(context.bot, update.effective_chat.id, result)


def send_reminders() -> int:
    """Nudge about drafts approved but not yet marked posted. Returns how many."""
    s = _settings()

    async def main() -> int:
        async with Bot(s.telegram_bot_token) as bot:
            with session() as db:
                waiting = list(
                    db.scalars(select(Draft).where(Draft.status == "approved").order_by(Draft.id))
                )
                for d in waiting:
                    platform = "LinkedIn" if d.platform == "linkedin" else "Facebook"
                    await bot.send_message(
                        s.telegram_chat_id,
                        f"⏰ #{d.id} ({platform}) is approved but not posted yet:\n"
                        f"{d.hook.splitlines()[0] if d.hook else ''}",
                        reply_markup=posted_keyboard(d.id),
                    )
                return len(waiting)

    return asyncio.run(main())


# --- long-running bot handlers ---


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if str(query.message.chat_id) != get_settings().telegram_chat_id:
        return
    action, _, raw_id = query.data.partition(":")
    draft_id = int(raw_id)

    with session() as db:
        d = db.get(Draft, draft_id)
        if d is None:
            await query.edit_message_reply_markup(None)
            return
        if action == "edit":
            await context.bot.send_message(
                query.message.chat_id,
                EDIT_PROMPT.format(id=draft_id),
                reply_markup=ForceReply(selective=True),
            )
            return
        if action == "kit":
            await send_kit(context.bot, query.message.chat_id, d)
            return
        if action == "posted":
            d.status = "posted"
            d.posted_at = datetime.now(UTC)
            db.commit()
            await query.edit_message_reply_markup(
                InlineKeyboardMarkup([[InlineKeyboardButton("✅ Posted", callback_data="noop:0")]])
            )
            await context.bot.send_message(
                query.message.chat_id,
                LINK_PROMPT.format(id=draft_id),
                reply_markup=ForceReply(selective=True),
            )
            return
        d.status = "approved" if action == "approve" else "rejected"
        db.commit()
        label = "✅ Approved — kit below" if action == "approve" else "❌ Rejected"
        await query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="noop:0")]])
        )
        if action == "approve":
            await send_kit(context.bot, query.message.chat_id, d)


async def on_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    replied = msg.reply_to_message
    if replied and (link := LINK_RE.match(replied.text or "")):
        with session() as db:
            if d := db.get(Draft, int(link.group(1))):
                d.post_url = msg.text.strip()[:500]
                db.commit()
                await msg.reply_text(f"Saved the link for #{d.id}.")
        return
    match = EDIT_RE.match(replied.text or "") if replied else None
    if not match:
        return
    draft_id = int(match.group(1))
    with session() as db:
        d = db.get(Draft, draft_id)
        if d is None:
            return
        d.body = msg.text
        d.hook = "\n".join(msg.text.strip().splitlines()[:2])
        d.status = "sent"
        d.telegram_message_id = await _send_draft(context.bot, msg.chat_id, d)
        db.commit()


async def on_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    count = await _send_pending(context.bot, str(update.effective_chat.id))
    if not count:
        await update.message.reply_text("No pending drafts.")


def _generator_command(what: str, run):
    """A /command that runs a slow generator in a thread and sends the result here.
    `run(sector)` returns draft ids; sector is the command's argument, if any."""

    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        sector = " ".join(context.args).strip() or None
        await update.message.reply_text(
            f"Working on {what} for {sector or 'a random business type'}. "
            "This takes a few minutes (research, writing, fact-check, graphics)."
        )
        try:
            ids = await asyncio.to_thread(run, sector)
        except Exception as e:
            log.exception("Generating %s failed", what)
            await update.message.reply_text(f"Generating {what} failed: {e}"[:TELEGRAM_LIMIT])
            return
        await _send_pending(context.bot, str(update.effective_chat.id), ids)

    return handler


def _daily(sector: str | None) -> list[int]:
    """/daily: today's random format; a business type argument overrides the random one."""
    from content_agent.generate import generate, load_settings, pick_format

    return generate(pick_format(load_settings()).name, sector)


def _make(name: str):
    def run(sector: str | None) -> list[int]:
        from content_agent.generate import generate

        return generate(name, sector)

    return run


async def on_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()


def run_bot() -> None:
    s = _settings()
    only_roy = filters.Chat(chat_id=int(s.telegram_chat_id))
    app = Application.builder().token(s.telegram_bot_token).build()
    app.add_handler(CallbackQueryHandler(on_noop, pattern=r"^noop:"))
    app.add_handler(
        CallbackQueryHandler(on_button, pattern=r"^(approve|edit|reject|posted|kit):\d+$")
    )
    app.add_handler(CommandHandler("pending", on_pending, filters=only_roy))
    # One command per format (/idea, /team, ...) plus /daily for a random one.
    # block=False: generating takes minutes; keep handling buttons meanwhile.
    for name, fmt in FORMATS.items():
        article = "an" if fmt.label[0].lower() in "aeiou" else "a"
        handler = _generator_command(f"{article} {fmt.label}", _make(name))
        app.add_handler(CommandHandler(name, handler, filters=only_roy, block=False))
    app.add_handler(
        CommandHandler(
            "daily", _generator_command("today's post", _daily), filters=only_roy, block=False
        )
    )
    app.add_handler(CommandHandler("guide", on_guide, filters=only_roy, block=False))
    app.add_handler(MessageHandler(only_roy & filters.REPLY & filters.TEXT, on_reply))
    log.info("Approval bot running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
