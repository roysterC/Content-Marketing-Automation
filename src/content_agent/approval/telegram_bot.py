"""Telegram approval gate and posting kit.

Every draft gets Approve / Edit / Reject buttons. Approving sends a *posting kit*: the
post text, the file to attach and the first comment as separate messages (so each is a
single long-press -> Copy), then a "Posted" button. Roy posts by hand; tapping Posted
records it (and optionally the post's link) for Phase 4 analytics. Nothing is published
from here.

Painted images: each package also gets a paste-ready prompt for the Gemini app (free
there, no API). Roy sends the image Gemini makes back to the bot; it's proofread against
the approved copy and used in the posting kit instead of the HTML infographic.

Entry points:
- send_pending(): push any pending drafts to the chat, then exit (safe to run from cron).
- send_reminders(): nudge about approved drafts not yet marked posted (cron).
- run_bot(): long-running process that handles buttons, replies and commands.
"""

import asyncio
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

from content_agent.config import OUTPUT_DIR, get_settings
from content_agent.db import Draft, session
from content_agent.formats import FORMATS
from content_agent.llm import LLMError
from content_agent.visuals.paint import build_prompt, style_names

log = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
EDIT_PROMPT = "Edit draft #{id}: reply to this message with the full new post text."
EDIT_RE = re.compile(r"^Edit draft #(\d+):")
LINK_PROMPT = "Posted #{id}. Reply to this message with the post's link (optional)."
LINK_RE = re.compile(r"^Posted #(\d+)\.")
PAINT_STEPS = (
    "🎨 Painted image for #{id} (optional, free, about a minute)\n"
    "1. Copy the next message into the Gemini app and send it.\n"
    "2. Save the image Gemini makes. Not quite right? Ask Gemini to fix it.\n"
    "3. Reply to this message with the image, sent as a file to keep full quality.\n"
    "I'll check its text and use it in the posting kit."
)
PAINT_RE = re.compile(r"^🎨 Painted image for #(\d+)")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
RECENT_PROMPTS = 20  # drafts searched when Roy replies to a prompt message itself


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


def _painted(d: Draft) -> Path | None:
    return Path(d.painted_path) if d.painted_path and Path(d.painted_path).exists() else None


def paint_prompt(d: Draft, style: str | None = None) -> str | None:
    """The Gemini prompt for a draft's single-image visual, or None if it has none."""
    return build_prompt(d.visual["kind"], d.visual["data"], style) if d.visual else None


def painted_file(group_id: str, suffix: str) -> Path:
    return OUTPUT_DIR / "painted" / f"{group_id}{suffix}"


async def send_paint_prompt(bot: Bot, chat_id, d: Draft, style: str | None = None) -> None:
    """The steps, then the prompt on its own so long-press -> Copy gets exactly it."""
    prompt = paint_prompt(d, style)
    if not prompt:
        return
    await bot.send_message(chat_id, PAINT_STEPS.format(id=d.id))
    if len(prompt) <= TELEGRAM_LIMIT:
        await bot.send_message(chat_id, prompt)
    else:  # an unusually big visual: too long for one message, so send it as a file
        await bot.send_document(
            chat_id,
            prompt.encode(),
            filename=f"gemini-prompt-{d.id}.txt",
            caption="The prompt is too long for one message: copy it from this file.",
        )


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
            if painted := _painted(d):
                await bot.send_document(
                    chat_id, painted, caption="Or post this painted image instead of the PDF"
                )
        elif image := _painted(d) or image:
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
        if image := _painted(d) or _image(d):
            await bot.send_document(chat_id, image)
    await bot.send_message(
        chat_id, f"Tap Posted once #{d.id} is live.", reply_markup=posted_keyboard(d.id)
    )


async def _send_draft(bot: Bot, chat_id: str, d: Draft, with_prompt: bool = True) -> int:
    if image := _image(d):
        # As a document, not a photo: Telegram recompresses photos, and this is the
        # full-quality PNG to upload to LinkedIn/Facebook.
        await bot.send_document(chat_id, image, caption=f"Image for draft #{d.id}")
    if carousel := _carousel(d):
        await bot.send_document(chat_id, carousel, caption=f"Carousel for draft #{d.id}")
    msg = await bot.send_message(chat_id, format_draft(d), reply_markup=keyboard(d.id))
    # One prompt per LinkedIn/Facebook pair: they share the image.
    if with_prompt and d.platform == "linkedin" and not _painted(d):
        await send_paint_prompt(bot, chat_id, d)
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
        d.telegram_message_id = await _send_draft(context.bot, msg.chat_id, d, with_prompt=False)
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


def _latest_with_visual(db) -> Draft | None:
    return db.scalars(
        select(Draft)
        .where(Draft.platform == "linkedin", Draft.visual.is_not(None))
        .order_by(Draft.id.desc())
        .limit(1)
    ).first()


def paint_target(db, replied_text: str | None) -> Draft | None:
    """Which draft an incoming painted image is for: the one named in the steps message
    it replies to, or whose prompt it replies to, else the latest draft with a visual."""
    if replied_text and (m := PAINT_RE.match(replied_text)):
        return db.get(Draft, int(m.group(1)))
    if replied_text:
        recent = db.scalars(
            select(Draft)
            .where(Draft.platform == "linkedin", Draft.visual.is_not(None))
            .order_by(Draft.id.desc())
            .limit(RECENT_PROMPTS)
        )
        for d in recent:
            if any(paint_prompt(d, s).strip() == replied_text.strip()
                   for s in style_names()):  # fmt: skip
                return d
    return _latest_with_visual(db)


async def on_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Roy sent a painted image: save it for the draft pair, then proofread its text."""
    from content_agent.drafting.imagecheck import check_image, format_check

    msg = update.message
    replied = msg.reply_to_message
    if msg.photo:
        file_id, suffix, compressed = msg.photo[-1].file_id, ".jpg", True
    else:
        suffix = Path((msg.document.file_name or "").lower()).suffix
        if suffix not in IMAGE_SUFFIXES:
            suffix = ".png"
        file_id, compressed = msg.document.file_id, False

    with session() as db:
        d = paint_target(db, (replied.text if replied else None))
        if d is None:
            await msg.reply_text("No draft with a visual to attach this image to.")
            return
        path = painted_file(d.group_id, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        tg_file = await context.bot.get_file(file_id)
        await tg_file.download_to_drive(path)
        pair = list(db.scalars(select(Draft).where(Draft.group_id == d.group_id)))
        for p in pair:
            p.painted_path = str(path)
        db.commit()
        prompt = paint_prompt(d)
        ids = " and ".join(f"#{p.id}" for p in sorted(pair, key=lambda p: p.id))
        notes = [f"🖼️ Saved as the image for {ids}. Checking its text…"]
        if compressed:
            notes.append("It came as a photo, so Telegram compressed it. Send it as a file "
                         "for full quality.")  # fmt: skip
        if any(p.status == "approved" for p in pair):
            notes.append("Already approved: tap 🔁 Resend kit to get a kit with it.")
        await msg.reply_text("\n".join(notes))

    try:
        result = await asyncio.to_thread(check_image, path, prompt)
    except (LLMError, OSError) as e:
        log.exception("Image check failed")
        await msg.reply_text(f"Couldn't check the text ({e}). Have a close look yourself."[:500])
        return
    await msg.reply_text(format_check(result))


async def on_paint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/paint [draft id] [style]: (re)send a draft's Gemini prompt, e.g. in another style."""
    draft_id = next((int(a.lstrip("#")) for a in context.args if a.lstrip("#").isdigit()), None)
    style = next((a.lower() for a in context.args if not a.lstrip("#").isdigit()), None)
    if style and style not in style_names():
        await update.message.reply_text(f"Art styles: {', '.join(style_names())}")
        return
    with session() as db:
        d = db.get(Draft, draft_id) if draft_id else _latest_with_visual(db)
        if d is not None and d.platform != "linkedin":
            d = (
                db.scalars(
                    select(Draft).where(Draft.group_id == d.group_id, Draft.platform == "linkedin")
                ).first()
                or d
            )
        if d is None or not d.visual:
            await update.message.reply_text("No draft with a visual found.")
            return
        await send_paint_prompt(context.bot, update.effective_chat.id, d, style)


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
    app.add_handler(CommandHandler("paint", on_paint, filters=only_roy))
    app.add_handler(
        MessageHandler(only_roy & (filters.PHOTO | filters.Document.IMAGE), on_image, block=False)
    )
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
    app.add_handler(MessageHandler(only_roy & filters.REPLY & filters.TEXT, on_reply))
    log.info("Approval bot running")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
