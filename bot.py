import os
import asyncio
from threading import Thread
import certifi
import uuid
import re
from urllib.parse import quote
from flask import Flask

from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaDocument
from pyrogram.errors import UserNotParticipant

# ================= 🌐 WEB SERVER (For Render) =================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Trenda Bot is Running Successfully with Ultra Premium Features!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ================= ⚙️ CONFIGURATION =================
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
MONGO_URI = os.environ.get("MONGO_URI", "")

DEFAULT_FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", -1003903891234))
DEFAULT_FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/+57MfRxJ_0QdiZjRl")
DEFAULT_DELETE_TIME = 300
DEFAULT_START_PIC = "https://telegra.ph/file/0c320d759dc23bcbbbb9b.jpg"

# ================= 🗄 DATABASE SETUP =================
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
    print("⚠️ MONGO_URI missing!")
    movies_col = users_col = searches_col = posters_col = settings_col = admins_col = None

# ================= 🤖 BOT INSTANCE =================
app = Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


# ================= 🛠 DATABASE HELPERS =================
async def is_admin(user_id):
    if user_id == ADMIN_ID: return True
    if admins_col is not None:
        admin = await admins_col.find_one({"user_id": user_id})
        return bool(admin)
    return False

async def get_fsub_config():
    if settings_col is not None:
        config = await settings_col.find_one({"_id": "fsub_config"})
        if config: return config.get("channel_id"), config.get("link")
    return DEFAULT_FORCE_SUB_CHANNEL, DEFAULT_FORCE_SUB_LINK

async def get_delete_time():
    if settings_col is not None:
        config = await settings_col.find_one({"_id": "timer_config"})
        if config: return config.get("time", DEFAULT_DELETE_TIME)
    return DEFAULT_DELETE_TIME

async def get_start_config():
    default_text = "✨ **Welcome to Trenda Cinema Bot** ✨\n\n👤 **YOUR PROFILE:**\n┣ 📝 **Name:** {name}\n┣ 🆔 **User ID:** `{id}`\n┗ 🔗 **Username:** {username}\n\n🍿 *Just type the name of the movie you want to download!*"
    if settings_col is not None:
        config = await settings_col.find_one({"_id": "start_config"})
        if config:
            return config.get("text", default_text), config.get("pic", DEFAULT_START_PIC)
    return default_text, DEFAULT_START_PIC

async def get_website_link():
    if settings_col is not None:
        config = await settings_col.find_one({"_id": "web_config"})
        if config: return config.get("url", "")
    return ""

async def add_user(user_id):
    if users_col is not None:
        try:
            await users_col.update_one({"user_id": user_id}, {"$setOnInsert": {"user_id": user_id, "is_banned": 0}}, upsert=True)
            return True
        except Exception: return False
    return False

async def check_user_access(client, message):
    user_id = message.from_user.id
    if users_col is not None:
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
        except Exception: return True
    return True

# ================= 🚀 MAIN COMMANDS =================
@app.on_message(filters.command("start") & filters.private)
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


# ================= 👑 ROSE BOT STYLE ADMIN DASHBOARD =================
@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if not await is_admin(message.from_user.id): return
    buttons = [
        [InlineKeyboardButton("📊 Live Statistics", callback_data="admin_stats"), InlineKeyboardButton("⚙️ Bot Settings", callback_data="menu_bot")],
        [InlineKeyboardButton("🎬 Movie Management", callback_data="menu_movies"), InlineKeyboardButton("👥 User Management", callback_data="menu_users")],
        [InlineKeyboardButton("📢 Broadcast Panel", callback_data="admin_bcinfo"), InlineKeyboardButton("🔐 FSub Manager", callback_data="menu_fsub")],
        [InlineKeyboardButton("🌐 Website Manager", callback_data="admin_webinfo"), InlineKeyboardButton("🗑 Database Manager", callback_data="menu_db")],
        [InlineKeyboardButton("🛠 Advanced Tools", callback_data="menu_adv")],
        [InlineKeyboardButton("❌ Close Dashboard", callback_data="close_panel")]
    ]
    text = "👑 **Trenda Bot Control Panel** 👑\n\nSystem Status: `Online 🟢`\nVersion: `v3.0 (Rose UI)`\nServer: `Render (Web)`\n\n👋 Welcome Master! Select a module below to configure your bot:"
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^menu_") | filters.regex(r"^close_panel") | filters.regex(r"^admin_home$"))
async def admin_menus(client, callback_query):
    if not await is_admin(callback_query.from_user.id): return
    data = callback_query.data
    if data == "close_panel":
        return await callback_query.message.delete()
        
    elif data == "admin_home":
        buttons = [
            [InlineKeyboardButton("📊 Live Statistics", callback_data="admin_stats"), InlineKeyboardButton("⚙️ Bot Settings", callback_data="menu_bot")],
            [InlineKeyboardButton("🎬 Movie Management", callback_data="menu_movies"), InlineKeyboardButton("👥 User Management", callback_data="menu_users")],
            [InlineKeyboardButton("📢 Broadcast Panel", callback_data="admin_bcinfo"), InlineKeyboardButton("🔐 FSub Manager", callback_data="menu_fsub")],
            [InlineKeyboardButton("🌐 Website Manager", callback_data="admin_webinfo"), InlineKeyboardButton("🗑 Database Manager", callback_data="menu_db")],
            [InlineKeyboardButton("🛠 Advanced Tools", callback_data="menu_adv")],
            [InlineKeyboardButton("❌ Close Dashboard", callback_data="close_panel")]
        ]
        text = "👑 **Trenda Bot Control Panel** 👑\n\n👋 Welcome Master! Select a module below to configure your bot:"
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_bot":
        text = "⚙️ **FULL BOT SETTINGS**\n\n🖼 `/setstartpic [URL]`\n📝 `/setstarttext [Text]`\n🎭 `/setthumb [URL]`\n⏱ `/settimer [Sec]`"
        buttons = [[InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_users":
        buttons = [
            [InlineKeyboardButton("🚫 Ban / Unban", callback_data="admin_baninfo"), InlineKeyboardButton("👑 Multiple Admins", callback_data="admin_roles")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("👥 **USER MANAGEMENT**", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_movies":
        buttons = [
            [InlineKeyboardButton("🔥 Trending Searches", callback_data="admin_trend"), InlineKeyboardButton("❌ Delete Movie", callback_data="admin_delinfo")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🎬 **MOVIE MANAGEMENT**", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_fsub":
        buttons = [[InlineKeyboardButton("⚙️ View Current FSub", callback_data="admin_fsub")], [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]]
        await callback_query.message.edit_text("🔐 **FORCE SUBSCRIBE MANAGER**\n\n`/setchannel -100xxxxxxxx`\n`/setlink https://t.me/...`", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_db":
        buttons = [
            [InlineKeyboardButton("💾 Backup / Restore", callback_data="admin_backup"), InlineKeyboardButton("🗑 Clear Database", callback_data="admin_clear")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🗑 **DATABASE MANAGER**", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_adv":
        buttons = [
            [InlineKeyboardButton("🔄 Restart Bot", callback_data="admin_restart"), InlineKeyboardButton("📝 Logs Viewer", callback_data="admin_logs")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🛠 **ADVANCED TOOLS**", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^admin_(stats|trend|fsub|timer|baninfo|bcinfo|delinfo|setthumb|clear|confclear|webinfo|roles|restart|backup|logs)$"))
async def admin_actions(client, callback_query):
    if not await is_admin(callback_query.from_user.id): return
    action = callback_query.data.split("_")[1]
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_home")]])

    if action == "stats":
        u = await users_col.count_documents({}) if users_col is not None else 0
        m = await movies_col.count_documents({}) if movies_col is not None else 0
        p = await posters_col.count_documents({}) if posters_col is not None else 0
        text = f"📈 **LIVE ANALYTICS:**\n\n👥 Users: `{u}`\n🎬 Movies: `{m}`\n🎭 Posters: `{p}`"
        await callback_query.message.edit_text(text, reply_markup=back_btn)

    elif action == "trend":
        results = await searches_col.find().sort("count", -1).limit(10).to_list(length=10) if searches_col is not None else []
        text = "🔥 **Top 10 Trending:**\n\n" if results else "No searches yet!"
        for idx, res in enumerate(results, 1): text += f"{idx}. {res['_id'].title()} ({res['count']})\n"
        await callback_query.message.edit_text(text, reply_markup=back_btn)
        
    elif action == "fsub":
        f_id, f_link = await get_fsub_config()
        await callback_query.message.edit_text(f"⚙️ **FSub Config:**\n\nID: `{f_id}`\nLink: {f_link}", reply_markup=back_btn)
        
    elif action == "timer":
        t = await get_delete_time()
        await callback_query.message.edit_text(f"⏱️ **Timer:** {t} seconds.\n\nChange: `/settimer SECONDS`", reply_markup=back_btn)

    elif action == "webinfo":
        await callback_query.message.edit_text("🌐 **Website Manager:**\n\nConnect a website for 'Watch Online' feature.\nUsage: `/setwebsite https://yourwebsite.com`\nTo Disable: `/setwebsite off`", reply_markup=back_btn)
        
    elif action == "roles":
        await callback_query.message.edit_text("👑 **Multiple Admin Roles:**\n\nAdd Admin: `/addadmin UserID`\nRemove Admin: `/removeadmin UserID`", reply_markup=back_btn)
        
    elif action == "baninfo":
        await callback_query.message.edit_text("🚫 **Ban / Unban:**\n`/ban UserID`\n`/unban UserID`", reply_markup=back_btn)
        
    elif action == "bcinfo":
        await callback_query.message.edit_text("📢 **Broadcast Panel:**\nReply to any message with `/broadcast`\n\nAdd inline buttons in message text like:\n`[Button Name | URL]`", reply_markup=back_btn)
        
    elif action == "delinfo":
        await callback_query.message.edit_text("❌ **Delete Movie:**\n`/delmovie Movie Name`", reply_markup=back_btn)

    elif action == "clear":
        buttons = [[InlineKeyboardButton("✅ Confirm Clear", callback_data="admin_confclear")], [InlineKeyboardButton("❌ Cancel", callback_data="admin_home")]]
        await callback_query.message.edit_text("⚠️ **Clear all movies and posters?**", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif action == "confclear":
        if movies_col is not None: await movies_col.delete_many({})
        if posters_col is not None: await posters_col.delete_many({})
        await callback_query.message.edit_text("✅ Databases cleared!", reply_markup=back_btn)
        
    elif action == "restart":
        await callback_query.message.edit_text("🔄 **Restarting Bot...**")
        os.system("kill 1") 
        
    elif action == "backup":
        await callback_query.answer("💾 MongoDB Auto-Backup is active.", show_alert=True)
        
    elif action == "logs":
        await callback_query.message.edit_text("📝 **Logs:** Check Render Application Logs.", reply_markup=back_btn)

# ================= ⚙️ SETTINGS COMMANDS =================
@app.on_message(filters.command("setstarttext") & filters.private)
async def set_start_text(client, message):
    if not await is_admin(message.from_user.id): return
    if len(message.command) < 2: return await message.reply_text("Usage: `/setstarttext Welcome to bot...`")
    new_text = message.text.split(None, 1)[1]
    if settings_col is not None: await settings_col.update_one({"_id": "start_config"}, {"$set": {"text": new_text}}, upsert=True)
    await message.reply_text("✅ Start text updated successfully!")

@app.on_message(filters.command("setstartpic") & filters.private)
async def set_start_pic(client, message):
    if not await is_admin(message.from_user.id): return
    pic_link = message.reply_to_message.photo.file_id if (message.reply_to_message and message.reply_to_message.photo) else (message.command[1] if len(message.command) > 1 else "")
    if not pic_link: return await message.reply_text("Reply to a photo with `/setstartpic` or provide a URL.")
    if settings_col is not None: await settings_col.update_one({"_id": "start_config"}, {"$set": {"pic": pic_link}}, upsert=True)
    await message.reply_text("✅ Custom Start Photo updated!")

@app.on_message(filters.command("usedp") & filters.private)
async def set_user_dp(client, message):
    if not await is_admin(message.from_user.id): return
    if settings_col is not None: await settings_col.update_one({"_id": "start_config"}, {"$set": {"pic": "user_dp"}}, upsert=True)
    await message.reply_text("✅ Start photo is now set to User's Profile Picture (DP)!")

@app.on_message(filters.command("setwebsite") & filters.private)
async def set_website_url(client, message):
    if not await is_admin(message.from_user.id): return
    if len(message.command) < 2: return await message.reply_text("Usage: `/setwebsite https://yourwebsite.com`\n(Send `off` to disable)")
    url = message.command[1]
    if url.lower() == "off":
        if settings_col is not None: await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": ""}}, upsert=True)
        await message.reply_text("✅ Watch Online button Disabled.")
    else:
        if settings_col is not None: await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": url}}, upsert=True)
        await message.reply_text(f"✅ Website configured! Link:\n`{url}/?s=MOVIE_NAME`")

@app.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    thumb_file_id = message.reply_to_message.photo.file_id if (message.reply_to_message and message.reply_to_message.photo) else (message.command[1] if len(message.command) > 1 else "")
    if not thumb_file_id: return await message.reply_text("Usage: Reply to a photo with /setthumb or provide a URL.")
    if settings_col is not None: await settings_col.update_one({"_id": "thumb_config"}, {"$set": {"file_id": thumb_file_id}}, upsert=True)
    await message.reply_text("✅ File Thumbnail updated successfully!")

@app.on_message(filters.command("setchannel") & filters.private)
async def set_channel_id(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        new_id = int(message.command[1])
        if settings_col is not None: await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"channel_id": new_id}}, upsert=True)
        await message.reply_text(f"✅ FSub Channel ID set to: `{new_id}`")
    except Exception: await message.reply_text("Usage: `/setchannel -100xxxxxxxx`")

@app.on_message(filters.command("setlink") & filters.private)
async def set_channel_link(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        new_link = message.command[1]
        if settings_col is not None: await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"link": new_link}}, upsert=True)
        await message.reply_text(f"✅ FSub Link set to:\n{new_link}")
    except Exception: await message.reply_text("Usage: `/setlink LINK`")

@app.on_message(filters.command("settimer") & filters.private)
async def set_timer(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        t = int(message.command[1])
        if settings_col is not None: await settings_col.update_one({"_id": "timer_config"}, {"$set": {"time": t}}, upsert=True)
        await message.reply_text(f"✅ Timer updated to: `{t}` seconds.")
    except Exception: await message.reply_text("Usage: `/settimer 300`")

@app.on_message(filters.command("addadmin") & filters.private)
async def add_admin_cmd(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.command[1])
        if admins_col is not None: await admins_col.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
        await message.reply_text(f"✅ User `{uid}` added as Admin.")
    except Exception: await message.reply_text("Usage: `/addadmin USER_ID`")

@app.on_message(filters.command("removeadmin") & filters.private)
async def remove_admin_cmd(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        uid = int(message.command[1])
        if admins_col is not None: await admins_col.delete_one({"user_id": uid})
        await message.reply_text(f"❌ User `{uid}` removed from Admin.")
    except Exception: await message.reply_text("Usage: `/removeadmin USER_ID`")

@app.on_message(filters.command("ban") & filters.private)
async def ban_user(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        target_id = int(message.command[1])
        if users_col is not None: await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 1}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` BANNED.")
    except Exception: await message.reply_text("Usage: `/ban UserID`")

@app.on_message(filters.command("unban") & filters.private)
async def unban_user(client, message):
    if not await is_admin(message.from_user.id): return
    try:
        target_id = int(message.command[1])
        if users_col is not None: await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 0}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` UNBANNED.")
    except Exception: await message.reply_text("Usage: `/unban UserID`")

@app.on_message(filters.command("delmovie") & filters.private)
async def delete_movie(client, message):
    if not await is_admin(message.from_user.id): return
    if len(message.command) < 2: return await message.reply_text("⚠️ Usage: `/delmovie Movie Name`")
    query = message.text.split(" ", 1)[1].strip().lower()
    search_pattern = query.replace(" ", ".*")
    del_files_count = 0
    del_poster_count = 0
    if movies_col is not None:
        del_files = await movies_col.delete_many({"file_name": {"$regex": search_pattern, "$options": "i"}})
        del_files_count = del_files.deleted_count
    if posters_col is not None:
        del_poster = await posters_col.delete_one({"title": query})
        del_poster_count = del_poster.deleted_count
    
    poster_status = 'Yes' if del_poster_count > 0 else 'No'
    text = f"✅ Successfully Deleted!\n\n🎬 Movie: `{query.title()}`\n📁 Files deleted: `{del_files_count}`\n🖼️ Poster deleted: `{poster_status}`"
    await message.reply_text(text)

@app.on_message(filters.command("broadcast") & filters.private)
async def advanced_broadcast(client, message):
    if not await is_admin(message.from_user.id): return
    if not message.reply_to_message:
        return await message.reply_text("⚠️ Reply to a message with `/broadcast`")
    
    reply_msg = message.reply_to_message
    status_msg = await message.reply_text("📢 Broadcast Started...")
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
    if users_col is not None:
        async for user in users_col.find({}):
            try:
                if reply_msg.media:
                    await reply_msg.copy(chat_id=user["user_id"], caption=clean_text if buttons else reply_msg.caption, reply_markup=markup)
                else:
                    await client.send_message(chat_id=user["user_id"], text=clean_text if buttons else reply_msg.text, reply_markup=markup)
                success += 1
                await asyncio.sleep(0.05) 
            except Exception: failed += 1
        await status_msg.edit_text(f"✅ **Broadcast Completed!**\n\n💚 Success: {success}\n❤️ Failed: {failed}")
    else:
        await status_msg.edit_text("❌ Database not initialized.")


# ================= 🚀 SEARCH & SAVE LOGIC =================
@app.on_message(filters.photo & filters.channel)
async def save_poster(client, message):
    if posters_col is not None and message.caption and "🎬 Title :" in message.caption:
        try:
            lines = message.caption.split('\n')
            title_line = [line for line in lines if "Title :" in line][0]
            movie_title = title_line.split(":", 1)[1].strip().lower()
            await posters_col.update_one({"title": movie_title}, {"$set": {"file_id": message.photo.file_id, "caption": message.caption}}, upsert=True)
        except Exception: pass

@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if movies_col is not None and file:
        f_name = getattr(file, "file_name", "Unknown_Movie")
        short_id = uuid.uuid4().hex[:8] 
        try:
            await movies_col.update_one({"file_id": file.file_id}, {"$setOnInsert": {"file_name": f_name, "file_size": getattr(file, "file_size", 0), "short_id": short_id}}, upsert=True)
        except Exception: pass

@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    if message.text.startswith("/"): return
    if not await add_user(message.from_user.id): return
    if not await check_user_access(client, message): return
        
    query = message.text.strip()
    if searches_col is not None:
        await searches_col.update_one({"_id": query.lower()}, {"$inc": {"count": 1}}, upsert=True)
    
    search_pattern = query.replace(" ", ".*")
    if movies_col is not None:
        cursor = movies_col.find({"file_name": {"$regex": search_pattern, "$options": "i"}}).limit(50)
        results = await cursor.to_list(length=50)
    else:
        results = []
    
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

    poster = await posters_col.find_one({"title": query.lower()}) if posters_col is not None else None
    if poster:
        final_caption = poster["caption"] + "\n\n👇 **Choose Quality to Download:**"
        try:
            await message.reply_photo(photo=poster["file_id"], caption=final_caption, reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await message.reply_text(final_caption, reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await message.reply_text("🍿 **Here are your search results:**", reply_markup=InlineKeyboardMarkup(buttons))

async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception: pass

@app.on_callback_query(filters.regex(r"^send_"))
async def send_file(client, callback_query):
    if not await check_user_access(client, callback_query): return
    short_id = callback_query.data.split("_")[1]
    
    result = await movies_col.find_one({"short_id": short_id}) if movies_col is not None else None
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
        
        thumb_file_id = None
        if settings_col is not None:
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
            except Exception: pass
        
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

# ================= 🚀 FINAL STARTUP =================
if __name__ == "__main__":
    Thread(target=run_server, daemon=True).start()
    print("✅ Web Server & Bot Engine Started Successfully!", flush=True)
    app.run()
