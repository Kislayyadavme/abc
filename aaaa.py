#!/usr/bin/env python3
"""
YouTube Age Verification Bypass + Downloader - Telegram Bot
Bypasses age verification and allows downloading video or audio.

Requirements:
    pip install python-telegram-bot yt-dlp
    # Also install ffmpeg for audio conversion:
    # Ubuntu/Debian: sudo apt install ffmpeg
    # Windows: https://ffmpeg.org/download.html
    # Mac: brew install ffmpeg

Usage:
    1. Get a bot token from @BotFather on Telegram
    2. Set your token in the BOT_TOKEN variable below
    3. Run: python youtube_age_bypass_bot.py
"""

import re
import os
import logging
import asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
import yt_dlp

# ── Configuration ─────────────────────────────────────────────────────────────
BOT_TOKEN = "8414761321:AAG0HXXtXiiL0hAfgRJ1LNzIB9w0D08QClA"   # Replace with your token from @BotFather
DOWNLOAD_DIR = Path("downloads")    # Temp folder for downloaded files
MAX_FILE_SIZE_MB = 50               # Telegram bot limit is 50MB

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)
DOWNLOAD_DIR.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_video_id(url: str) -> str | None:
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


def get_video_info(url: str) -> dict | None:
    """Fetch video metadata without downloading."""
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", "Unknown"),
                "view_count": info.get("view_count", 0),
            }
    except Exception as e:
        logger.error("Error fetching video info: %s", e)
        return None


def download_video(url: str, video_id: str) -> Path | None:
    """Download best quality video (max 720p to keep file size manageable)."""
    output_path = DOWNLOAD_DIR / f"{video_id}_video.mp4"
    ydl_opts = {
        "format": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]",
        "outtmpl": str(DOWNLOAD_DIR / f"{video_id}_video"),
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        if output_path.exists():
            return output_path
        for f in DOWNLOAD_DIR.glob(f"{video_id}_video*"):
            return f
    except Exception as e:
        logger.error("Video download error: %s", e)
    return None


def download_audio(url: str, video_id: str) -> Path | None:
    """Download and convert to MP3 audio only."""
    output_template = str(DOWNLOAD_DIR / f"{video_id}_audio")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": True,
        "no_warnings": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        output_path = Path(output_template + ".mp3")
        if output_path.exists():
            return output_path
        for f in DOWNLOAD_DIR.glob(f"{video_id}_audio*"):
            return f
    except Exception as e:
        logger.error("Audio download error: %s", e)
    return None


def format_duration(seconds: int) -> str:
    mins, secs = divmod(seconds, 60)
    hours, mins = divmod(mins, 60)
    if hours:
        return f"{hours}:{mins:02d}:{secs:02d}"
    return f"{mins}:{secs:02d}"


def cleanup_file(path: Path) -> None:
    try:
        if path and path.exists():
            path.unlink()
    except Exception:
        pass


# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *YouTube Age-Gate Bypass & Downloader Bot*\n\n"
        "Send me any YouTube link and I will:\n"
        "• Bypass age verification\n"
        "• Let you download the *video* (MP4) or *audio* (MP3)\n\n"
        "Just paste a YouTube URL to get started!",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ℹ️ *How to use*\n\n"
        "1. Paste a YouTube URL\n"
        "2. Choose *Download Video* or *Download Audio*\n"
        "3. Wait for the file to be sent to you\n\n"
        "⚠️ *Note:* Files larger than 50MB cannot be sent via Telegram.\n"
        "Video is capped at 720p to keep sizes manageable.\n\n"
        "*Requirements:* ffmpeg must be installed for audio downloads.",
        parse_mode="Markdown"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()

    if "youtube.com" not in text and "youtu.be" not in text:
        await update.message.reply_text(
            "⚠️ Please send a valid YouTube URL.\n"
            "Example: `https://www.youtube.com/watch?v=VIDEO_ID`",
            parse_mode="Markdown"
        )
        return

    video_id = extract_video_id(text)
    if not video_id:
        await update.message.reply_text("❌ Couldn't extract a video ID from that URL.")
        return

    # Store URL in user context for the download callback
    context.user_data["url"] = text
    context.user_data["video_id"] = video_id

    status_msg = await update.message.reply_text("🔍 Fetching video info...")

    loop = asyncio.get_event_loop()
    info = await loop.run_in_executor(None, get_video_info, text)

    embed_url = build_embed_url(video_id)

    if info:
        duration_str = format_duration(info["duration"])
        views = f"{info['view_count']:,}" if info["view_count"] else "N/A"
        caption = (
            f"🎬 *{info['title']}*\n"
            f"👤 {info['uploader']}\n"
            f"⏱ {duration_str}  •  👁 {views} views\n\n"
            f"▶️ [Watch via embed (age bypass)]({embed_url})\n\n"
            f"What would you like to do?"
        )
    else:
        caption = (
            f"✅ Video ID: `{video_id}`\n"
            f"▶️ [Watch via embed (age bypass)]({embed_url})\n\n"
            "What would you like to do?"
        )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎥 Download Video (MP4)", callback_data=f"dl_video_{video_id}"),
            InlineKeyboardButton("🎵 Download Audio (MP3)", callback_data=f"dl_audio_{video_id}"),
        ]
    ])

    await status_msg.edit_text(
        caption,
        parse_mode="Markdown",
        reply_markup=keyboard,
        disable_web_page_preview=False
    )


async def handle_download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data  # "dl_video_VIDEO_ID" or "dl_audio_VIDEO_ID"
    parts = data.split("_", 2)
    if len(parts) != 3:
        await query.edit_message_text("❌ Invalid action.")
        return

    _, mode, video_id = parts
    url = context.user_data.get("url") or f"https://www.youtube.com/watch?v={video_id}"

    await query.edit_message_text(
        f"⏳ {'Downloading video (720p)...' if mode == 'video' else 'Extracting audio (MP3)...'}\n"
        "Please wait, this may take a moment."
    )

    loop = asyncio.get_event_loop()

    if mode == "video":
        file_path = await loop.run_in_executor(None, download_video, url, video_id)
    else:
        file_path = await loop.run_in_executor(None, download_audio, url, video_id)

    if not file_path or not file_path.exists():
        await query.edit_message_text(
            "❌ Download failed. The video may be unavailable or restricted.\n"
            "Try using the embed URL to watch instead."
        )
        return

    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        cleanup_file(file_path)
        await query.edit_message_text(
            f"⚠️ File is too large ({file_size_mb:.1f} MB) — Telegram's limit is {MAX_FILE_SIZE_MB} MB.\n"
            "Try a shorter video or use the embed URL."
        )
        return

    await query.edit_message_text(f"📤 Uploading {'video' if mode == 'video' else 'audio'} ({file_size_mb:.1f} MB)...")

    try:
        with open(file_path, "rb") as f:
            if mode == "video":
                await query.message.reply_video(
                    video=f,
                    caption="🎥 Here's your video!",
                    supports_streaming=True
                )
            else:
                await query.message.reply_audio(
                    audio=f,
                    caption="🎵 Here's your audio!"
                )
        await query.edit_message_text("✅ Done! Enjoy your file.")
    except Exception as e:
        logger.error("Upload error: %s", e)
        await query.edit_message_text("❌ Failed to upload the file. Please try again.")
    finally:
        cleanup_file(file_path)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise ValueError("Please set your BOT_TOKEN before running the bot.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_download_callback, pattern=r"^dl_(video|audio)_"))

    logger.info("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
