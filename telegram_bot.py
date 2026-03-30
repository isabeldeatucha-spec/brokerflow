"""
Brand Scout — Telegram bot interface.

Primary broker-facing interface. Two modes:
  1. On-demand evaluation  — send any brand name (with optional URL)
  2. Morning digest        — daily at 7 AM, discovers + scores new arrivals

Commands:
  /start          — welcome + instructions
  /digest         — run morning digest immediately
  /outreach       — show last email draft with Approve/Edit buttons
  /history        — all previously evaluated brands sorted by score
  /help           — command reference

Free-text messages:
  "Chomps"                          → evaluate brand name only
  "Chomps https://chomps.com"       → evaluate with URL (faster, more accurate)

Run:
  python3 -m sedge.telegram_bot
"""
import logging
import os
import re
import types as _types
import uuid
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
DIGEST_HOUR = int(os.environ.get("DIGEST_HOUR", "7"))
DIGEST_MINUTE = int(os.environ.get("DIGEST_MINUTE", "0"))

# ── Module-level app reference (set in _on_startup) ──────────────────────────

_app: Optional[Application] = None
_scheduler = AsyncIOScheduler(timezone="America/New_York")

# ── Lazy graph loader ─────────────────────────────────────────────────────────

_graph = None
_get_config_fn = None


def _load_graph():
    global _graph, _get_config_fn
    if _graph is None:
        from sedge.agents.brand_scout.graph import graph
        from sedge.memory import get_config
        _graph = graph
        _get_config_fn = get_config
    return _graph, _get_config_fn


# ── Per-chat session state ────────────────────────────────────────────────────
# last_result: most recent completed evaluation (for /outreach, /history display)
# pending:     evaluation paused at human_approval interrupt
_last_result: dict[int, dict] = {}
_pending: dict[int, dict] = {}


# ── Formatting ────────────────────────────────────────────────────────────────

_RANK_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


def _verdict_label(total: int) -> tuple[str, str]:
    """Return (emoji, label) for a total score."""
    if total >= 70:
        return "🟢", "Broker Ready"
    if total >= 45:
        return "🟡", "Promising — Watch"
    return "🔴", "Too Early"


def _score_emoji(score: int, max_pts: int) -> str:
    pct = score / max_pts
    if pct >= 0.80:
        return "✅"
    if pct >= 0.50:
        return "⚠️"
    return "❌"


def format_brand_report(result: dict) -> str:
    """
    Format a Brand Scout evaluation result as a Telegram Markdown message.
    Uses legacy Markdown (ParseMode.MARKDOWN) — no special char escaping needed.
    """
    brand_name = result.get("brand_name", "Unknown")
    category = result.get("category", "unknown").replace("_", " ").title()
    score_obj = result.get("score", {})
    total = score_obj.get("total", 0)
    verdict_emoji, verdict_label = _verdict_label(total)

    detail = result.get("signals_found", {}).get("score_detail", {})
    broker_brief = detail.get("broker_brief", "No brief available.")
    key_gaps = detail.get("key_gaps", [])

    def pts(key: str) -> int:
        entry = detail.get(key, {})
        return entry.get("score", score_obj.get(key, 0)) if isinstance(entry, dict) else score_obj.get(key, 0)

    velocity      = pts("velocity_proof")
    distribution  = pts("distribution_density")
    margin        = pts("margin_viability")
    story         = pts("brand_story_clarity")
    promo         = pts("promotional_independence")

    key_gaps_formatted = "\n".join(f"• {g}" for g in key_gaps) if key_gaps else "None identified."

    reflection_notes = result.get("reflection_notes", [])
    if reflection_notes:
        reflection_lines = []
        for i, note in enumerate(reflection_notes, 1):
            short = note[:220] + "…" if len(note) > 220 else note
            reflection_lines.append(f"*Round {i}:* {short}")
        reflection_notes_formatted = "\n\n".join(reflection_lines)
    else:
        reflection_notes_formatted = "No reflection loops required."

    timestamp = datetime.now().strftime("%-d %b %Y, %-I:%M %p")

    sep = "━━━━━━━━━━━━━━━━━━━━"

    return (
        f"🔍 *Brand Scout Report — {brand_name}*\n"
        f"📦 Category: {category}\n"
        f"⭐ Score: {total}/100 — {verdict_emoji} {verdict_label}\n"
        f"\n{sep}\n"
        f"📊 *Scorecard*\n"
        f"{sep}\n"
        f"{_score_emoji(velocity, 25)} Velocity Proof         {velocity}/25\n"
        f"{_score_emoji(distribution, 20)} Distribution Density   {distribution}/20\n"
        f"{_score_emoji(margin, 20)} Margin Viability        {margin}/20\n"
        f"{_score_emoji(story, 20)} Brand Story Clarity     {story}/20\n"
        f"{_score_emoji(promo, 15)} Promo Independence      {promo}/15\n"
        f"\n{sep}\n"
        f"📝 *Broker Brief*\n"
        f"{sep}\n"
        f"{broker_brief}\n"
        f"\n{sep}\n"
        f"🚨 *Key Gaps*\n"
        f"{sep}\n"
        f"{key_gaps_formatted}\n"
        f"\n{sep}\n"
        f"🧠 *Agent Reasoning*\n"
        f"{sep}\n"
        f"{reflection_notes_formatted}\n"
        f"\n_Evaluated {timestamp}_"
    )


def _format_digest_entry(rank: int, result: dict) -> str:
    """One compact entry for the morning digest."""
    rank_emoji = _RANK_EMOJIS[rank - 1] if rank <= len(_RANK_EMOJIS) else f"{rank}."
    brand_name = result.get("brand_name", "Unknown")
    total = result.get("score", {}).get("total", 0)
    verdict_emoji, _ = _verdict_label(total)
    category = result.get("category", "unknown").replace("_", " ").title()

    detail = result.get("signals_found", {}).get("score_detail", {})
    broker_brief = detail.get("broker_brief", "")
    one_line = broker_brief.split(".")[0] + "." if broker_brief else "No brief."

    # Best single signal: first non-empty signals_used from highest-scoring criterion
    key_signal = ""
    score_obj = result.get("score", {})
    for key in ["velocity_proof", "distribution_density", "brand_story_clarity"]:
        entry = detail.get(key, {})
        if isinstance(entry, dict):
            signals = entry.get("signals_used", [])
            if signals:
                key_signal = str(signals[0]).replace("_", " ")
                break

    return (
        f"{rank_emoji} *{brand_name}* — {total}/100 {verdict_emoji}\n"
        f"{one_line}\n"
        f"_{category}{' • ' + key_signal if key_signal else ''}_"
    )


def _outreach_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Approve & Send", callback_data="outreach:approve"),
        InlineKeyboardButton("✏️ Edit",           callback_data="outreach:edit"),
    ]])


# ── Core evaluation runner ────────────────────────────────────────────────────

async def _run_evaluation(
    brand_name: str,
    website_url: str,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    progress_message_id: Optional[int] = None,
    skip_outreach: bool = False,
) -> Optional[dict]:
    """
    Stream the Brand Scout graph, edit a progress message in-place, and return
    the final state. Pauses at human_approval; caller decides whether to resume.
    """
    graph, get_config = _load_graph()
    thread_id = str(uuid.uuid4())
    cfg = get_config(thread_id)

    initial_state = {
        "brand_name": brand_name,
        "website_url": website_url,
        "sources_checked": [],
        "signals_found": {},
        "follow_up_queries": [],
        "reflection_count": 0,
        "reflection_notes": [],
        "category": "",
        "benchmark": {},
        "score": {},
        "verdict": "",
        "founder_name": "",
        "founder_email": "",
        "email_draft": "",
        "approved": None,
        "rejection_reason": None,
    }

    _NODE_LABELS = {
        "discover_brands":      "🔍 Discovering brands…",
        "research_brand":       "📊 Researching signals…",
        "reflect_and_decide":   "🤔 Checking for gaps…",
        "detect_category_node": "🏷️ Detecting category…",
        "score_brand":          "🎯 Scoring brand…",
        "store_memory":         "💾 Saving to memory…",
        "draft_outreach":       "✍️ Drafting email…",
    }

    last_label = ""
    try:
        async for chunk in graph.astream(initial_state, config=cfg, stream_mode="updates"):
            for node_name in chunk:
                if skip_outreach and node_name == "draft_outreach":
                    continue
                label = _NODE_LABELS.get(node_name, f"⚙️ {node_name}…")
                if label == last_label:
                    continue
                last_label = label
                if progress_message_id:
                    try:
                        await context.bot.edit_message_text(
                            chat_id=chat_id,
                            message_id=progress_message_id,
                            text=label,
                        )
                    except Exception:
                        pass

            state_snap = graph.get_state(cfg)
            if state_snap.next and "human_approval" in state_snap.next:
                final = state_snap.values
                _pending[chat_id] = {"state": final, "thread_id": thread_id, "config": cfg}
                _last_result[chat_id] = final
                return final

    except Exception as exc:
        logger.exception("Graph error for %s", brand_name)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"⚠️ Evaluation failed for *{brand_name}*: {exc}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return None

    final = graph.get_state(cfg).values
    _last_result[chat_id] = final
    return final


# ── Command handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "👋 Welcome to *Brand Scout* by Sedge\\.\n\n"
        "I'm your AI broker assistant\\. I evaluate CPG brands and tell you "
        "whether they're worth your time\\.\n\n"
        "*How to use me:*\n"
        "\\- Send any brand name → I'll research and score it\n"
        "\\- Send a brand name \\+ URL → faster and more accurate\n"
        "\\- /digest → get today's new brand discoveries\n"
        "\\- /history → see brands you've evaluated before\n\n"
        "I run every morning at 7am with new brand discoveries from Whole Foods, "
        "Sprouts, and Target new arrivals\\."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "*Brand Scout* — commands\n\n"
        "Send any brand name (or brand \\+ URL) to evaluate it\n\n"
        "/digest — run morning digest now\n"
        "/outreach — show last email draft\n"
        "/history — all evaluated brands\n"
        "/help — this message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Free-text handler. Parses:
      "Chomps"                         → brand name only
      "Chomps https://chomps.com"      → brand + URL
    """
    print(f"Chat ID: {update.effective_chat.id}")
    text = (update.message.text or "").strip()
    if not text:
        return

    # Extract trailing URL if present
    url_match = re.search(r'(https?://\S+)', text)
    if url_match:
        website_url = url_match.group(1)
        brand_name = text[:url_match.start()].strip()
    else:
        website_url = ""
        brand_name = text

    if not brand_name:
        await update.message.reply_text("Please send a brand name, e.g. *Chomps* or *Chomps https://chomps.com*", parse_mode=ParseMode.MARKDOWN)
        return

    chat_id = update.effective_chat.id
    msg = await update.message.reply_text(
        f"🔍 Researching *{brand_name}*… This takes about 30 seconds.",
        parse_mode=ParseMode.MARKDOWN,
    )

    final = await _run_evaluation(brand_name, website_url, chat_id, context, progress_message_id=msg.message_id)

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
    except Exception:
        pass

    if final is None:
        return

    report = format_brand_report(final)

    # Telegram message limit is 4096 chars — split if needed
    if len(report) > 4000:
        await update.message.reply_text(report[:4000], parse_mode=ParseMode.MARKDOWN)
        await update.message.reply_text(report[4000:], parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(report, parse_mode=ParseMode.MARKDOWN)

    # If above threshold, prompt for outreach
    total = final.get("score", {}).get("total", 0)
    if total >= 70:
        await update.message.reply_text(
            "💌 *Outreach draft ready.* Reply /outreach to see the email draft.",
            parse_mode=ParseMode.MARKDOWN,
        )


async def cmd_outreach(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/outreach — show draft email from last evaluation with Approve/Edit buttons."""
    chat_id = update.effective_chat.id
    result = _last_result.get(chat_id) or _pending.get(chat_id, {}).get("state")

    if not result:
        await update.message.reply_text(
            "No recent evaluation found. Send a brand name to evaluate first.",
        )
        return

    email_draft = result.get("email_draft", "")
    if not email_draft:
        await update.message.reply_text(
            "No email draft available — brand may have scored below threshold.",
        )
        return

    founder = result.get("founder_name", "")
    founder_email = result.get("founder_email", "")
    brand_name = result.get("brand_name", "")
    total = result.get("score", {}).get("total", 0)
    verdict_emoji, _ = _verdict_label(total)

    header = f"📧 *Draft Email — {brand_name}* {verdict_emoji}\nTo: {founder} <{founder_email}>\n\n"
    draft_text = header + f"```\n{email_draft[:1400]}{'…' if len(email_draft) > 1400 else ''}\n```"

    await update.message.reply_text(
        draft_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_outreach_keyboard(),
    )


async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/digest — run the morning digest immediately."""
    await update.message.reply_text("☀️ Running Brand Scout digest…")
    await _run_morning_digest(context, override_chat_id=update.effective_chat.id)


async def cmd_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/history — list all previously evaluated brands sorted by score."""
    from sedge.memory import retrieve_all_evaluations

    evaluations = retrieve_all_evaluations()

    def _v2(s: str) -> str:
        """Escape a plain string for MARKDOWN_V2."""
        return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', s)

    if not evaluations:
        await update.message.reply_text(
            "📚 *Brands You've Evaluated*\n\nNo brands evaluated yet\\.\n"
            "Send a brand name to start\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    lines = ["📚 *Brands You've Evaluated*", ""]
    for ev in evaluations:
        total = ev["score"]
        verdict_emoji, _ = _verdict_label(total)
        brand = _v2(ev["brand_name"])
        # Parse date from ISO timestamp
        date_str = ""
        raw_date = ev.get("evaluated_at", "")
        if raw_date:
            try:
                dt = datetime.fromisoformat(raw_date)
                date_str = _v2(dt.strftime("%-d %b"))
            except ValueError:
                date_str = _v2(raw_date[:10])
        date_part = f" — {date_str}" if date_str else ""
        lines.append(f"{verdict_emoji} *{brand}* — {_v2(str(total))}/100{date_part}")

    lines.append("\nSend any brand name for a full report\\.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN_V2)


# ── Inline keyboard callbacks ─────────────────────────────────────────────────

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    chat_id = update.effective_chat.id

    if data == "outreach:approve":
        await _do_approve(chat_id, context, query)
    elif data == "outreach:edit":
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                "✏️ *Editing via bot coming soon.*\n\n"
                "For now: copy the draft above, edit in your email client, "
                "then use /outreach → Approve to send the original, "
                "or just send it manually."
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    elif data.startswith("approve:"):
        await _do_approve(chat_id, context, query)
    elif data.startswith("reject:"):
        await _do_reject(chat_id, "Rejected via button", context, query)


async def _do_approve(
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    query,
) -> None:
    from langgraph.types import Command as LGCommand

    pending = _pending.pop(chat_id, None)
    if not pending:
        await query.edit_message_text("No pending evaluation to approve.")
        return
    graph, _ = _load_graph()
    try:
        graph.invoke(
            LGCommand(resume={"approved": True, "rejection_reason": ""}),
            config=pending["config"],
        )
        brand = pending["state"].get("brand_name", "")
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ Email approved and sent for *{brand}*.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Send failed: {exc}")


async def _do_reject(
    chat_id: int,
    reason: str,
    context: ContextTypes.DEFAULT_TYPE,
    query,
) -> None:
    from langgraph.types import Command as LGCommand

    pending = _pending.pop(chat_id, None)
    if not pending:
        await query.edit_message_text("No pending evaluation.")
        return
    graph, _ = _load_graph()
    try:
        graph.invoke(
            LGCommand(resume={"approved": False, "rejection_reason": reason}),
            config=pending["config"],
        )
        brand = pending["state"].get("brand_name", "")
        await query.edit_message_reply_markup(reply_markup=None)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Rejected *{brand}*. Reason: {reason}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Rejection failed: {exc}")


# ── Morning digest ────────────────────────────────────────────────────────────

async def _run_morning_digest(
    context: ContextTypes.DEFAULT_TYPE,
    override_chat_id: Optional[int] = None,
) -> None:
    """Discover new brands, evaluate top 3, send ranked digest."""
    MAX_BRANDS = 3
    target_chat = override_chat_id or (int(CHAT_ID) if CHAT_ID else None)
    if not target_chat:
        logger.warning("Digest skipped — TELEGRAM_CHAT_ID not set")
        return

    from sedge.agents.brand_scout.tools import (
        scrape_whole_foods_new_arrivals,
        scrape_sprouts_new_arrivals,
        scrape_target_new_arrivals,
    )

    date_str = datetime.now().strftime("%A, %B %-d")

    # Discover
    all_found: list[dict] = []
    seen: set[str] = set()
    for fn in [scrape_whole_foods_new_arrivals, scrape_sprouts_new_arrivals, scrape_target_new_arrivals]:
        for b in fn():
            name = b.get("brand_name", "")
            if not name or "error" in b:
                continue
            key = name.lower()
            if key not in seen:
                seen.add(key)
                all_found.append(b)

    if not all_found:
        await context.bot.send_message(
            chat_id=target_chat,
            text="☀️ *Brand Scout Daily Digest*\n\n⚠️ No new brands discovered today.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Evaluate top N
    evaluated: list[dict] = []
    for brand_dict in all_found[:MAX_BRANDS]:
        brand_name = brand_dict["brand_name"]
        website_url = brand_dict.get("website_url", "")
        prog = await context.bot.send_message(
            chat_id=target_chat,
            text=f"🔍 Evaluating *{brand_name}*…",
            parse_mode=ParseMode.MARKDOWN,
        )
        result = await _run_evaluation(
            brand_name, website_url, target_chat, context,
            progress_message_id=prog.message_id,
            skip_outreach=True,
        )
        try:
            await context.bot.delete_message(chat_id=target_chat, message_id=prog.message_id)
        except Exception:
            pass
        if result:
            evaluated.append(result)

    evaluated.sort(key=lambda r: r.get("score", {}).get("total", 0), reverse=True)

    if not evaluated:
        await context.bot.send_message(
            chat_id=target_chat,
            text="☀️ *Brand Scout Daily Digest*\n\n⚠️ All evaluations failed.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    entries = "\n\n".join(_format_digest_entry(i + 1, r) for i, r in enumerate(evaluated))

    digest = (
        f"☀️ *Brand Scout Daily Digest*\n"
        f"_{date_str}_\n\n"
        f"Here are today's top picks from new retail arrivals:\n\n"
        f"{entries}\n\n"
        f"Reply with any brand name for a full report\\."
    )

    await context.bot.send_message(
        chat_id=target_chat,
        text=digest,
        parse_mode=ParseMode.MARKDOWN_V2,
    )


# ── APScheduler digest callback ───────────────────────────────────────────────

async def send_morning_digest() -> None:
    """APScheduler callback — proactively sends the digest to CHAT_ID."""
    if not _app or not CHAT_ID:
        logger.warning("send_morning_digest skipped — app or CHAT_ID not set")
        return
    ctx = _types.SimpleNamespace(bot=_app.bot)
    await _run_morning_digest(ctx)


# ── App lifecycle hooks ───────────────────────────────────────────────────────

async def _on_startup(app: Application) -> None:
    global _app
    _app = app
    _scheduler.add_job(
        send_morning_digest,
        "cron",
        hour=DIGEST_HOUR,
        minute=DIGEST_MINUTE,
        id="morning_digest",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Morning digest scheduled for %02d:%02d America/New_York daily",
        DIGEST_HOUR, DIGEST_MINUTE,
    )


async def _on_shutdown(app: Application) -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


# ── Error handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Unhandled exception", exc_info=context.error)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(_on_startup)
        .post_stop(_on_shutdown)
        .build()
    )

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("digest",   cmd_digest))
    app.add_handler(CommandHandler("outreach", cmd_outreach))
    app.add_handler(CommandHandler("history",  cmd_history))
    app.add_handler(CallbackQueryHandler(callback_handler))
    # Free-text messages (not commands)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    if not CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set — morning digest will not send automatically")

    logger.info("Brand Scout bot starting…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def run_bot() -> None:
    """Public entry point called from sedge/main.py --telegram."""
    main()


if __name__ == "__main__":
    main()
