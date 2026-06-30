import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import uuid
import certifi
import re
from pyrogram import Client, filters, enums
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
    print("⚠️ WARNING: MONGO_URI is not set!", flush=True)


# ================= DATABASE HELPERS (ZERO-CODE CONTROL) =================

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
    
    # 1. Ban Check
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
        except Exception: 
            # ഇവിടെയാണ് നമ്മൾ പുതിയ "I Have Joined" ബട്ടൺ കൊടുക്കുന്നത്
            btn = [
                [InlineKeyboardButton("📢 Join Our Channel", url=fsub_link)],
                [InlineKeyboardButton("🔄 I Have Joined", callback_data="check_joined")]
            ]
            error_msg = (
                "⚠️ **Please join our main channel to use this bot and download movies!**\n\n"
                "Click the button below to join, then click 'I Have Joined'."
            )
            try:
                _, custom_pic = await get_start_config()
                pic_to_send = custom_pic if custom_pic != "user_dp" else DEFAULT_START_PIC
                await message.reply_photo(photo=pic_to_send, caption=error_msg, reply_markup=InlineKeyboardMarkup(btn))
            except Exception:
                await message.reply_text(error_msg, reply_markup=InlineKeyboardMarkup(btn))
            return False 
            
    return True


# ================= START COMMAND =================

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    if not await add_user(message.from_user.id):
        await message.reply_text("⚠️ **Database is not connected yet!**")
        return
    
    _fsub_link = await get_fsub_config()
    buttons = [
        [InlineKeyboardButton("🔍 Search Movies", switch_inline_query_current_chat="")],
        [InlineKeyboardButton("📢 Updates Channel", url=_fsub_link[1])]
    ]
    
    user = message.from_user
    u_name = user.first_name
    u_id = user.id
    u_username = f"@{user.username}" if user.username else "None"
    
    # ഡാറ്റാബേസിൽ നിന്ന് കസ്റ്റം സെറ്റിംഗ്സ് എടുക്കുന്നു
    custom_text, custom_pic = await get_start_config()
    
    # User DP വേണോ അതോ custom pic വേണോ എന്ന് നോക്കുന്നു
    photo = custom_pic
    if custom_pic == "user_dp" and user.photo:
        photo = user.photo.big_file_id
    elif custom_pic == "user_dp":
        photo = DEFAULT_START_PIC

    # പ്ലേസ്ഹോൾഡറുകൾ മാറ്റുന്നു ({name}, {id} etc)
    try:
        welcome_text = custom_text.format(name=u_name, id=u_id, username=u_username)
    except Exception:
        welcome_text = custom_text # ഫോർമാറ്റ് തെറ്റിയാൽ ഉള്ളത് പോലെ കാണിക്കാൻ
    
    try:
        await message.reply_photo(photo=photo, caption=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))
    except Exception:
        await message.reply_text(text=welcome_text, reply_markup=InlineKeyboardMarkup(buttons))


# ================= ULTRA PROFESSIONAL ADMIN PANEL =================

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if not await is_admin(message.from_user.id): return
    
    buttons = [
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="menu_bot"),
         InlineKeyboardButton("👥 Users & Broadcast", callback_data="menu_users")],
        [InlineKeyboardButton("🎬 Movie & Database", callback_data="menu_movies"),
         InlineKeyboardButton("🔐 FSub & Security", callback_data="menu_fsub")],
        [InlineKeyboardButton("👑 Admin Management", callback_data="menu_admins")],
        [InlineKeyboardButton("❌ Close Panel", callback_data="close_panel")]
    ]
    
    text = "👨‍💻 **ULTRA PREMIUM ADMIN PANEL**\n\nWelcome Master! 👑\nSelect a category below to control your bot completely:"
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^menu_") | filters.regex(r"^close_panel") | filters.regex(r"^admin_home$"))
async def admin_menus(client, callback_query):
    if not await is_admin(callback_query.from_user.id): return
    data = callback_query.data

    if data == "close_panel":
        await callback_query.message.delete()
        return
        
    elif data == "admin_home":
        buttons = [
            [InlineKeyboardButton("⚙️ Bot Settings", callback_data="menu_bot"), InlineKeyboardButton("👥 Users & Broadcast", callback_data="menu_users")],
            [InlineKeyboardButton("🎬 Movie & Database", callback_data="menu_movies"), InlineKeyboardButton("🔐 FSub & Security", callback_data="menu_fsub")],
            [InlineKeyboardButton("👑 Admin Management", callback_data="menu_admins")],
            [InlineKeyboardButton("❌ Close", callback_data="close_panel")]
        ]
        await callback_query.message.edit_text("👨‍💻 **ULTRA PREMIUM ADMIN PANEL**\n\nWelcome Master! 👑\nSelect a category below:", reply_markup=InlineKeyboardMarkup(buttons))

        elif data == "menu_bot":
        text = "⚙️ **BOT SETTINGS**\n\n**Commands to update:**\n1. `/setstarttext [Your Text]`\n2. `/setstartpic [Link]`\n3. `/setwebsite [URL]`\n4. `/setthumb` (To Set File Thumbnail)"
        buttons = [
            [InlineKeyboardButton("🖼️ Set File Thumbnail", callback_data="admin_setthumb")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_users":
        buttons = [
            [InlineKeyboardButton("📊 User Stats", callback_data="admin_stats"), InlineKeyboardButton("📢 Broadcast Info", callback_data="admin_bcinfo")],
            [InlineKeyboardButton("🚫 Ban Info", callback_data="admin_baninfo")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("👥 **USERS & BROADCAST**\n\nManage users and send messages:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_movies":
        buttons = [
            [InlineKeyboardButton("⏱️ Auto-Delete Timer", callback_data="admin_timer"), InlineKeyboardButton("🔥 Trending", callback_data="admin_trend")],
            [InlineKeyboardButton("❌ Delete Movie", callback_data="admin_delinfo"), InlineKeyboardButton("🗑️ Clear DB", callback_data="admin_clear")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🎬 **MOVIE & DATABASE**\n\nControl files, timers, and storage:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_fsub":
        buttons = [
            [InlineKeyboardButton("⚙️ View Current FSub", callback_data="admin_fsub")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🔐 **FSUB & SECURITY**\n\nTo change FSub use these commands:\n`/setchannel -100xxxxxxxx`\n`/setlink https://t.me/...`", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_admins":
        buttons = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="admin_home")]]
        await callback_query.message.edit_text("👑 **ADMIN MANAGEMENT**\n\nAdd/Remove admins using:\n`/addadmin USER_ID`\n`/removeadmin USER_ID`", reply_markup=InlineKeyboardMarkup(buttons))


# --- Admin Action Callbacks (Stats, Timers etc) ---
@app.on_callback_query(filters.regex(r"^admin_(stats|trend|fsub|timer|baninfo|bcinfo|delinfo|clear|confclear)$"))
async def admin_actions(client, callback_query):
    if not await is_admin(callback_query.from_user.id): return
    action = callback_query.data.split("_")[1]
    
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_home")]])

    if action == "stats":
        u = await users_col.count_documents({})
        m = await movies_col.count_documents({})
        p = await posters_col.count_documents({})
        await callback_query.message.edit_text(f"📊 **Bot Stats:**\n\n👥 Users: {u}\n🎬 Movies: {m}\n🖼️ Posters: {p}", reply_markup=back_btn)

    elif action == "trend":
        cursor = searches_col.find().sort("count", -1).limit(10)
        results = await cursor.to_list(length=10)
        text = "🔥 **Top 10 Trending Searches:**\n\n" if results else "No searches yet!"
        for idx, res in enumerate(results, 1): text += f"{idx}. {res['_id'].title()} ({res['count']} searches)\n"
        await callback_query.message.edit_text(text, reply_markup=back_btn)

    elif action == "fsub":
        f_id, f_link = await get_fsub_config()
        await callback_query.message.edit_text(f"⚙️ **Current FSub Config:**\n\nID: `{f_id}`\nLink: {f_link}", reply_markup=back_btn)

    elif action == "timer":
        t = await get_delete_time()
        await callback_query.message.edit_text(f"⏱️ **Auto-Delete Timer:** {t} seconds.\n\nChange using: `/settimer SECONDS`", reply_markup=back_btn)

    elif action == "baninfo":
        await callback_query.message.edit_text("🚫 **Ban / Unban:**\n`/ban UserID`\n`/unban UserID`", reply_markup=back_btn)
        
    elif action == "bcinfo":
        await callback_query.message.edit_text("📢 **Broadcast:**\nReply to any message with `/broadcast`\n\nAdd inline buttons in message text like:\n`[Button Name | URL]`", reply_markup=back_btn)
        
    elif action == "delinfo":
        await callback_query.message.edit_text("❌ **Delete Movie:**\n`/delmovie Movie Name`", reply_markup=back_btn)

    elif action == "clear":
        buttons = [[InlineKeyboardButton("✅ Confirm Clear", callback_data="admin_confclear")], [InlineKeyboardButton("❌ Cancel", callback_data="admin_home")]]
        await callback_query.message.edit_text("⚠️ **Clear entirely all movies and posters?**", reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "confclear":
        await movies_col.delete_many({})
        await posters_col.delete_many({})
        await callback_query.message.edit_text("✅ Databases cleared successfully!", reply_markup=back_btn)


# ================= ZERO-CODE SETTING COMMANDS =================

@app.on_message(filters.command("setstarttext") & filters.private)
async def set_start_text(client, message):
    if not await is_admin(message.from_user.id): return
    if len(message.command) < 2: return await message.reply_text("Usage: `/setstarttext Welcome to bot...`")
    new_text = message.text.split(None, 1)[1]
    await settings_col.update_one({"_id": "start_config"}, {"$set": {"text": new_text}}, upsert=True)
    await message.reply_text("✅ Start text updated successfully!")

@app.on_message(filters.command("setstartpic") & filters.private)
async def set_start_pic(client, message):
    if not await is_admin(message.from_user.id): return
    pic_link = ""
    if message.reply_to_message and message.reply_to_message.photo:
        pic_link = message.reply_to_message.photo.file_id
    elif len(message.command) > 1:
        pic_link = message.command[1]
    else:
        return await message.reply_text("Reply to a photo with `/setstartpic` or provide a URL.")
    await settings_col.update_one({"_id": "start_config"}, {"$set": {"pic": pic_link}}, upsert=True)
    await message.reply_text("✅ Custom Start Photo updated!")

@app.on_message(filters.command("usedp") & filters.private)
async def set_user_dp(client, message):
    if not await is_admin(message.from_user.id): return
    await settings_col.update_one({"_id": "start_config"}, {"$set": {"pic": "user_dp"}}, upsert=True)
    await message.reply_text("✅ Start photo is now set to User's Profile Picture (DP)!")

@app.on_message(filters.command("setwebsite") & filters.private)
async def set_website_url(client, message):
    if not await is_admin(message.from_user.id): return
    if len(message.command) < 2: 
        return await message.reply_text("Usage: `/setwebsite https://yourwebsite.com`\n(Send `off` to disable Watch Online button)")
    
    url = message.command[1]
    if url.lower() == "off":
        await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": ""}}, upsert=True)
        await message.reply_text("✅ Watch Online button Disabled.")
    else:
        await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": url}}, upsert=True)
        await message.reply_text(f"✅ Website configured! Watch Online button will redirect to:\n`{url}/?s=MOVIE_NAME`")
        # ================= SET FILE THUMBNAIL LOGIC =================

@app.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    
    # ഫോട്ടോ റിപ്ലൈ ആയിട്ടോ അല്ലെങ്കിൽ ലിങ്ക് ആയിട്ടോ നൽകാം
    if message.reply_to_message and message.reply_to_message.photo:
        thumb_file_id = message.reply_to_message.photo.file_id
    elif len(message.command) > 1:
        # യുസർ ലിങ്ക് ആണ് അയക്കുന്നതെങ്കിൽ
        thumb_file_id = message.command[1]
    else:
        return await message.reply_text("Usage: Reply to a photo with /setthumb or provide a photo URL.")
        
    # ഡാറ്റാബേസിൽ സേവ് ചെയ്യുന്നു
    await settings_col.update_one({"_id": "thumb_config"}, {"$set": {"file_id": thumb_file_id}}, upsert=True)
    await message.reply_text("✅ File Thumbnail updated successfully!")

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


# --- User Management Commands ---
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


# ================= MOVIE MANAGEMENT =================

@app.on_message(filters.command("delmovie") & filters.private)
async def delete_movie(client, message):
    if not await is_admin(message.from_user.id): return
    if len(message.command) < 2: return await message.reply_text("⚠️ **Usage:** `/delmovie Movie Name`")
        
    query = message.text.split(" ", 1)[1].strip().lower()
    search_pattern = query.replace(" ", ".*")
    
    del_files = await movies_col.delete_many({"file_name": {"$regex": search_pattern, "$options": "i"}})
    del_poster = await posters_col.delete_one({"title": query})
    
    text = f"✅ **Successfully Deleted!**\n\n🎬 Movie: `{query.title()}`\n📁 Files deleted: `{del_files.deleted_count}`\n🖼️ Poster deleted: `{'Yes' if del_poster.deleted_count > 0 else 'No'}`"
    await message.reply_text(text)


# ================= ADVANCED COPY-BROADCAST SYSTEM =================
# Bug Fixed & Indentation Corrected

@app.on_message(filters.command("broadcast") & filters.private)
async def advanced_broadcast(client, message):
    if not await is_admin(message.from_user.id): return
    
    if not message.reply_to_message:
        await message.reply_text(
            "⚠️ **How to use /broadcast:**\n\n"
            "You must reply to a message to send a broadcast.\n\n"
            "🔘 **Adding Inline Buttons:**\n"
            "To add a button, include it at the bottom of your message in this format: `[Button Name | URL]`\n\n"
            "📝 **Example:**\n"
            "NEW MOVIE 🍿\n\n"
            "[JOIN CHANNEL | https://t.me/yourchannel]",
            disable_web_page_preview=True
        )
        return

    reply_msg = message.reply_to_message
    status_msg = await message.reply_text("📢 **Advanced Broadcast Started...**")
    
    raw_text = reply_msg.text or reply_msg.caption or ""
    clean_text = raw_text
    buttons = []
    
    matches = re.finditer(r'\[([^|]+)\|([^\]]+)\]', raw_text)
    for match in matches:
        btn_text = match.group(1).strip()
        btn_url = match.group(2).strip()
        buttons.append([InlineKeyboardButton(btn_text, url=btn_url)])
        clean_text = clean_text.replace(match.group(0), "")
    
    clean_text = clean_text.strip()
    markup = InlineKeyboardMarkup(buttons) if buttons else reply_msg.reply_markup

    success, failed = 0, 0
    async for user in users_col.find({}):
        try:
            if reply_msg.media:
                await reply_msg.copy(chat_id=user["user_id"], caption=clean_text if buttons else reply_msg.caption, reply_markup=markup)
            else:
                await client.send_message(chat_id=user["user_id"], text=clean_text if buttons else reply_msg.text, reply_markup=markup)
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
    if not await check_user_access(client, message): return
        
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
        max_length = 30
        short_name = full_name[:max_length] + "..." if len(full_name) > max_length else full_name
        
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
    result = await movies_col.find_one({"short_id": short_id})
    
    if result:
        await callback_query.answer("Sending file... Please wait!", show_alert=False)
        del_time = await get_delete_time()
        del_mins = del_time // 60
        
        # --- WATCH ONLINE BUTTON LOGIC ---
        reply_markup = None
        base_url = await get_website_link()
        if base_url:
            # വെബ്സൈറ്റ് ലിങ്കിനൊപ്പം സിനിമയുടെ പേര് ചേർക്കുന്നു
            search_query = quote(result['file_name'])
            watch_link = f"{base_url.rstrip('/')}/?s={search_query}"
            btn = [[InlineKeyboardButton("💻 Watch Online", url=watch_link)]]
            reply_markup = InlineKeyboardMarkup(btn)
        
                # --- NEW: CUSTOM THUMBNAIL LOGIC ---
        thumb_config = await settings_col.find_one({"_id": "thumb_config"})
        thumb_file_id = thumb_config.get("file_id") if thumb_config else None
        
        sent_msg = await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result["file_id"], 
            caption=f"🎥 **{result['file_name']}**\n\n⚠️ *This file will auto-delete in {del_mins} minutes.*",
            reply_markup=reply_markup,
            thumb=thumb_file_id
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

print("Bot started successfully with ULTRA PREMIUM Features & Watch Online!", flush=True)
# ================= CHECK JOINED BUTTON LOGIC =================
@app.on_callback_query(filters.regex(r"^check_joined$"))
async def verify_joined(client, callback_query):
    user_id = callback_query.from_user.id
    fsub_channel, _ = await get_fsub_config()
    
    if fsub_channel != 0:
        try:
            member = await client.get_chat_member(fsub_channel, user_id)
            if member.status in [enums.ChatMemberStatus.BANNED, enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.RESTRICTED]:
                # ജോയിൻ ചെയ്തിട്ടില്ലെങ്കിൽ സ്ക്രീനിൽ കാണിക്കുന്ന വാണിംഗ്
                await callback_query.answer("⚠️ You haven't joined the channel yet! Please join first.", show_alert=True)
            else:
                # ജോയിൻ ചെയ്തിട്ടുണ്ടെങ്കിൽ ആ മെസ്സേജ് ഡിലീറ്റ് ആകുന്നു!
                await callback_query.message.delete()
                await callback_query.answer("✅ Thank you for joining! Now you can search for movies.", show_alert=True)
        except Exception:
            await callback_query.answer("⚠️ You haven't joined the channel yet! Please join first.", show_alert=True)

app.run()
