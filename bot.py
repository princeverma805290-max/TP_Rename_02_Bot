from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from flask import Flask
import threading
import os
import time
import json
import cv2  # For frame extraction
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser

# ==========================================
# 1. HUGGING FACE FAKE PORT SETUP (7860)
# ==========================================
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is running perfectly!"

def run_web_server():
    web_app.run(host="0.0.0.0", port=7860)

threading.Thread(target=run_web_server, daemon=True).start()

# ==========================================
# 2. BOT SETUP & VARIABLES
# ==========================================
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

owner_id_str = os.environ.get("OWNER_ID")
OWNER_ID = int(owner_id_str) if owner_id_str else 0

app = Client("thumbnail_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ==========================================
# 3. DATABASE SETUP (JSON FILE)
# ==========================================
DB_FILE = "database.json"

authorized_users = set()
user_thumbnails = {}  
user_captions = {}    
bot_mode = "private" 

def load_database():
    global authorized_users, user_thumbnails, user_captions, bot_mode
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                data = json.load(f)
                authorized_users = set(data.get("authorized_users", []))
                user_thumbnails = {int(k): v for k, v in data.get("user_thumbnails", {}).items()}
                user_captions = {int(k): v for k, v in data.get("user_captions", {}).items()}
                bot_mode = data.get("bot_mode", "private")
        except Exception as e:
            print(f"Error loading database: {e}")

def save_database():
    data = {
        "authorized_users": list(authorized_users),
        "user_thumbnails": user_thumbnails,
        "user_captions": user_captions,
        "bot_mode": bot_mode
    }
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

load_database()

# ==========================================
# 4. HELPER & ACCESS FUNCTIONS
# ==========================================
def is_owner(user_id):
    return user_id == OWNER_ID

def get_duration(file_path):
    metadata = extractMetadata(createParser(file_path))
    if metadata and metadata.has("duration"):
        return metadata.get("duration").seconds
    return 0

def get_width_height(file_path):
    metadata = extractMetadata(createParser(file_path))
    if metadata:
        width = metadata.get("width") if metadata.has("width") else 0
        height = metadata.get("height") if metadata.has("height") else 0
        return width, height
    return 0, 0

async def check_access(client, message):
    user_id = message.from_user.id
    if is_owner(user_id) or user_id in authorized_users:
        return True
    if bot_mode == "public":
        return True
    
    unauth_image = "https://graph.org/file/0d5c28c9cb49a4889ef16-7fdc19f094cc32ba73.jpg"
    user_name = message.from_user.first_name
    await message.reply_photo(
        photo=unauth_image,
        caption=(
            f"Hey 👋 [{user_name}](tg://user?id={user_id})\n\n"
            "You Are Not Authorised To Use me Please Tell My Bos To Authorise You After My master Authorised You\n"
            "You Can use Me Freely"
        )
    )
    return False

close_markup = InlineKeyboardMarkup([[InlineKeyboardButton("Close ❌", callback_data="close_msg")]])

def take_screen_shot(video_file, output_directory, ttl):
    out_put_file_name = f"{output_directory}/{time.time()}.jpg"
    if not os.path.exists(output_directory): os.makedirs(output_directory)
    cap = cv2.VideoCapture(video_file)
    cap.set(cv2.CAP_PROP_POS_MSEC, (ttl * 1000))
    ret, frame = cap.read()
    if ret:
        cv2.imwrite(out_put_file_name, frame)
    cap.release()
    return out_put_file_name if os.path.exists(out_put_file_name) else None

def get_readable_size(bytes_size):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0

async def progress_callback(current, total, msg, text, start_time):
    now = time.time()
    if getattr(msg, "last_update_time", 0) + 3 < now or current == total:
        msg.last_update_time = now
        percentage = current * 100 / total
        completed_blocks = int(percentage / 10)
        progress_bar = "[{0}{1}]".format(
            ''.join(["█" for i in range(completed_blocks)]),
            ''.join(["░" for i in range(10 - completed_blocks)])
        )
        curr_size = get_readable_size(current)
        tot_size = get_readable_size(total)
        progress_text = f"{text}\n\n{progress_bar} **{percentage:.1f}%**\n📦 **Size:** {curr_size} / {tot_size}"
        try:
            await msg.edit_text(progress_text)
        except Exception:
            pass

# ==========================================
# 5. UI TEXT GENERATORS
# ==========================================
START_IMAGE = "https://graph.org/file/4c2f7e3f7705839e10491-f023eaddcfca5b3271.jpg"
CMDS_IMAGE = "https://graph.org/file/546ddb39c87d2560a97d1-910afb26df1467a781.jpg"

def get_start_text(user_name, user_id):
    return (
        f"> Hey 👋 [{user_name}](tg://user?id={user_id})\n> \n"
        f"> I Am A Custom Thumbnails Or Custom caption setter bot.\n> \n"
        f"> Powered by : [TP Bots](https://t.me/TP_02_Bots)"
    )

def get_commands_text():
    return (
        "> **Bot Commands 📋**\n> \n"
        "> **👤 Users & Admin:**\n"
        "> `/setthumbnail` - Save thumbnail (Reply to photo)\n"
        "> `/seesetthumb` - View saved thumbnail\n"
        "> `/getthumbnail` - Get thumbnail from a video\n"
        "> `/removethumb` - Remove thumbnail OR strip from video\n"
        "> `/setcaption` - Set custom caption\n"
        "> `/seecaption` - View saved caption\n> \n"
        "> **👑 Owner Only:**\n"
        "> `/authorize` - Authorize a new user\n"
        "> `/removeauthorize` - Remove a user\n"
        "> `/seeauthorizeusers` - See authorized users\n"
        "> `/setbotsetting` - Set bot to Public/Private mode"
    )

# ==========================================
# 6. COMMAND HANDLERS
# ==========================================

@app.on_message(filters.command("start"))
async def start_command(client, message):
    if not await check_access(client, message): return
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Bot Commands 📋", callback_data="show_commands")]])
    await message.reply_photo(photo=START_IMAGE, caption=get_start_text(message.from_user.first_name, message.from_user.id), reply_markup=markup)

@app.on_message(filters.command("setbotsetting"))
async def set_bot_setting(client, message):
    if not is_owner(message.from_user.id):
        return await message.reply_text("❌ Only the Owner can use this command.")
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("Private 🔒", callback_data="set_mode_private"), InlineKeyboardButton("Public 🌍", callback_data="set_mode_public")]])
    await message.reply_text(f"⚙️ **Bot Settings**\n\nCurrent Mode: **{bot_mode.upper()}**", reply_markup=markup)

@app.on_message(filters.command("authorize"))
async def authorize_user(client, message):
    if not is_owner(message.from_user.id): return
    parts = message.text.split()
    if len(parts) == 1:
        return await message.reply_text("⚠️ **Wrong Input!**\n\n**Usage:** `/authorize <user_id>`\n**Example:** `/authorize 123456789`", reply_markup=close_markup)
    try:
        user_to_add = int(parts[1])
        authorized_users.add(user_to_add); save_database()
        await message.reply_text(f"✅ User `{user_to_add}` authorized.", reply_markup=close_markup)
    except: await message.reply_text("⚠️ User ID must be a number.")

@app.on_message(filters.command("removeauthorize"))
async def remove_authorize(client, message):
    if not is_owner(message.from_user.id): return
    parts = message.text.split()
    if len(parts) == 1:
        return await message.reply_text("⚠️ **Wrong Input!**\n\n**Usage:** `/removeauthorize <user_id>`\n**Example:** `/removeauthorize 123456789`", reply_markup=close_markup)
    try:
        user_to_remove = int(parts[1])
        if user_to_remove in authorized_users:
            authorized_users.remove(user_to_remove); save_database()
            await message.reply_text(f"✅ User `{user_to_remove}` removed.", reply_markup=close_markup)
        else: await message.reply_text("⚠️ User not in list.", reply_markup=close_markup)
    except: await message.reply_text("⚠️ User ID must be a number.")

@app.on_message(filters.command("seeauthorizeusers"))
async def see_authorized_users(client, message):
    if not is_owner(message.from_user.id): return
    if not authorized_users: return await message.reply_text("ℹ️ No authorized users found.")
    users_list = "\n".join([f"• `{uid}`" for uid in authorized_users])
    await message.reply_text(f"📋 **Authorized Users:**\n{users_list}", reply_markup=close_markup)

@app.on_message(filters.command("setthumbnail"))
async def set_thumbnail(client, message):
    if not await check_access(client, message): return
    if message.reply_to_message and message.reply_to_message.photo:
        user_thumbnails[message.from_user.id] = message.reply_to_message.photo.file_id
        save_database(); await message.reply_text("✅ **Thumbnail saved successfully!**", reply_markup=close_markup)
    else: await message.reply_text("⚠️ Please **reply** to a Photo with `/setthumbnail`.")

@app.on_message(filters.command("seesetthumb"))
async def see_thumbnail(client, message):
    if not await check_access(client, message): return
    tid = user_thumbnails.get(message.from_user.id)
    if tid: await client.send_photo(chat_id=message.chat.id, photo=tid, caption="🖼️ **Your currently saved thumbnail.**", reply_markup=close_markup)
    else: await message.reply_text("ℹ️ You haven't set any thumbnail yet.")

@app.on_message(filters.command("getthumbnail"))
async def get_video_thumbnail(client, message):
    if not await check_access(client, message): return
    if not message.reply_to_message or not message.reply_to_message.video:
        return await message.reply_text("⚠️ Please **reply** to a video with `/getthumbnail`.")
    
    status = await message.reply_text("⏳ Extracting thumbnail...")
    try:
        video = message.reply_to_message.video
        if video.thumbs:
            path = await client.download_media(video.thumbs[0].file_id)
        else:
            v_path = await message.reply_to_message.download()
            path = take_screen_shot(v_path, "downloads", 2)
            if v_path and os.path.exists(v_path): os.remove(v_path)

        if path:
            await client.send_photo(chat_id=message.chat.id, photo=path, caption="🖼️ **Video Thumbnail Extracted!**", reply_markup=close_markup)
            if os.path.exists(path): os.remove(path)
        else:
            await status.edit_text("❌ Failed to extract thumbnail.")
        await status.delete()
    except Exception as e: await status.edit_text(f"❌ Error: {e}")

@app.on_message(filters.command("setcaption"))
async def set_caption(client, message):
    if not await check_access(client, message): return
    parts = message.text.markdown.split(None, 1)
    if len(parts) > 1:
        user_captions[message.from_user.id] = parts[1]
        save_database(); await message.reply_text("✅ **Custom caption saved successfully!**", reply_markup=close_markup)
    else: await message.reply_text("⚠️ **Wrong Input!**\n\n**Usage:** `/setcaption <your text>`\n**Example:** `/setcaption hi`", reply_markup=close_markup)

@app.on_message(filters.command("seecaption"))
async def see_caption(client, message):
    if not await check_access(client, message): return
    user_id = message.from_user.id
    if user_id in user_captions: await message.reply_text(f"📝 **Your Current Caption:**\n\n{user_captions[user_id]}", reply_markup=close_markup)
    else: await message.reply_text("ℹ️ No custom caption set.")

@app.on_message(filters.command("removethumb"))
async def remove_thumbnail(client, message):
    if not await check_access(client, message): return
    user_id = message.from_user.id
    if message.reply_to_message and message.reply_to_message.video:
        status = await message.reply_text("⏳ Processing thumbnail removal...")
        try:
            v_path = await message.reply_to_message.download(progress=progress_callback, progress_args=(status, "📥 Downloading...", time.time()))
            thumb_path = take_screen_shot(v_path, "downloads", 2)
            dur = get_duration(v_path)
            await client.send_video(chat_id=message.chat.id, video=v_path, thumb=thumb_path, caption=message.reply_to_message.caption or "", supports_streaming=True)
            if thumb_path and os.path.exists(thumb_path): os.remove(thumb_path)
            if v_path and os.path.exists(v_path): os.remove(v_path)
            await status.delete()
        except Exception as e: await status.edit_text(f"❌ Error: {e}")
    else:
        if user_id in user_thumbnails:
            del user_thumbnails[user_id]; save_database()
            await message.reply_text("🗑️ **Saved thumbnail removed from settings.**", reply_markup=close_markup)
        else: await message.reply_text("ℹ️ No thumbnail to remove.")

# ==========================================
# 7. FILE PROCESSING (WITH SELECTION BUTTONS)
# ==========================================
@app.on_message(filters.video | filters.document)
async def handle_file(client, message):
    if not await check_access(client, message): return
    if message.from_user.id not in user_thumbnails:
        return await message.reply_text("❌ Please set a thumbnail first!")
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Video 📹", callback_data=f"v|{message.id}"),
         InlineKeyboardButton("File 📁", callback_data=f"f|{message.id}")]
    ])
    await message.reply_text("Choose output format:", reply_markup=markup)

@app.on_callback_query(filters.regex(r"^(v|f)\|"))
async def process_file_callback(client, callback_query):
    fmt, mid = callback_query.data.split("|")
    original_msg = await client.get_messages(callback_query.message.chat.id, int(mid))
    uid = callback_query.from_user.id
    msg = await callback_query.message.edit_text("⏳ Processing...")
    
    try:
        file_path = await original_msg.download(progress=progress_callback, progress_args=(msg, "📥 Downloading...", time.time()))
        thumb_path = await client.download_media(user_thumbnails[uid])
        caption = user_captions.get(uid, original_msg.caption or "")
        
        if fmt == "v":
            dur = get_duration(file_path); w, h = get_width_height(file_path)
            await client.send_video(callback_query.message.chat.id, video=file_path, thumb=thumb_path, caption=caption, duration=dur, width=w, height=h, progress=progress_callback, progress_args=(msg, "📤 Uploading Video...", time.time()))
        else:
            await client.send_document(callback_query.message.chat.id, document=file_path, thumb=thumb_path, caption=caption, progress=progress_callback, progress_args=(msg, "📤 Uploading File...", time.time()))
        await msg.delete()
    except Exception as e: await msg.edit_text(f"❌ Error: {e}")
    finally:
        if 'file_path' in locals() and os.path.exists(file_path): os.remove(file_path)
        if 'thumb_path' in locals() and os.path.exists(thumb_path): os.remove(thumb_path)

# ==========================================
# 8. UI CALLBACKS (Back/Commands/Settings)
# ==========================================
@app.on_callback_query(filters.regex("show_commands"))
async def show_commands_handler(client, callback_query):
    await callback_query.edit_message_media(media=InputMediaPhoto(CMDS_IMAGE, caption=get_commands_text()), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Back 🔙", callback_data="back_start")]]))

@app.on_callback_query(filters.regex("back_start"))
async def back_start_handler(client, callback_query):
    user_name = callback_query.from_user.first_name
    user_id = callback_query.from_user.id
    await callback_query.edit_message_media(media=InputMediaPhoto(START_IMAGE, caption=get_start_text(user_name, user_id)), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Bot Commands 📋", callback_data="show_commands")]]))

@app.on_callback_query(filters.regex("set_mode_"))
async def mode_callback(client, callback_query):
    global bot_mode
    if not is_owner(callback_query.from_user.id): return
    bot_mode = "private" if "private" in callback_query.data else "public"
    save_database(); await callback_query.edit_message_text(f"✅ Bot Mode set to: **{bot_mode.upper()}**")

@app.on_callback_query(filters.regex("close_msg"))
async def close_message_handler(client, callback_query):
    try: await callback_query.message.delete()
    except: pass

# ==========================================
# 9. START BOT
# ==========================================
if __name__ == "__main__":
    print("Bot is starting..."); app.run()
    
