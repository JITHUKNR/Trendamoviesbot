import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import uuid
import certifi
import re
import logging
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaVideo
from pyrogram.errors import UserNotParticipant
from flask import Flask
from threading import Thread
from urllib.parse import quote
from motor.motor_asyncio import AsyncIOMotorClient

# ലോഗിംഗ് സജ്ജീകരിക്കുന്നു
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Web Server (Keep Alive) ---
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
DEFAULT_START_PIC = "https://telegra.ph/file/0c320d759dc23bcbbbb9b.jpg"

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
    admins_col = db["admins"] 
else:
    logger.warning("⚠️ MONGO_URI is not set! Database features will be disabled.")
    movies_col = users_col = searches_col = posters_col = settings_col = admins_col = None


# ================= DATABASE HELPERS =================

async def is_admin(user_id):
    if user_id == ADMIN_ID: return True
    if admins_col is None: return False
    admin = await admins_col.find_one({"user_id": user_id})
    return bool(admin)

async def get_fsub_config():
    if settings_col is None: return DEFAULT_FORCE_SUB_CHANNEL, DEFAULT_FORCE_SUB_LINK
    config = await settings_col.find_one({"_id": "fsub_config"})
    if config: return config.get("channel_id"), config.get("link")
    return DEFAULT_FORCE_SUB_CHANNEL, DEFAULT_FORCE_SUB_LINK

async def get_delete_time():
    if settings_col is None: return DEFAULT_DELETE_TIME
    config = await settings_col.find_one({"_id": "timer_config"})
    if config: return config.get("time", DEFAULT_DELETE_TIME)
    return DEFAULT_DELETE_TIME

async def get_start_config():
    default_text = "✨ **Welcome to Trenda Cinema Bot** ✨\n\n👤 **YOUR PROFILE:**\n┣ 📝 **Name:** {name}\n┣ 🆔 **User ID:** `{id}`\n┗ 🔗 **Username:** {username}\n\n🍿 *Just type the name of the movie you want to download!*"
    if settings_col is None: return default_text, DEFAULT_START_PIC
    config = await settings_col.find_one({"_id": "start_config"})
    if config:
        return config.get("text", default_text), config.get("pic", DEFAULT_START_PIC)
    return default_text, DEFAULT_START_PIC

async def get_website_link():
    if settings_col is None: return ""
    config = await settings_col.find_one({"_id": "web_config"})
    if config: return config.get("url", "")
    return ""

async def add_user(user_id):
    if users_col is None: return False
    try:
        await users_col.update_one({"user_id": user_id}, {"$setOnInsert": {"user_id": user_id, "is_banned": 0}}, upsert=True)
        return True
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        return False

async def check_user_access(client, message):
    user_id = message.from_user.id

    # 1. Ban Check
    if users_col:
        try:
            user = await users_col.find_one({"user_id": user_id})
            if user and user.get("is_banned") == 1:
                await message.reply_text("⛔ **You are banned from using this bot.**")
                return False
        except Exception: pass

    # 2. Strict FSub Check
    fsub_channel, fsub_link = await get_fsub_config()

    if fsub_channel != 0:
        try:
            member = await client.get_chat_member(fsub_channel, user_id)
            if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.RESTRICTED]:
                raise UserNotParticipant
        except UserNotParticipant:
            btn = [
                [InlineKeyboardButton("📢 Join Our Channel", url=fsub_link)],
                [InlineKeyboardButton("🔄 I Have Joined", callback_data="check_joined")]
            ]
            error_msg = "⚠️ **Please join our main channel to use this bot and download movies!**\n\nClick the button below to join, then click 'I Have Joined'."
            
            try:
                _, custom_pic = await get_start_config()
                pic_to_send = custom_pic if custom_pic != "user_dp" else DEFAULT_START_PIC
                await message.reply_photo(photo=pic_to_send, caption=error_msg, reply_markup=InlineKeyboardMarkup(btn))
            except Exception:
                await message.reply_text(error_msg, reply_markup=InlineKeyboardMarkup(btn))
            return False
        except Exception as e:
            logger.error(f"FSub Error: {e}")
            return True
    return True


# ================= START COMMAND =================

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if not await add_user(message.from_user.id):
        await message.reply_text("⚠️ **Database is not connected yet!**")
        return
    
    _, fsub_link = await get_fsub_config()
    buttons = [
        [InlineKeyboardButton("🔍 Search Movies", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📢 Updates Channel", url=fsub_link)]
    ]
    
    user = message.from_user
    u_name = user.first_name
    u_id = user.id
    u_username = f"@{user.username}" if user.username else "None"
    
    custom_text, custom_pic = await get_start_config()
    
    photo = custom_pic
    if custom_pic == "user_dp" and user.photo:
        photo = user.photo.big_file_id
    elif custom_pic == "user_dp":
        photo = DEFAULT_START_PIC

    try:
        welcome_text = custom_text.format(name=u_name, id=u_id, username=u_username)
    except Exception:
        welcome_text = custom_text 
    
    try:
        await message.reply_photo(photo=photo, caption=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))


# ================= POSTER & FILE SAVING LOGIC (CHANNELS) =================

@app.on_message(filters.photo & filters.channel)
async def save_poster(client, message):
    if posters_col is None: return
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
        except Exception as e:
            logger.error(f"Error saving poster: {e}")

@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    if movies_col is None: return
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
        except Exception as e:
            logger.error(f"Error saving file: {e}")


# ================= SMART REGEX SEARCH =================

@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    if movies_col is None: return
    if message.text.startswith("/"): return
    if not await add_user(message.from_user.id): return
    if not await check_user_access(client, message): return
        
    query = message.text.strip()
    if searches_col:
        await searches_col.update_one({"_id": query.lower()}, {"$inc": {"count": 1}}, upsert=True)
    
    # Regex സുരക്ഷിതമാക്കുന്നു (ReDoS ഒഴിവാക്കാൻ)
    search_pattern = re.escape(query).replace(r"\ ", ".*")
    cursor = movies_col.find({"file_name": {"$regex": search_pattern, "$options": "i"}}).limit(50)
    results = await cursor.to_list(length=50)
    
    if not results:
        btn = [[InlineKeyboardButton("📩 Request Movie to Admin", callback_data=f"req_{query[:30]}")]]
        await message.reply_text("🥲 **Sorry, this movie is not available.**", reply_markup=InlineKeyboardMarkup(btn))
        return

    buttons = []
    for result in results:
        size_mb = round(result.get("file_size", 0) / (1024 * 1024), 2)
        full_name = result['file_name']
        max_length = 30
        short_name = full_name[:max_length] + "..." if len(full_name) > max_length else full_name
        
        btn_text = f"[{size_mb}MB] {short_name}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{result['short_id']}")])

    poster = await posters_col.find_one({"title": query.lower()}) if posters_col else None
    if poster:
        final_caption = poster["caption"] + "\n\n👇 **Choose Quality to Download:**"
        try:
            await message.reply_photo(photo=poster["file_id"], caption=final_caption, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await message.reply_text(final_caption, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text("🍿 **Here are your search results:**", reply_markup=InlineKeyboardMarkup(buttons))


# ================= SEND FILE, AUTO DELETE & WATCH ONLINE =================

async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception: pass

@app.on_callback_query(filters.regex(r"^send_"))
async def send_file(client, callback_query):
    if not await check_user_access(client, callback_query): return
    short_id = callback_query.data.split("_")[1]
    result = await movies_col.find_one({"short_id": short_id}) if movies_col else None
    
    if result:
        await callback_query.answer("Sending file... Please wait!", show_alert=False)
        del_time = await get_delete_time()
        del_mins = del_time // 60
        
        # --- WATCH ONLINE BUTTON LOGIC ---
        reply_markup = None
        base_url = await get_website_link()
        if base_url:
            search_query = quote(result['file_name'])
            watch_link = f"{base_url.rstrip('/')}/?s={search_query}"
            btn = [[InlineKeyboardButton("💻 Watch Online", url=watch_link)]]
            reply_markup = InlineKeyboardMarkup(btn)
            
        # --- CUSTOM THUMBNAIL LOGIC ---
        thumb_file_id = None
        if settings_col:
            thumb_config = await settings_col.find_one({"_id": "thumb_config"})
            thumb_file_id = thumb_config.get("file_id") if thumb_config else None
        
        sent_msg = await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result["file_id"], 
            caption=f"🎥 **{result['file_name']}**\n\n⚠️ *This file will auto-delete in {del_mins} minutes.*",
            reply_markup=reply_markup
        )
        
        # തംബ്നെയിൽ മാറ്റാൻ ശ്രമിക്കുന്നു
        if thumb_file_id and sent_msg.video:
            try:
                await client.edit_message_media(
                    chat_id=sent_msg.chat.id,
                    message_id=sent_msg.id,
                    media=InputMediaVideo(
                        media=result["file_id"],
                        thumb=thumb_file_id,
                        caption=sent_msg.caption
                    )
                )
            except Exception as e:
                logger.warning(f"Thumb Edit Error (Normal for some files): {e}")
        
        asyncio.create_task(delete_after_delay(sent_msg, del_time))
    else:
        await callback_query.answer("File not found in database!", show_alert=True)

@app.on_callback_query(filters.regex(r"^req_"))
async def request_movie(client, callback_query):
    query = callback_query.data.split("_", 1)[1]
    user = callback_query.from_user
    try:
        await client.send_message(ADMIN_ID, f"🆕 **New Movie Request!**\n\n🎬 Movie: `{query}`\n👤 User: {user.mention} (`{user.id}`)")
        await callback_query.answer("Your request has been sent to the admin!", show_alert=True)
    except Exception:
        await callback_query.answer("Failed to contact the admin.", show_alert=True)


# ================= CHECK JOINED BUTTON LOGIC =================
@app.on_callback_query(filters.regex(r"^check_joined$"))
async def verify_joined(client, callback_query):
    user_id = callback_query.from_user.id
    fsub_channel, _ = await get_fsub_config()
    
    if fsub_channel != 0:
        try:
            member = await client.get_chat_member(fsub_channel, user_id)
            if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.RESTRICTED]:
                await callback_query.answer("⚠️ You haven't joined the channel yet! Please join first.", show_alert=True)
            else:
                await callback_query.message.delete()
                await callback_query.answer("✅ Thank you for joining! Now you can search for movies.", show_alert=True)
        except Exception:
            await callback_query.answer("⚠️ You haven't joined the channel yet! Please join first.", show_alert=True)

print("Bot started successfully with ULTRA PREMIUM Features & Watch Online!", flush=True)
app.run()
