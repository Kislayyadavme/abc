#!/usr/bin/env python3
"""
YouTube Age Verification Bypass - Telegram Bot
Converts YouTube watch URLs to embed URLs to bypass age verification.

Requirements:
    pip install python-telegram-bot

Usage:
    1. Get a bot token from @BotFather on Telegram
    2. Set your token in the BOT_TOKEN variable below
    3. Run: python youtube_age_bypass_bot.py
"""

import re
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ── Configuration ────────────────────────────────────────────────────────────
BOT_TOKEN = "8414761321:AAG0HXXtXiiL0hAfgRJ1LNzIB9w0D08QClA"  # Replace with your token from @BotFather

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_video_id(url: str) -> str | None:
    """
    Extract the YouTube video ID from various URL formats:
      - https://www.youtube.com/watch?v=VIDEO_ID
      - https://youtu.be/VIDEO_ID
      - https://www.youtube.com/watch?v=VIDEO_ID&list=...
    """
    patterns = [
        r"(?:youtube\.com/watch\?(?:.*&)?v=)([A-Za-z0-9_\-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_\-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def build_embed_url(video_id: str) -> str:
    return f"https://www.youtube.com/embed/{video_id}?autoplay=1&showinfo=0"


def build_invidious_url(video_id: str) -> str:
    """Alternative: use Invidious (privacy-friendly front-end) as fallback."""
    return f"https://invidious.io/watch?v={video_id}"


# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *YouTube Age-Gate Bypass Bot*\n\n"
        "Send me any YouTube link and I'll give you an embed URL "
        "that skips the age verification — no login required.\n\n"
        "Just paste a link like:\n"
        "`https://www.youtube.com/watch?v=dQw4w9WgXcQ`",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ *How to use*\n\n"
        "1. Paste a YouTube URL into this chat.\n"
        "2. I'll extract the video ID and return an embed link.\n"
        "3. Open the embed link in your browser — no age prompt!\n\n"
        "*Supported formats:*\n"
        "• `https://www.youtube.com/watch?v=VIDEO_ID`\n"
        "• `https://youtu.be/VIDEO_ID`\n"
        "• URLs with extra query params (playlists, timestamps, etc.)",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    # Check if the message contains a YouTube URL
    if "youtube.com" not in text and "youtu.be" not in text:
        await update.message.reply_text(
            "⚠️ That doesn't look like a YouTube URL.\n"
            "Please send a link like:\n"
            "`https://www.youtube.com/watch?v=VIDEO_ID`",
            parse_mode="Markdown"
        )
        return

    video_id = extract_video_id(text)
    if not video_id:
        await update.message.reply_text(
            "❌ Couldn't extract a video ID from that URL.\n"
            "Make sure it's a valid YouTube watch link."
        )
        return

    embed_url = build_embed_url(video_id)
    invidious_url = build_invidious_url(video_id)

    reply = (
        f"✅ *Age-gate bypass ready!*\n\n"
        f"🎬 *Video ID:* `{video_id}`\n\n"
        f"▶️ *Embed URL* (open in browser):\n{embed_url}\n\n"
        f"🔒 *Privacy alternative (Invidious):*\n{invidious_url}"
    )
    await update.message.reply_text(reply, parse_mode="Markdown")
    logger.info("Processed video ID: %s for user: %s", video_id, update.effective_user.id)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("Please set your BOT_TOKEN before running the bot.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
