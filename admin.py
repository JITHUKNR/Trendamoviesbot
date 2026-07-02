import asyncio
import os
import sys
import re
from pyrogram import filters
from config import (
    app, ADMIN_ID, is_admin, get_fsub_config, get_delete_time,
    users_col, movies_col, posters_col, settings_col, admins_col, searches_col
)

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
    
    text = """
👑 **Trenda Bot Control Panel** 👑

**System Status:** `Online 🟢`
**Version:** `v3.0 (Rose UI)`
**Server:** `Render (Web)`

👋 Welcome Master! Select a module below to configure your bot:
"""
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
        text = "⚙️ **FULL BOT SETTINGS**\n\nConfigure bot appearance and behaviors:\n\n🖼 `/setstartpic [URL]` - Set Start Image\n📝 `/setstarttext [Text]` - Set Welcome Text\n🎭 `/setthumb [URL]` - Set Default Thumbnail\n⏱ `/settimer [Sec]` - Set Auto-Delete Time"
        buttons = [
            [InlineKeyboardButton("🎭 Thumbnail Manager", callback_data="admin_setthumb"), InlineKeyboardButton("⏱ Auto Delete Timer", callback_data="admin_timer")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_users":
        buttons = [
            [InlineKeyboardButton("🚫 Ban / Unban", callback_data="admin_baninfo"), InlineKeyboardButton("👑 Multiple Admins", callback_data="admin_roles")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("👥 **USER MANAGEMENT**\n\nManage users and assign admin roles.", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_movies":
        buttons = [
            [InlineKeyboardButton("🔥 Trending Searches", callback_data="admin_trend"), InlineKeyboardButton("❌ Delete Movie", callback_data="admin_delinfo")],
            [InlineKeyboardButton("📂 Categories", callback_data="admin_comingsoon"), InlineKeyboardButton("🤖 Auto Suggestions", callback_data="admin_comingsoon")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🎬 **MOVIE MANAGEMENT**\n\nControl movies, trends, and smart search features.", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_fsub":
        buttons = [[InlineKeyboardButton("⚙️ View Current FSub", callback_data="admin_fsub")], [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]]
        await callback_query.message.edit_text("🔐 **FORCE SUBSCRIBE MANAGER**\n\nUpdate using:\n`/setchannel -100xxxxxxxx`\n`/setlink https://t.me/...`", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_db":
        buttons = [
            [InlineKeyboardButton("💾 Backup / Restore", callback_data="admin_backup"), InlineKeyboardButton("🗑 Clear Database", callback_data="admin_clear")],
            [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🗑 **DATABASE MANAGER**\n\nManage MongoDB data, backups, and cleanups.", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_adv":
        buttons = [
            [InlineKeyboardButton("🔄 Restart Bot", callback_data="admin_restart"), InlineKeyboardButton("🟢 Maintenance Mode", callback_data="admin_maint")],
            [InlineKeyboardButton("📝 Logs Viewer", callback_data="admin_logs"), InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text("🛠 **ADVANCED TOOLS**\n\nSystem level configurations and server management.", reply_markup=InlineKeyboardMarkup(buttons))


@app.on_callback_query(filters.regex(r"^admin_(stats|trend|fsub|timer|baninfo|bcinfo|delinfo|setthumb|clear|confclear|webinfo|roles|comingsoon|restart|maint|backup|logs)$"))
async def admin_actions(client, callback_query):
    if not await is_admin(callback_query.from_user.id): return
    action = callback_query.data.split("_")[1]
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_home")]])

    if action == "stats":
        u = await users_col.count_documents({}) if users_col is not None else 0
        m = await movies_col.count_documents({}) if movies_col is not None else 0
        p = await posters_col.count_documents({}) if posters_col is not None else 0
        text = f"📈 **LIVE ANALYTICS & STATS:**\n\n👥 Total Users: `{u}`\n🎬 Total Movies: `{m}`\n🎭 Total Posters: `{p}`\n⚡ Fast Search: `Active`\n🌍 Language: `English/Malayalam`"
        await callback_query.message.edit_text(text, reply_markup=back_btn)
    
    elif action == "trend":
        results = await searches_col.find().sort("count", -1).limit(10).to_list(length=10) if searches_col is not None else []
        text = "🔥 **Top 10 Trending Searches:**\n\n" if results else "No searches yet!"
        for idx, res in enumerate(results, 1): text += f"{idx}. {res['_id'].title()} ({res['count']} searches)\n"
        await callback_query.message.edit_text(text, reply_markup=back_btn)
        
    elif action == "webinfo":
        await callback_query.message.edit_text("🌐 **Website Manager:**\n\nConnect a website for 'Watch Online' feature.\nUsage: `/setwebsite https://yourwebsite.com`\nTo Disable: `/setwebsite off`", reply_markup=back_btn)
        
    elif action == "roles":
        await callback_query.message.edit_text("👑 **Multiple Admin Roles:**\n\nAdd Admin: `/addadmin UserID`\nRemove Admin: `/removeadmin UserID`", reply_markup=back_btn)

    elif action == "fsub":
        f_id, f_link = await get_fsub_config()
        await callback_query.message.edit_text(f"⚙️ **Current FSub Config:**\n\nID: `{f_id}`\nLink: {f_link}", reply_markup=back_btn)
        
    elif action == "timer":
        t = await get_delete_time()
        await callback_query.message.edit_text(f"⏱️ **Auto-Delete Timer:** {t} seconds.\n\nChange using: `/settimer SECONDS`", reply_markup=back_btn)
        
    elif action == "baninfo":
        await callback_query.message.edit_text("🚫 **Ban / Unban:**\n`/ban UserID`\n`/unban UserID`", reply_markup=back_btn)
        
    elif action == "bcinfo":
        await callback_query.message.edit_text("📢 **Broadcast Panel:**\nReply to any message with `/broadcast`\n\nAdd inline buttons in message text like:\n`[Button Name | URL]`", reply_markup=back_btn)
        
    elif action == "delinfo":
        await callback_query.message.edit_text("❌ **Delete Movie:**\n`/delmovie Movie Name`", reply_markup=back_btn)
        
    elif action == "setthumb":
        await callback_query.message.edit_text("🖼️ **Set File Thumbnail:**\n\nReply to any photo with the command:\n`/setthumb`\n\nOr use:\n`/setthumb Photo_URL`", reply_markup=back_btn)
        
    elif action == "clear":
        buttons = [[InlineKeyboardButton("✅ Confirm Clear", callback_data="admin_confclear")], [InlineKeyboardButton("❌ Cancel", callback_data="admin_home")]]
        await callback_query.message.edit_text("⚠️ **Clear entirely all movies and posters?**", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif action == "confclear":
        if movies_col is not None: await movies_col.delete_many({})
        if posters_col is not None: await posters_col.delete_many({})
        await callback_query.message.edit_text("✅ Databases cleared successfully!", reply_markup=back_btn)
        
    elif action == "comingsoon":
        await callback_query.answer("🚀 This feature is coming in the next update!", show_alert=True)
        
    elif action == "restart":
        await callback_query.message.edit_text("🔄 **Restarting Bot...**\nPlease wait 10 seconds.")
        os.system("kill 1") 
        sys.exit(1)
        
    elif action == "maint":
        await callback_query.answer("🟢 Maintenance Mode will be active in v4.0", show_alert=True)
        
    elif action == "backup":
        await callback_query.answer("💾 MongoDB Auto-Backup is active in the cloud.", show_alert=True)
        
    elif action == "logs":
        await callback_query.message.edit_text("📝 **Logs Viewer:**\n\nPlease check your hosting server's Application Logs to view real-time live logs.", reply_markup=back_btn)


# ================= ⚙️ SETTINGS & MANAGEMENT COMMANDS =================

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
    if len(message.command) < 2: return await message.reply_text("Usage: `/setwebsite https://yourwebsite.com`\n(Send `off` to disable Watch Online button)")
    url = message.command[1]
    if url.lower() == "off":
        if settings_col is not None: await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": ""}}, upsert=True)
        await message.reply_text("✅ Watch Online button Disabled.")
    else:
        if settings_col is not None: await settings_col.update_one({"_id": "web_config"}, {"$set": {"url": url}}, upsert=True)
        await message.reply_text(f"✅ Website configured! Watch Online button will redirect to:\n`{url}/?s=MOVIE_NAME`")

@app.on_message(filters.command("setthumb") & filters.private)
async def set_thumb_cmd(client, message):
    if not await is_admin(message.from_user.id): return
    thumb_file_id = message.reply_to_message.photo.file_id if (message.reply_to_message and message.reply_to_message.photo) else (message.command[1] if len(message.command) > 1 else "")
    if not thumb_file_id: return await message.reply_text("Usage: Reply to a photo with /setthumb or provide a photo URL.")
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
        await message.reply_text(f"✅ Auto-Delete timer updated to: `{t}` seconds.")
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
    if len(message.command) < 2: return await message.reply_text("⚠️ **Usage:** `/delmovie Movie Name`")
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
    text = f"✅ **Successfully Deleted!**\n\n🎬 Movie: `{query.title()}`\n📁 Files deleted: `{del_files_count}`\n🖼️ Poster deleted: `{'Yes' if del_poster_count > 0 else 'No'}`"
    await message.reply_text(text)

@app.on_message(filters.command("broadcast") & filters.private)
async def advanced_broadcast(client, message):
    if not await is_admin(message.from_user.id): return
    if not message.reply_to_message:
        return await message.reply_text(
            "⚠️ **How to use /broadcast:**\n\nYou must reply to a message to send a broadcast.\n\n"
            "🔘 **Adding Inline Buttons:**\nTo add a button, include it at the bottom of your message in this format: `[Button Name | URL]`",
            disable_web_page_preview=True
        )
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
            except Exception: failed += 1
        await status_msg.edit_text(f"✅ **Broadcast Completed!**\n\n💚 Successful: {success}\n❤️ Failed/Blocked: {failed}")
    else:
        await status_msg.edit_text("❌ Broadcast failed because the database is not initialized.")
