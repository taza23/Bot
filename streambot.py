# streambot.py

import json
import time
import asyncio
import subprocess
from pathlib import Path

import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8959010683:AAGC-uu1YG7QnNQbtEBeGmHdkrPOQ6gBo9E"

TOKENS_FILE = Path("tokens.json")

STREAM_DURATION = (3 * 60 * 60) + (50 * 60)
MAX_STREAMS_PER_TOKEN = 2

user_tokens = {}


class StreamManager:
    def __init__(self):
        self.streams = {}

    def add(self, chat_id, name, data):
        if chat_id not in self.streams:
            self.streams[chat_id] = {}

        self.streams[chat_id][name] = data

    def get(self, chat_id, name):
        return self.streams.get(chat_id, {}).get(name)

    def remove(self, chat_id, name):
        if chat_id in self.streams:
            self.streams[chat_id].pop(name, None)

            if not self.streams[chat_id]:
                self.streams.pop(chat_id, None)

    def count_by_token(self, token_key):
        count = 0

        for user_map in self.streams.values():
            for stream in user_map.values():
                if stream["token_key"] == token_key:
                    count += 1

        return count

    def all(self, chat_id):
        return self.streams.get(chat_id, {})


stream_manager = StreamManager()


def load_tokens():
    try:
        if TOKENS_FILE.exists():
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass

    return {}


def save_tokens(tokens):
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(tokens, f, indent=2, ensure_ascii=False)


def check_ffmpeg():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )

        return True

    except Exception:
        return False


def optimize_dash_url(url):
    if not url:
        return url

    return url.replace("scontent", "video")


def create_stream(token, page_id, name):
    try:
        create_url = f"https://graph.facebook.com/v18.0/{page_id}/live_videos"

        response = requests.post(
            create_url,
            data={
                "access_token": token,
                "status": "UNPUBLISHED",
                "title": name,
                "description": f"بث {name}"
            },
            timeout=30
        )

        data = response.json()

        if "id" not in data:
            return None

        live_id = data["id"]

        info = requests.get(
            f"https://graph.facebook.com/v18.0/{live_id}",
            params={
                "access_token": token,
                "fields": "stream_url,dash_preview_url"
            },
            timeout=30
        )

        info_data = info.json()

        return {
            "live_id": live_id,
            "stream_url": info_data.get("stream_url"),
            "dash_url": optimize_dash_url(
                info_data.get("dash_preview_url")
            )
        }

    except Exception:
        return None


def delete_stream(live_id, token):
    try:
        requests.delete(
            f"https://graph.facebook.com/v18.0/{live_id}",
            params={
                "access_token": token
            },
            timeout=15
        )
    except Exception:
        pass


def start_ffmpeg(stream_url, source):
    args = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",

        "-stream_loop", "-1",
        "-re",

        "-fflags", "+genpts",
        "-thread_queue_size", "4096",

        "-i", source,

        "-map", "0:v:0",
        "-map", "0:a:0?",

        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",

        "-r", "30",
        "-g", "60",

        "-b:v", "2000k",
        "-maxrate", "2000k",
        "-bufsize", "4000k",

        "-c:a", "aac",
        "-b:a", "96k",
        "-ar", "44100",

        "-f", "flv",
        stream_url
    ]

    return subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE
    )


async def stop_stream(chat_id, name):
    stream = stream_manager.get(chat_id, name)

    if not stream:
        return

    try:
        process = stream["proc"]

        if process:
            process.terminate()

            try:
                process.wait(timeout=5)
            except Exception:
                process.kill()

    except Exception:
        pass

    try:
        delete_stream(stream["live_id"], stream["token"])
    except Exception:
        pass

    stream_manager.remove(chat_id, name)


async def auto_stop(chat_id, name):
    await asyncio.sleep(STREAM_DURATION)
    await stop_stream(chat_id, name)


async def start_stream(chat_id, name, url, token_key):
    tokens = load_tokens()

    token_info = tokens.get(str(token_key))

    if not token_info:
        return {
            "success": False,
            "message": "❌ التوكن غير موجود"
        }

    if stream_manager.count_by_token(token_key) >= MAX_STREAMS_PER_TOKEN:
        return {
            "success": False,
            "message": "❌ التوكن وصل الحد"
        }

    stream = create_stream(
        token_info["token"],
        token_info["page_id"],
        name
    )

    if not stream:
        return {
            "success": False,
            "message": "❌ فشل إنشاء البث"
        }

    process = start_ffmpeg(
        stream["stream_url"],
        url
    )

    stream_manager.add(
        chat_id,
        name,
        {
            "proc": process,
            "token": token_info["token"],
            "token_key": token_key,
            "live_id": stream["live_id"],
            "started_at": time.time()
        }
    )

    asyncio.create_task(
        auto_stop(chat_id, name)
    )

    return {
        "success": True,
        "message": (
            f"✅ {name}\n\n"
            f"🎥 RTMP:\n{stream['stream_url']}\n\n"
            f"📺 MPD:\n{stream['dash_url']}"
        )
    }


async def addtoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) < 3:
        await update.message.reply_text(
            "/addtoken PAGE_ID TOKEN NAME"
        )
        return

    page_id = args[0]
    token = args[1]
    name = " ".join(args[2:])

    tokens = load_tokens()

    num = 1

    while str(num) in tokens:
        num += 1

    tokens[str(num)] = {
        "page_id": page_id,
        "token": token,
        "name": name
    }

    save_tokens(tokens)

    await update.message.reply_text(
        f"✅ تم إضافة {name}"
    )


async def tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_tokens()

    if not data:
        await update.message.reply_text(
            "❌ مفيش توكنات"
        )
        return

    msg = "🔐 التوكنات:\n\n"

    for k, v in data.items():
        msg += (
            f"{k}. {v['name']}\n"
            f"📄 {v['page_id']}\n\n"
        )

    await update.message.reply_text(msg)


async def selecttoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if not args:
        await update.message.reply_text(
            "/selecttoken رقم"
        )
        return

    token_id = args[0]

    tokens = load_tokens()

    if token_id not in tokens:
        await update.message.reply_text(
            "❌ رقم غلط"
        )
        return

    user_tokens[
        str(update.effective_chat.id)
    ] = token_id

    await update.message.reply_text(
        f"✅ تم اختيار {tokens[token_id]['name']}"
    )


async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if len(args) < 2:
        await update.message.reply_text(
            "/stream name url"
        )
        return

    chat_id = str(update.effective_chat.id)

    token_key = user_tokens.get(chat_id)

    if not token_key:
        await update.message.reply_text(
            "❌ اختار توكن أولا"
        )
        return

    name = args[0]
    url = " ".join(args[1:])

    result = await start_stream(
        chat_id,
        name,
        url,
        token_key
    )

    await update.message.reply_text(
        result["message"]
    )


async def stopstream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if not args:
        await update.message.reply_text(
            "/stopstream name"
        )
        return

    chat_id = str(update.effective_chat.id)

    name = args[0]

    await stop_stream(chat_id, name)

    await update.message.reply_text(
        f"🛑 تم إيقاف {name}"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    streams = stream_manager.all(chat_id)

    if not streams:
        await update.message.reply_text(
            "📡 لا يوجد بث"
        )
        return

    msg = "📡 البثوث:\n\n"

    for name, data in streams.items():
        duration = int(
            time.time() - data["started_at"]
        )

        mins = duration // 60
        hours = mins // 60

        msg += (
            f"🎬 {name}\n"
            f"⏱️ {hours}h {mins % 60}m\n\n"
        )

    await update.message.reply_text(msg)


async def stopall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)

    streams = list(
        stream_manager.all(chat_id).keys()
    )

    for name in streams:
        await stop_stream(chat_id, name)

    await update.message.reply_text(
        f"🛑 تم إيقاف {len(streams)} بث"
    )


def main():
    if not check_ffmpeg():
        print("FFMPEG NOT INSTALLED")
        return

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    app.add_handler(CommandHandler("addtoken", addtoken))
    app.add_handler(CommandHandler("tokens", tokens))
    app.add_handler(CommandHandler("selecttoken", selecttoken))
    app.add_handler(CommandHandler("stream", stream))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("stopstream", stopstream))
    app.add_handler(CommandHandler("stopall", stopall))

    print("BOT STARTED")

    app.run_polling()


if __name__ == "__main__":
    main()
