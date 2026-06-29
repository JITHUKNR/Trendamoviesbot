import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import uuid
import certifi
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
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
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
MONGO_URI = os.environ.get("MONGO_URI", "") 

# Default FSub (Will be overridden by DB settings if changed by Admin)
DEFAULT_FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", -100)) 
DEFAULT_FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/")
AUTO_DELETE_TIME = 300 

# Welcome Image URL
START_PIC = "https://telegra.ph/file/11797c555d4d3d758c0c9.jpg" # ഇവിടെ നിങ്ങളുടെ സ്വന്തം പോസ്റ്റർ ലിങ്ക് കൊടുക്കാം

app = Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB Setup
if MONGO_URI:
    mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = mongo_client["trenda_movies"]
    movies_col = db["movies"]
    users_col = db["users"]
    searches_col = db["searches"]
    posters_col = db["posters"]  # New Collection for Posters
    settings_col = db["settings"] # New Collection for Dynamic FSub
else:
    print("⚠️ WARNING: MONGO_URI is not set!", flush=True)

# Get Dynamic FSub Settings
async def get_fsub_config():
    config = await settings_col.find_one({"_id": "fsub_config"})
    if config:
        return config.get("channel_id"), config.get("link")
    return DEFAULT_FORCE_SUB_CHANNEL, DEFAULT_FORCE_SUB_LINK

# Add New User
async def add_user(user_id):
    try:
        await users_col.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"user_id": user_id, "is_banned": 0}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"MongoDB Error: {e}", flush=True)
        return False

# Check Access (Ban & FSub)
async def check_user_access(client, message):
    user_id = message.from_user.id
    
    try:
        user = await users_col.find_one({"user_id": user_id})
        if user and user.get("is_banned") == 1:
            await message.reply_text("⛔ **You are banned from using this bot.**")
            return False
    except Exception:
        pass
            
    fsub_channel, fsub_link = await get_fsub_config()
    
    if fsub_channel != -100:
        try:
            await client.get_chat_member(fsub_channel, user_id)
        except UserNotParticipant:
            btn = [[InlineKeyboardButton("📢 Join Our Channel", url=fsub_link)]]
            await message.reply_photo(
                photo=START_PIC,
                caption="⚠️ **Please join our main channel to use this bot and download movies!**\n\nClick the button below to join, then come back and search again.", 
                reply_markup=InlineKeyboardMarkup(btn)
            )
            return False
        except Exception:
            pass 
        
    return True

# Premium Start Command
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    db_status = await add_user(message.from_user.id)
    if not db_status:
        await message.reply_text("⚠️ **Database is not connected yet!**\nPlease wait a minute and try again.")
        return
        
    if not await check_user_access(client, message):
        return
        
    buttons = [
        [InlineKeyboardButton("🔍 Search Movies", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📢 Updates Channel", url=await get_fsub_config() and (await get_fsub_config())[1] or "https://t.me/"),
         InlineKeyboardButton("👨‍💻 Admin", callback_data="help_admin")]
    ]
    
    welcome_text = (
        f"👋 **Hello {message.from_user.first_name}, Welcome to Trenda Cinema Bot!**\n\n"
        f"🎬 I can provide you with direct download links for Malayalam & Other Movies.\n\n"
        f"💡 **How to use me?**\n"
        f"Just type the name of the movie you want to download and send it to me.\n"
        f"*(e.g., Derby, Drishyam, etc.)*"
    )
    
    await message.reply_photo(
        photo=START_PIC,
        caption=welcome_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ================= ADVANCED ADMIN PANEL =================

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if message.from_user.id != ADMIN_ID: return
    buttons = [
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats"),
         InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ FSub Settings (New)", callback_data="admin_fsub_info")],
        [InlineKeyboardButton("🗑️ Clear Movies DB", callback_data="admin_cleardb")]
    ]
    await message.reply_text("👨‍💻 **Welcome to the Premium Admin Panel!**\nSelect an option below:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^admin_"))
async def admin_callbacks(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID: return
    action = callback_query.data.split("_")[1]

    if action == "stats":
        users_count = await users_col.count_documents({})
        movies_count = await movies_col.count_documents({})
        posters_count = await posters_col.count_documents({})
        text = f"📊 **Trenda Bot Statistics**\n\n👥 Users: {users_count}\n🎬 Movies: {movies_count}\n🖼️ Posters Saved: {posters_count}"
        await callback_query.message.edit_text(text)

    elif action == "fsub":
        # Info about setting dynamic FSub
        f_id, f_link = await get_fsub_config()
        text = (
            f"⚙️ **Force Subscribe Settings**\n\n"
            f"**Current Channel ID:** `{f_id}`\n"
            f"**Current Link:** {f_link}\n\n"
            f"💡 **To Change Settings instantly, send commands like this:**\n\n"
            f"`/setchannel -10012345678`\n"
            f"`/setlink https://t.me/+YourLinkHere`"
        )
        await callback_query.message.edit_text(text)
        
    # (Rest of Admin actions remain same: cleardb, broadcast...)

# Dynamic FSub Commands
@app.on_message(filters.command("setchannel") & filters.private)
async def set_channel_id(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        new_id = int(message.command[1])
        await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"channel_id": new_id}}, upsert=True)
        await message.reply_text(f"✅ **Force Sub Channel ID updated to:** `{new_id}`")
    except Exception:
        await message.reply_text("⚠️ **Usage:** `/setchannel -100123456789`")

@app.on_message(filters.command("setlink") & filters.private)
async def set_channel_link(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        new_link = message.command[1]
        await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"link": new_link}}, upsert=True)
        await message.reply_text(f"✅ **Force Sub Link updated to:**\n{new_link}")
    except Exception:
        await message.reply_text("⚠️ **Usage:** `/setlink https://t.me/yourlink`")

# ================= POSTER & FILE SAVING LOGIC =================

@app.on_message(filters.photo & filters.channel)
async def save_poster(client, message):
    # ഈ ഫംഗ്ഷൻ ചാനലിലെ പോസ്റ്ററുകൾ സേവ് ചെയ്യും
    if message.caption and "🎬 Title :" in message.caption:
        try:
            # Extract title exactly from the line
            lines = message.caption.split('\n')
            title_line = [line for line in lines if "Title :" in line][0]
            movie_title = title_line.split(":", 1)[1].strip().lower()
            
            await posters_col.update_one(
                {"title": movie_title},
                {"$set": {
                    "file_id": message.photo.file_id, 
                    "caption": message.caption
                }},
                upsert=True
            )
            print(f"Poster Saved for: {movie_title}")
        except Exception as e:
            print(f"Error parsing poster: {e}")

@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if file:
        f_name = getattr(file, "file_name", "Unknown_Movie")
        short_id = uuid.uuid4().hex[:8] 
        try:
            await movies_col.update_one(
                {"file_id": file.file_id},
                {"$setOnInsert": {
                    "file_name": f_name, 
                    "file_size": getattr(file, "file_size", 0),
                    "short_id": short_id
                }},
                upsert=True
            )
        except Exception as e:
            pass

# ================= SMART SEARCH =================

@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    if message.text.startswith("/"): return
    
    if not await check_user_access(client, message): return
        
    query = message.text.strip()
    
    await searches_col.update_one({"_id": query.lower()}, {"$inc": {"count": 1}}, upsert=True)
    
    # Smart Regex Search (Spaces will match any character)
    search_pattern = query.replace(" ", ".*")
    cursor = movies_col.find({"file_name": {"$regex": search_pattern, "$options": "i"}}).limit(50)
    results = await cursor.to_list(length=50)
    
    if not results:
        btn = [[InlineKeyboardButton("📩 Request Movie to Admin", callback_data=f"req_{query[:30]}")]]
        await message.reply_text("🥲 **Sorry, this movie is not available.**", reply_markup=InlineKeyboardMarkup(btn))
        return

    # Create File Buttons
    buttons = []
    for result in results:
        size_mb = round(result["file_size"] / (1024 * 1024), 2)
        btn_text = f"[{size_mb}MB] {result['file_name']}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{result['short_id']}")])

    # Check if a Poster matches the query
    poster = await posters_col.find_one({"title": query.lower()})
    
    if poster:
        # പോസ്റ്റർ ഉണ്ടെങ്കിൽ, പോസ്റ്ററിന് താഴെ ബട്ടണുകൾ വരും!
        final_caption = poster["caption"] + "\n\n👇 **Choose Quality to Download:**"
        await message.reply_photo(
            photo=poster["file_id"],
            caption=final_caption,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        # പോസ്റ്റർ ഇല്ലെങ്കിൽ സാധാരണ രീതിയിൽ ബട്ടൺ നൽകും
        await message.reply_text("🍿 **Here are your search results:**", reply_markup=InlineKeyboardMarkup(buttons))

# ================= SEND FILE LOGIC =================

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
        sent_msg = await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result["file_id"], 
            caption=f"🎥 **{result['file_name']}**\n\n⚠️ *This file will auto-delete in 5 minutes to prevent copyright issues.*"
        )
        asyncio.create_task(delete_after_delay(sent_msg, AUTO_DELETE_TIME))
    else:
        await callback_query.answer("File not found!", show_alert=True)

print("Bot started successfully with Premium features!", flush=True)
app.run()
