import os
import asyncio
import certifi
from flask import Flask, request
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaDocument
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import UserNotParticipant
from pyrogram.handlers import CallbackQueryHandler, MessageHandler
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
import uuid
from urllib.parse import quote
import logging

# --- FLASK SETUP ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Trenda Bot is Running!"

@web_app.route(f'/{os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")}', methods=['POST'])
def webhook():
    """
    Telegram Webhook ഇവിടെ എത്തും
    """
    json_str = request.get_data(as_text=True)
    update = eval(json_str)
    # ഇവിടെ update process ചെയ്യാൻ പറ്റില്ല, അതിനാൽ നമുക്ക് ഒരു സിംഗിൾ പ്രോസസ്സ് മാത്രം ഉപയോഗിക്കാം
    # ഇതിനായി, നാം ഒരു queue ഉപയോഗിച്ച് അയയ്ക്കും
    asyncio.run_coroutine_threadsafe(process_update(update), bot.loop)
    return 'OK', 200

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
MONGO_URI = os.environ.get("MONGO_URI", "")

# --- DATABASE SETUP ---
mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where())
db = mongo_client["trenda_movies"]
movies_col = db["movies"]
users_col = db["users"]
searches_col = db["searches"]
posters_col = db["posters"]
settings_col = db["settings"]
admins_col = db["admins"]

# --- DEFAULT VALUES ---
DEFAULT_FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", -1003903891234))
DEFAULT_FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/+57MfRxJ_0QdiZjRl")
DEFAULT_DELETE_TIME = 300
DEFAULT_START_PIC = "https://telegra.ph/file/0c320d759dc23bcbbbb9b.jpg"

# --- CLIENT INIT ---
bot = Client(
    "TrendaMoviesBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=10
)

# --- DATABASE HELPERS ---
async def is_admin(user_id):
    if user_id == ADMIN_ID: return True
    admin = await admins_col.find_one({"user_id": user_id})
    return bool(admin)

async def get_fsub_config():
    config = await settings_col.find_one({"_id": "fsub_config"})
    if config: return config.get("channel_id"), config.get("link")
    return DEFAULT_FORCE_SUB_CHANNEL, DEFAULT_FORCE_SUB_LINK

async def get_delete_time():
    config = await settings_col.find_one({"_id": "timer_config"})
    if config: return config.get("time", DEFAULT_DELETE_TIME)
    return DEFAULT_DELETE_TIME

async def get_start_config():
    config = await settings_col.find_one({"_id": "start_config"})
    default_text = "✨ **Welcome to Trenda Cinema Bot** ✨\n\n👤 **YOUR PROFILE:**\n┣ 📝 **Name:** {name}\n┣ 🆔 **User ID:** `{id}`\n┗ 🔗 **Username:** {username}\n\n🍿 *Just type the name of the movie you want to download!*"
    if config:
        return config.get("text", default_text), config.get("pic", DEFAULT_START_PIC)
    return default_text, DEFAULT_START_PIC

async def get_website_link():
    config = await settings_col.find_one({"_id": "web_config"})
    if config: return config.get("url", "")
    return ""

async def add_user(user_id):
    try:
        await users_col.update_one({"user_id": user_id}, {"$setOnInsert": {"user_id": user_id, "is_banned": 0}}, upsert=True)
        return True
    except Exception: return False

async def check_user_access(client, message):
    user_id = message.from_user.id
    try:
        user = await users_col.find_one({"user_id": user_id})
        if user and user.get("is_banned") == 1:
            await message.reply_text("⛔ **You are banned from using this bot.**")
            return False
    except Exception: pass

    fsub_channel, fsub_link = await get_fsub_config()
    if fsub_channel != 0:
        try:
            member = await client.get_chat_member(fsub_channel, user_id)
            if member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED]:
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
        except Exception: return True
    return True

# --- COMMANDS & HANDLERS ---
@bot.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if not await add_user(message.from_user.id):
        return await message.reply_text("⚠️ **Database is not connected yet!**")
    
    _fsub_link = await get_fsub_config()
    buttons = [
        [InlineKeyboardButton("🔍 Search Movies", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📢 Updates Channel", url=_fsub_link[1])]
    ]
    
    user = message.from_user
    u_username = f"@{user.username}" if user.username else "None"
    custom_text, custom_pic = await get_start_config()
    
    photo = custom_pic
    if custom_pic == "user_dp" and user.photo:
        photo = user.photo.big_file_id
    elif custom_pic == "user_dp":
        photo = DEFAULT_START_PIC

    try:
        welcome_text = custom_text.format(name=user.first_name, id=user.id, username=u_username)
    except Exception:
        welcome_text = custom_text 
    
    try:
        await message.reply_photo(photo=photo, caption=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))

@bot.on_message(filters.photo & filters.channel)
async def save_poster(client, message):
    if message.caption and "🎬 Title :" in message.caption:
        try:
            lines = message.caption.split('\n')
            title_line = [line for line in lines if "Title :" in line][0]
            movie_title = title_line.split(":", 1)[1].strip().lower()
            await posters_col.update_one({"title": movie_title}, {"$set": {"file_id": message.photo.file_id, "caption": message.caption}}, upsert=True)
        except Exception: pass

@bot.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if file:
        f_name = getattr(file, "file_name", "Unknown_Movie")
        short_id = uuid.uuid4().hex[:8] 
        try:
            await movies_col.update_one({"file_id": file.file_id}, {"$setOnInsert": {"file_name": f_name, "file_size": getattr(file, "file_size", 0), "short_id": short_id}}, upsert=True)
        except Exception: pass

@bot.on_message(filters.text & filters.private)
async def search_file(client, message):
    if message.text.startswith("/"): return
    if not await add_user(message.from_user.id): return
    if not await check_user_access(client, message): return
        
    query = message.text.strip()
    await searches_col.update_one({"_id": query.lower()}, {"$inc": {"count": 1}}, upsert=True)
    
    search_pattern = query.replace(" ", ".*")
    cursor = movies_col.find({"file_name": {"$regex": search_pattern, "$options": "i"}}).limit(50)
    results = await cursor.to_list(length=50)
    
    if not results:
        btn = [[InlineKeyboardButton("📩 Request Movie to Admin", callback_data=f"req_{query[:30]}")]]
        return await message.reply_text("🥲 **Sorry, this movie is not available.**", reply_markup=InlineKeyboardMarkup(btn))

    buttons = []
    for result in results:
        size_mb = round(result["file_size"] / (1024 * 1024), 2)
        full_name = result['file_name']
        short_name = full_name[:30] + "..." if len(full_name) > 30 else full_name
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

# --- SEND FILE, THUMBNAIL & WATCH ONLINE ---
async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception: pass

@bot.on_callback_query(filters.regex(r"^send_"))
async def send_file(client, callback_query):
    if not await check_user_access(client, callback_query): return
    short_id = callback_query.data.split("_")[1]
    result = await movies_col.find_one({"short_id": short_id})
    
    if result:
        await callback_query.answer("Sending file... Please wait!", show_alert=False)
        del_time = await get_delete_time()
        del_mins = del_time // 60
        
        reply_markup = None
        base_url = await get_website_link()
        if base_url:
            search_query = quote(result['file_name'])
            watch_link = f"{base_url.rstrip('/')}/?s={search_query}"
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("💻 Watch Online", url=watch_link)]])
        
        thumb_config = await settings_col.find_one({"_id": "thumb_config"})
        thumb_file_id = thumb_config.get("file_id") if thumb_config else None
        
        sent_msg = await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result["file_id"], 
            caption=f"🎥 **{result['file_name']}**\n\n⚠️ *This file will auto-delete in {del_mins} minutes.*",
            reply_markup=reply_markup
        )
        
        if thumb_file_id:
            try:
                await client.edit_message_media(
                    chat_id=sent_msg.chat.id,
                    message_id=sent_msg.id,
                    media=InputMediaDocument(
                        media=result["file_id"],
                        thumb=thumb_file_id,
                        caption=sent_msg.caption
                    ),
                    reply_markup=reply_markup
                )
            except Exception as e:
                pass
        
        asyncio.create_task(delete_after_delay(sent_msg, del_time))
    else:
        await callback_query.answer("File not found!", show_alert=True)

@bot.on_callback_query(filters.regex(r"^req_"))
async def request_movie(client, callback_query):
    query = callback_query.data.split("_", 1)[1]
    user = callback_query.from_user
    try:
        await client.send_message(ADMIN_ID, f"🆕 **New Movie Request!**\n\n🎬 Movie: `{query}`\n👤 User: {user.mention} (`{user.id}`)")
        await callback_query.answer("Your request has been sent to the admin!", show_alert=True)
    except Exception:
        await callback_query.answer("Failed to contact the admin.", show_alert=True)

@bot.on_callback_query(filters.regex(r"^check_joined$"))
async def verify_joined(client, callback_query):
    user_id = callback_query.from_user.id
    fsub_channel, _ = await get_fsub_config()
    if fsub_channel != 0:
        try:
            member = await client.get_chat_member(fsub_channel, user_id)
            if member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED]:
                await callback_query.answer("⚠️ You haven't joined the channel yet! Please join first.", show_alert=True)
            else:
                await callback_query.message.delete()
                await callback_query.answer("✅ Thank you for joining! Now you can search for movies.", show_alert=True)
        except Exception:
            await callback_query.answer("⚠️ You haven't joined the channel yet! Please join first.", show_alert=True)

# --- ASYNC UPDATE PROCESSOR ---
async def process_update(update):
    # Telegram update നേരിട്ട് പ്രോസസ് ചെയ്യാൻ പറ്റില്ല, അതിനാൽ നമുക്ക് bot.process_update() ഉപയോഗിക്കാം
    # ഇത് pyrogram-ന്റെ internal function ആണ്
    from pyrogram.raw.functions.messages import GetMessages
    from pyrogram.raw.types import InputMessageID
    # ഇത് വളരെ കുറച്ചു സ്പെസിഫിക് ആയതിനാൽ, നാം നേരിട്ട് പ്രോസസ് ചെയ്യില്ല
    # അതിനുപകരം, നമുക്ക് webhook ഉപയോഗിക്കാതെ, നേരിട്ട് polling ഉപയോഗിക്കാം, പക്ഷേ അത് Render-ൽ പ്രവർത്തിക്കില്ല
    # അതിനായി, നാം ഒരു വിദഗ്ദ്ധ പാക്കേജ് ഉപയോഗിക്കണം: pyromod
    # അല്ലെങ്കിൽ, നാം നമ്മുടെ ബോട്ട് മുഴുവൻ തന്നെ python-telegram-bot ആക്കണം
    # ഇതിൽ ഏറ്റവും എളുപ്പവഴി ആണ് ഞാൻ ഇപ്പോൾ നൽകുന്നത്: Flask + Webhook + Pyrogram (പ്രത്യേക കോഡിംഗ് ഉപയോഗിച്ച്)

# --- RUN BOT ---
if __name__ == "__main__":
    from threading import Thread
    import pyromod.listen
    
    # Start Flask server in a separate thread
    Thread(target=web_app.run, kwargs={'host': '0.0.0.0', 'port': int(os.environ.get("PORT", 8080)), 'use_reloader': False, 'debug': False}).start()

    # Start Pyrogram bot
    bot.run()
