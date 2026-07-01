import asyncio
import re
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot import app
from database import (
    ADMIN_ID,
    is_admin,
    get_fsub_config,
    get_delete_time,
    users_col,
    movies_col,
    posters_col,
    settings_col,
    admins_col,
    searches_col
)

# ================= ADMIN PANEL MAIN MENU =================

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if not await is_admin(message.from_user.id): 
        return
    
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


# ================= CALLBACK MENU NAVIGATOR =================

@app.on_callback_query(filters.regex(r"^menu_") | filters.regex(r"^close_panel") | filters.regex(r"^admin_home$"))
async def admin_menus(client, callback_query):
    if not await is_admin(callback_query.from_user.id): 
        return
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


# ================= CALLBACK ACTION HANDLERS =================

@app.on_callback_query(filters.regex(r"^admin_(stats|trend|fsub|timer|baninfo|bcinfo|delinfo|clear|confclear)$"))
async def admin_actions(client, callback_query):
    if not await is_admin(callback_query.from_user.id): 
        return
    action = callback_query.data.split("_")[1]
    
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_home")]])

    if action == "stats":
        u = await users_col.count_documents({}) if users_col is not None else 0
        m = await movies_col.count_documents({}) if movies_col is not None else 0
        p = await posters_col.count_documents({}) if posters_col is not None else 0
        await callback_query.message.edit_text(f"📊 **Bot Stats:**\n\n👥 Users: {u}\n🎬 Movies: {m}\n🖼️ Posters: {p}", reply_markup=back_btn)

    elif action == "trend":
        results = []
        if searches_col is not None:
            cursor = searches_col.find().sort("count", -1).limit(10)
            results = await cursor.to_list(length=10)
        text = "🔥 **Top 10 Trending Searches:**\n\n" if results else "No searches yet!"
        for idx, res in enumerate(results, 1): 
            text += f"{idx}. {res['_id'].title()} ({res['count']} searches)\n"
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
        if movies_col is not None:
            await movies_col.delete_many({})
        if posters_col is not None:
            await posters_col.delete_many({})
        await callback_query.message.edit_text("✅ Databases cleared successfully!", reply_markup=back_btn)


# ================= SETTINGS CONFIGURATION =================

@app.on_message(filters.command("setstarttext") & filters.private)
async def set_start_text(client, message):
    if not await is_admin(message.from_user.id): 
        return
    if len(message.command) < 2: 
        return await message.reply_text("Usage: `/setstarttext Welcome to bot...`")
    new_text = message.text.split(None, 1)[1]
    if settings_col is not None:
        await settings_col.update_one({"_id": "start_config"}, {"$set": {"text": new_text}}, upsert=True)
    await message.reply_text("✅ Start text updated successfully!")

@app.on_message(filters.command("setstartpic") & filters.private)
async def set_start_pic(client, message):
    if not await is_admin(message.from_user.id): 
        return
    pic_link = ""
    if message.reply_to_message and message.reply_to_message.photo:
        pic_link = message.reply_to_message.photo.file_id
    elif len(message.command) > 1:
        pic_link = message.command[1]
    else:
        return await message.reply_text("Reply to a photo with `/setstartpic` or provide a URL.")
    if settings_col is not None:
        await settings_col.update_one({"_id": "start_config"}, {"$set": {"pic": pic_link}}, upsert=True)
    await message.reply_text("✅ Custom Start Photo updated!")

@app.on_message(filters.command("usedp") & filters.private)
async def set_user_dp(client, message):
    if not await is_admin(message.from_user.id): 
        return
    if settings_col is not None:
        await settings_col.update_one({"_id": "start_config"}, {"$set": {"pic": "user_dp"}}, upsert=True)
    await message.reply_text("✅ Start photo is now set to User's Profile Picture (DP)!")

@app.on_message(filters.command("setwebsite") & filters.private)
async def set_website_url(client, message):
    if not await is_admin(message.from_user.id): 
        return
    if len(message.command) < 2: 
        return await message.reply_text("Usage: `/setwebsite https://yourwebsite.com`\n(Send `off` to disable Watch Online button)")
    
    url = message.command[1]
    if url.lower() == "off":
        if settings_col is not None:
            await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": ""}}, upsert=True)
        await message.reply_text("✅ Watch Online button Disabled.")
    else:
        if settings_col is not None:
            await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": url}}, upsert=True)
        await message.reply_text(f"✅ Website configured! Watch Online button will redirect to:\n`{url}/?s=MOVIE_NAME`")

@app.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_cmd(client, message):
    if not await is_admin(message.from_user.id): 
        return
    
    if message.reply_to_message and message.reply_to_message.photo:
        thumb_file_id = message.reply_to_message.photo.file_id
    elif len(message.command) > 1:
        thumb_file_id = message.command[1]
    else:
        return await message.reply_text("Usage: Reply to a photo with /setthumb or provide a photo URL.")
        
    if settings_col is not None:
        await settings_col.update_one({"_id": "thumb_config"}, {"$set": {"file_id": thumb_file_id}}, upsert=True)
    await message.reply_text("✅ File Thumbnail updated successfully!")


# ================= FORCE SUBSCRIBE CONFIGURATION =================

@app.on_message(filters.command("setchannel") & filters.private)
async def set_channel_id(client, message):
    if not await is_admin(message.from_user.id): 
        return
    try:
        new_id = int(message.command[1])
        if settings_col is not None:
            await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"channel_id": new_id}}, upsert=True)
        await message.reply_text(f"✅ FSub Channel ID set to: `{new_id}`")
    except Exception: 
        await message.reply_text("Usage: `/setchannel -100xxxxxxxx`")

@app.on_message(filters.command("setlink") & filters.private)
async def set_channel_link(client, message):
    if not await is_admin(message.from_user.id): 
        return
    try:
        new_link = message.command[1]
        if settings_col is not None:
            await settings_col.update_one({"_id": "fsub_config"}, {"$set": {"link": new_link}}, upsert=True)
        await message.reply_text(f"✅ FSub Link set to:\n{new_link}")
    except Exception: 
        await message.reply_text("Usage: `/setlink LINK`")


# ================= TIMER CONFIGURATION =================

@app.on_message(filters.command("settimer") & filters.private)
async def set_timer(client, message):
    if not await is_admin(message.from_user.id): 
        return
    try:
        t = int(message.command[1])
        if settings_col is not None:
            await settings_col.update_one({"_id": "timer_config"}, {"$set": {"time": t}}, upsert=True)
        await message.reply_text(f"✅ Auto-Delete timer updated to: `{t}` seconds.")
    except Exception: 
        await message.reply_text("Usage: `/settimer 300`")


# ================= USER & ADMIN MANAGEMENT =================

@app.on_message(filters.command("addadmin") & filters.private)
async def add_admin_cmd(client, message):
    if message.from_user.id != ADMIN_ID: 
        return
    try:
        uid = int(message.command[1])
        if admins_col is not None:
            await admins_col.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
        await message.reply_text(f"✅ User `{uid}` added as Admin.")
    except Exception: 
        await message.reply_text("Usage: `/addadmin USER_ID`")

@app.on_message(filters.command("removeadmin") & filters.private)
async def remove_admin_cmd(client, message):
    if message.from_user.id != ADMIN_ID: 
        return
    try:
        uid = int(message.command[1])
        if admins_col is not None:
            await admins_col.delete_one({"user_id": uid})
        await message.reply_text(f"❌ User `{uid}` removed from Admin.")
    except Exception: 
        await message.reply_text("Usage: `/removeadmin USER_ID`")

@app.on_message(filters.command("ban") & filters.private)
async def ban_user(client, message):
    if not await is_admin(message.from_user.id): 
        return
    try:
        target_id = int(message.command[1])
        if users_col is not None:
            await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 1}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` BANNED.")
    except Exception: 
        await message.reply_text("Usage: `/ban UserID`")

@app.on_message(filters.command("unban") & filters.private)
async def unban_user(client, message):
    if not await is_admin(message.from_user.id): 
        return
    try:
        target_id = int(message.command[1])
        if users_col is not None:
            await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 0}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` UNBANNED.")
    except Exception: 
        await message.reply_text("Usage: `/unban UserID`")


# ================= MOVIE DELETION =================

@app.on_message(filters.command("delmovie") & filters.private)
async def delete_movie(client, message):
    if not await is_admin(message.from_user.id): 
        return
    if len(message.command) < 2: 
        return await message.reply_text("⚠️ **Usage:** `/delmovie Movie Name`")
        
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
    
    text = f"✅ **Successfully Deleted!**\n\n🎬 Movie: `{query.title()}`\n📁 Files deleted: `{del_files_count}`\n🖼️ Poster deleted: `{"Yes" if del_poster_count > 0 else "No"}`"
    await message.reply_text(text)


# ================= ADVANCED BROADCAST SYSTEM =================

@app.on_message(filters.command("broadcast") & filters.private)
async def advanced_broadcast(client, message):
    if not await is_admin(message.from_user.id): 
        return
    
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
    if users_col is not None:
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
    else:
        await status_msg.edit_text("❌ Broadcast failed because the database is not initialized.")
