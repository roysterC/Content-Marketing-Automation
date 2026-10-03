"""Telegram approval gate: every draft gets Approve / Edit / Reject buttons.

Nothing is published from here in Phase 1 - approving just marks the draft so Roy can
copy it out and post manually. Phase 2 will pick up approved drafts for the scheduler.

Two entry points:
- send_pending(): push any pending drafts to the chat, then exit (safe to run from cron).
- run_bot(): long-running process that handles button presses and edit replies.
"""

import asyncio
import logging
import re
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

log = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
EDIT_PROMPT = "Edit draft #{id}: reply to this message with the full new post text."
EDIT_RE = re.compile(r"^Edit draft #(\d+):")


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
    if d.item and d.item.url.startswith(("idea:", "team:")):
        kind = "AI team chart" if d.item.url.startswith("team:") else "idea"
        lines += ["", f"Source: Claude's own {kind} ({d.item.business_type}), web-checked"]
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


async def _send_draft(bot: Bot, chat_id: str, d: Draft) -> int:
    from content_agent.config import OUTPUT_DIR
    from content_agent.visuals.render import poster_path

    image = poster_path(d.id)
    if not image.exists():  # where ideas were saved before posters/ existed
        image = OUTPUT_DIR / "ideas" / f"draft-{d.id}.png"
    if image.exists():
        # As a document, not a photo: Telegram recompresses photos, and this is the
        # full-quality PNG to upload to LinkedIn/Facebook.
        await bot.send_document(chat_id, image, caption=f"Image for draft #{d.id}")
    if d.carousel_path and Path(d.carousel_path).exists():
        await bot.send_document(
            chat_id, Path(d.carousel_path), caption=f"Carousel for draft #{d.id}"
        )
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
        d.status = "approved" if action == "approve" else "rejected"
        db.commit()

    label = "✅ Approved — ready to post" if action == "approve" else "❌ Rejected"
    await query.edit_message_reply_markup(
        InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data="noop:0")]])
    )


async def on_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.message
    replied = msg.reply_to_message
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


def _generator_command(what: str, load_generator):
    """A /command that runs a slow generator in a thread and sends the result here.
    `load_generator` imports lazily so the bot starts without loading Playwright."""

    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        sector = " ".join(context.args).strip() or None
        await update.message.reply_text(
            f"Working on {what} for {sector or 'a random business type'}. "
            "This takes a few minutes (research, writing, fact-check, graphics)."
        )
        try:
            ids = await asyncio.to_thread(load_generator(), sector)
        except Exception as e:
            log.exception("Generating %s failed", what)
            await update.message.reply_text(f"Generating {what} failed: {e}"[:TELEGRAM_LIMIT])
            return
        await _send_pending(context.bot, str(update.effective_chat.id), ids)

    return handler


def _idea_generator():
    from content_agent.drafting.idea import generate_idea

    return generate_idea


def _team_generator():
    from content_agent.drafting.team import generate_team

    return generate_team


on_idea = _generator_command("an automation idea", _idea_generator)
on_team = _generator_command("an AI team chart", _team_generator)


async def on_noop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.callback_query.answer()


def run_bot() -> None:
    s = _settings()
    only_roy = filters.Chat(chat_id=int(s.telegram_chat_id))
    app = Application.builder().token(s.telegram_bot_token).build()
    app.add_handler(CallbackQueryHandler(on_noop, pattern=r"^noop:"))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(approve|edit|reject):\d+$"))
    app.add_handler(CommandHandler("pending", on_pending, filters=only_roy))
    # block=False: generating takes minutes; keep handling buttons meanwhile.
    app.add_handler(CommandHandler("idea", on_idea, filters=only_roy, block=False))
    app.add_handler(CommandHandler("team", on_team, filters=only_roy, block=False))
    app.add_handler(MessageHandler(only_roy & filters.REPLY & filters.TEXT, on_reply))
    log.info("Approval bot running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
