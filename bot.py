import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import uuid
import certifi
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from flask import Flask
from threading import Thread
from urllib.parse import quote
from motor.motor_asyncio import AsyncIOMotorClient

# --- Web Server ---
web_app = Flask(__name__)
@web_app.route('/')
def home():
    return "Trenda Bot is Running with Premium Ultimate Features!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_server).start()
# ------------------

# Configuration
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0)) # Super Admin
MONGO_URI = os.environ.get("MONGO_URI", "") 

# Default Configurations
DEFAULT_FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", -1003903891234)) 
DEFAULT_FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/+57MfRxJ_0QdiZjRl")
DEFAULT_DELETE_TIME = 300 

START_PIC = "https://telegra.ph/file/0c320d759dc23bcbbbb9b.jpg"

app = Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB Setup
if MONGO_URI:
    mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = mongo_client["trenda_movies"]
    movies_col = db["movies"]
    users_col = db["users"]
    searches_col = db["searches"]
    posters_col = db["posters"]  
    settings_col = db["settings"] 
    admins_col = db["admins"] # Multiple Admins Collection
else:
    print("⚠️ WARNING: MONGO_URI is not set!", flush=True)

# Helper: Check if User is Admin or Super Admin
async def is_admin(user_id):
    if user_id == ADMIN_ID:
        return True
    admin = await admins_col.find_one({"user_id": user_id})
    return bool(admin)

# Helper: Get Dynamic FSub Settings
async def get_fsub_config():
    config = await settings_col.find_one({"_id": "fsub_config"})
    if config:
        return config.get("channel_id"), config.get("link")
    return DEFAULT_FORCE_SUB_CHANNEL, DEFAULT_FORCE_SUB_LINK

# Helper: Get Auto-Delete Time
async def get_delete_time():
    config = await settings_col.find_one({"_id": "timer_config"})
    if config:
        return config.get("time", DEFAULT_DELETE_TIME)
    return DEFAULT_DELETE_TIME

# Add New User
async def add_user(user_id):
    try:
        await users_col.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"user_id": user_id, "is_banned": 0}},
            upsert=True
        )
        return True
    except Exception:
        return False

# Check Access (Ban & FSub Strict Rule)
async def check_user_access(client, message):
    user_id = message.from_user.id
    
    try:
        user = await users_col.find_one({"user_id": user_id})
        if user and user.get("is_banned") == 1:
            await message.reply_text("⛔ **You are banned from using this bot.**")
            return False
    except Exception: pass
            
    fsub_channel, fsub_link = await get_fsub_config()
    if fsub_channel != -100:
        try:
            member = await client.get_chat_member(fsub_channel, user_id)
            if member.status in ["kicked", "left"]: # Strict Check
                raise UserNotParticipant
        except UserNotParticipant:
            btn = [[InlineKeyboardButton("📢 Join Our Channel", url=fsub_link)]]
            error_text = "⚠️ **Please join our main channel to use this bot!**\n\nClick the button below to join, then come back and search again."
            try:
                await message.reply_photo(photo=START_PIC, caption=error_text, reply_markup=InlineKeyboardMarkup(btn))
            except Exception:
                await message.reply_text(error_text, reply_markup=InlineKeyboardMarkup(btn))
            return False
        except Exception: pass 
    return True

# Start Command
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if not await add_user(message.from_user.id):
        await message.reply_text("⚠️ **Database is not connected yet!**")
        return
    if not await check_user_access(client, message): return
        
    _, fsub_link = await get_fsub_config()
    buttons = [
        [InlineKeyboardButton("🔍 Search Movies", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📢 Updates Channel", url=fsub_link)]
    ]
    welcome_text = f"👋 **Hello {message.from_user.first_name}, Welcome to Trenda Cinema Bot!**\n\nType the name of the movie you want to download."
    try:
        await message.reply_photo(photo=START_PIC, caption=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

# ================= 5+ ADVANCED ADMIN PANEL =================

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if not await is_admin(message.from_user.id): return
    buttons = [
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
         InlineKeyboardButton("🔥 Trending", callback_data="admin_trend")],
        [InlineKeyboardButton("⚙️ FSub Control", callback_data="admin_fsub"),
         InlineKeyboardButton("⏱️ Auto-Delete", callback_data="admin_timer")],
        [InlineKeyboardButton("👥 Manage Admins", callback_data="admin_mng"),
         InlineKeyboardButton("🗑️ Clear DB", callback_data="admin_clear")],
        [InlineKeyboardButton("❌ Del Movie", callback_data="admin_delmovie_info")] # New Button
    ]
    await message.reply_text("👨‍💻 **Welcome to Premium Admin Control Panel!**\nSelect an option:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^admin_"))
async def admin_callbacks(client, callback_query):
    if not await is_admin(callback_query.from_user.id): return
    action = callback_query.data.split("_")[1]

    if action == "stats":
        u = await users_col.count_documents({})
        m = await movies_col.count_documents({})
        p = await posters_col.count_documents({})
        await callback_query.message.edit_text(f"📊 **Bot Stats:**\n\n👥 Users: {u}\n🎬 Movies: {m}\n🖼️ Posters: {p}")

    elif action == "trend":
        cursor = searches_col.find().sort("count", -1).limit(10)
        results = await cursor.to_list(length=10)
        text = "🔥 **Top 10 Trending Searches:**\n\n" if results else "No searches yet!"
        for idx, res in enumerate(results, 1):
            text += f"{idx}. {res['_id'].title()} ({res['count']} searches)\n"
        await callback_query.message.edit_text(text)

    elif action == "fsub":
        f_id, f_link = await get_fsub_config()
        await callback_query.message.edit_text(f"⚙️ **FSub Config:**\n\nID: `{f_id}`\nLink: {f_link}\n\nUpdate using:\n`/setchannel ID`\n`/setlink LINK`")

    elif action == "timer":
        t = await get_delete_time()
        await callback_query.message.edit_text(f"⏱️ **Current Auto-Delete Timer:** {t} seconds.\n\nUpdate using:\n`/settimer SECONDS`\n*(e.g., /settimer 300)*")

    elif action == "mng":
        text = f"👥 **Admin Management:**\n\n👑 Super Admin: `{ADMIN_ID}`\n\nAdd/Remove Admins using:\n`/addadmin USER_ID`\n`/removeadmin USER_ID`"
        await callback_query.message.edit_text(text)
        
    elif action == "delmovie_info":
        text = f"❌ **Delete a Movie**\n\nTo completely delete a movie (Files + Poster) from the bot, send this command:\n\n`/delmovie Movie Name`\n*(e.g., /delmovie Derby)*"
        await callback_query.message.edit_text(text)

    elif action == "clear":
        buttons = [[InlineKeyboardButton("✅ Confirm Clear All", callback_data="admin_confclear")], [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel_home")]]
        await callback_query.message.edit_text("⚠️ **Are you sure to clear movies and posters?**", reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "confclear":
        await movies_col.delete_many({})
        await posters_col.delete_many({})
        await callback_query.message.edit_text("✅ Databases cleared successfully!")

# Multi-Admin & Settings Commands
@app.on_message(filters.command("setchannel") & filters.private)
async def set_channel_id(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        new_id = int(message.command[1])
        await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"channel_id": new_id}}, upsert=True)
        await message.reply_text(f"✅ FSub Channel ID set to: `{new_id}`")
    except Exception: await message.reply_text("Usage: `/setchannel -100xxxxxxxx`")

@app.on_message(filters.command("setlink") & filters.private)
async def set_channel_link(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        new_link = message.command[1]
        await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"link": new_link}}, upsert=True)
        await message.reply_text(f"✅ FSub Link set to:\n{new_link}")
    except Exception: await message.reply_text("Usage: `/setlink LINK`")

@app.on_message(filters.command("settimer") & filters.private)
async def set_timer(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        t = int(message.command[1])
        await settings_col.update_one({"_id": "timer_config"}, {"$set": {"time": t}}, upsert=True)
        await message.reply_text(f"✅ Auto-Delete timer updated to: `{t}` seconds.")
    except Exception: await message.reply_text("Usage: `/settimer 300`")

@app.on_message(filters.command("addadmin") & filters.private)
async def add_admin_cmd(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.command[1])
        await admins_col.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
        await message.reply_text(f"✅ User `{uid}` added as Admin.")
    except Exception: await message.reply_text("Usage: `/addadmin USER_ID`")

@app.on_message(filters.command("removeadmin") & filters.private)
async def remove_admin_cmd(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.command[1])
        await admins_col.delete_one({"user_id": uid})
        await message.reply_text(f"❌ User `{uid}` removed from Admin.")
    except Exception: await message.reply_text("Usage: `/removeadmin USER_ID`")

@app.on_message(filters.command("ban") & filters.private)
async def ban_user(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        target_id = int(message.command[1])
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 1}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` BANNED.")
    except Exception: await message.reply_text("Usage: `/ban UserID`")

@app.on_message(filters.command("unban") & filters.private)
async def unban_user(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        target_id = int(message.command[1])
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 0}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` UNBANNED.")
    except Exception: await message.reply_text("Usage: `/unban UserID`")

# --- Delete Specific Movie (Files + Poster) ---
@app.on_message(filters.command("delmovie") & filters.private)
async def delete_movie(client, message):
    if not await is_admin(message.from_user.id): return
    if len(message.command) < 2:
        await message.reply_text("⚠️ **Usage:** `/delmovie Movie Name`\n*(e.g., /delmovie Derby)*")
        return
        
    query = message.text.split(" ", 1)[1].strip().lower()
    search_pattern = query.replace(" ", ".*")
    
    del_files = await movies_col.delete_many({"file_name": {"$regex": search_pattern, "$options": "i"}})
    del_poster = await posters_col.delete_one({"title": query})
    
    text = f"✅ **Deleted successfully!**\n\n🎬 Movie: `{query.title()}`\n📁 Files deleted: `{del_files.deleted_count}`\n🖼️ Poster deleted: `{'Yes' if del_poster.deleted_count > 0 else 'No'}`"
    await message.reply_text(text)


# ================= ADVANCED COPY-BROADCAST SYSTEM =================

@app.on_message(filters.command("broadcast") & filters.private)
async def advanced_broadcast(client, message):
    if not await is_admin(message.from_user.id): return
    if not message.reply_to_message:
        await message.reply_text("⚠️ **How to use:**\nReply to any message (Text, Photo, Video, Animation with/without buttons) with `/broadcast` to send it to all users.")
        return

    reply_msg = message.reply_to_message
    status_msg = await message.reply_text("📢 **Advanced Broadcast Started...**")
    
    success, failed = 0, 0
    async for user in users_col.find({}):
        try:
            # copy_message preserves photos, videos, captions, and inline buttons perfectly!
            await reply_msg.copy(chat_id=user["user_id"])
            success += 1
            await asyncio.sleep(0.05) 
        except Exception:
            failed += 1
            
    await status_msg.edit_text(f"✅ **Broadcast Completed!**\n\n💚 Successful: {success}\n❤️ Failed/Blocked: {failed}")


# ================= POSTER & FILE SAVING LOGIC =================

@app.on_message(filters.photo & filters.channel)
async def save_poster(client, message):
    if message.caption and "🎬 Title :" in message.caption:
        try:
            lines = message.caption.split('\n')
            title_line = [line for line in lines if "Title :" in line][0]
            movie_title = title_line.split(":", 1)[1].strip().lower()
            await posters_col.update_one(
                {"title": movie_title},
                {"$set": {"file_id": message.photo.file_id, "caption": message.caption}},
                upsert=True
            )
        except Exception: pass

@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if file:
        f_name = getattr(file, "file_name", "Unknown_Movie")
        short_id = uuid.uuid4().hex[:8] 
        try:
            await movies_col.update_one(
                {"file_id": file.file_id},
                {"$setOnInsert": {"file_name": f_name, "file_size": getattr(file, "file_size", 0), "short_id": short_id}},
                upsert=True
            )
        except Exception: pass

# ================= SMART REGEX SEARCH =================

@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    if message.text.startswith("/"): return
    if not await add_user(message.from_user.id): return
    if not await check_user_access(client, message): return # Strict FSub check is here
        
    query = message.text.strip()
    await searches_col.update_one({"_id": query.lower()}, {"$inc": {"count": 1}}, upsert=True)
    
    search_pattern = query.replace(" ", ".*")
    cursor = movies_col.find({"file_name": {"$regex": search_pattern, "$options": "i"}}).limit(50)
    results = await cursor.to_list(length=50)
    
    if not results:
        btn = [[InlineKeyboardButton("📩 Request Movie to Admin", callback_data=f"req_{query[:30]}")]]
        await message.reply_text("🥲 **Sorry, this movie is not available.**", reply_markup=InlineKeyboardMarkup(btn))
        return

    buttons = []
    for result in results:
        size_mb = round(result["file_size"] / (1024 * 1024), 2)
        full_name = result['file_name']
        # Trim Name to keep buttons small (Max 25 characters)
        short_name = full_name[:25] + "..." if len(full_name) > 25 else full_name
        btn_text = f"[{size_mb}MB] {short_name}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{result['short_id']}")])

    poster = await posters_col.find_one({"title": query.lower()})
    if poster:
        final_caption = poster["caption"] + "\n\n👇 **Choose Quality to Download:**"
        try:
            await message.reply_photo(photo=poster["file_id"], caption=final_caption, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await message.reply_text(final_caption, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text("🍿 **Here are your search results:**", reply_markup=InlineKeyboardMarkup(buttons))

# ================= SEND FILE & AUTO DELETE =================

async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception: pass

@app.on_callback_query(filters.regex(r"^send_"))
async def send_file(client, callback_query):
    if not await check_user_access(client, callback_query): return
    short_id = callback_query.data.split("_")[1]
    result = await movies_col.find_one({"short_id": short_id})
    
    if result:
        await callback_query.answer("Sending file... Please wait!", show_alert=False)
        del_time = await get_delete_time()
        del_mins = del_time // 60
        sent_msg = await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result["file_id"], 
            caption=f"🎥 **{result['file_name']}**\n\n⚠️ *This file will auto-delete in {del_mins} minutes to prevent copyright issues.*"
        )
        asyncio.create_task(delete_after_delay(sent_msg, del_time))
    else:
        await callback_query.answer("File not found!", show_alert=True)

@app.on_callback_query(filters.regex(r"^req_"))
async def request_movie(client, callback_query):
    query = callback_query.data.split("_", 1)[1]
    user = callback_query.from_user
    try:
        await client.send_message(ADMIN_ID, f"🆕 **New Movie Request!**\n\n🎬 Movie: `{query}`\n👤 User: {user.mention} (`{user.id}`)")
        await callback_query.answer("Your request has been sent to the admin!", show_alert=True)
    except Exception:
        await callback_query.answer("Failed to contact the admin.", show_alert=True)

print("Bot started successfully with 5+ Ultimate Features & Custom Broadcast!", flush=True)
app.run()
