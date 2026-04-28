import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import threading
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIG =====
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OWNER_ID = int(os.environ.get("OWNER_ID"))
PORT = int(os.environ.get("PORT", 8080))

app = Client("rename_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ===== WEB SERVER (KEEP ALIVE) =====
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running!"

def run_web():
    web_app.run(host="0.0.0.0", port=PORT)

# ===== STORAGE =====
user_thumb = {}
user_filename = {}

os.makedirs("downloads", exist_ok=True)

# ===== START =====
@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply_text(
        "👋 Send file to rename\n\n"
        "Commands:\n"
        "/name filename.mp4\n"
        "/thumb (reply photo)\n"
        "/removethumb"
    )

# ===== SET NAME =====
@app.on_message(filters.command("name"))
async def set_name(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Use: /name filename.mp4")

    user_filename[message.from_user.id] = message.text.split(" ", 1)[1]
    await message.reply("✅ Name saved!")

# ===== SET THUMB =====
@app.on_message(filters.command("thumb") & filters.reply)
async def set_thumb(client, message):
    if not message.reply_to_message.photo:
        return await message.reply("❌ Reply to photo")

    file = await message.reply_to_message.download()
    user_thumb[message.from_user.id] = file

    await message.reply("✅ Thumbnail saved!")

# ===== REMOVE THUMB =====
@app.on_message(filters.command("removethumb"))
async def remove_thumb(client, message):
    user_thumb.pop(message.from_user.id, None)
    await message.reply("🗑 Thumbnail removed!")

# ===== FILE HANDLE =====
@app.on_message(filters.document | filters.video | filters.audio)
async def rename_file(client, message: Message):
    user_id = message.from_user.id

    file_path = await message.download()

    new_name = user_filename.get(user_id)
    if not new_name:
        return await message.reply("❌ First use /name")

    new_path = f"downloads/{new_name}"
    os.rename(file_path, new_path)

    thumb = user_thumb.get(user_id)

    await message.reply("📤 Uploading...")

    await message.reply_document(
        document=new_path,
        thumb=thumb
    )

    try:
        os.remove(new_path)
    except:
        pass

# ===== RUN BOTH =====
if __name__ == "__main__":
    threading.Thread(target=run_web).start()
    app.run()
