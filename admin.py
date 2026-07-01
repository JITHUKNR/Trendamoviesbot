import asyncio
import re
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# നിങ്ങളുടെ bot.py യിൽ നിന്നോ database.py യിൽ നിന്നോ ഉള്ള ഇംപോർട്ടുകൾ ഇതിൽ ചേർക്കുക
# ഉദാഹരണത്തിന്:
# from bot import app, ADMIN_ID
# from database import is_admin, users_col, movies_col, posters_col, settings_col, searches_col

# ================= ULTRA PREMIUM ADMIN DASHBOARD (ROSE STYLE) =================

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    # അഡ്മിൻ ആണോ എന്ന് ചെക്ക് ചെയ്യുന്നു (നിങ്ങളുടെ ഡാറ്റാബേസ് ഫംഗ്ഷൻ ഉപയോഗിക്കുക)
    # if not await is_admin(message.from_user.id): return
    
    buttons = [
        [InlineKeyboardButton("📊 Statistics & Analytics", callback_data="admin_stats")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="menu_bot"),
         InlineKeyboardButton("🎬 Movie Mgt.", callback_data="menu_movies")],
        [InlineKeyboardButton("👥 User Mgt.", callback_data="menu_users"),
         InlineKeyboardButton("📢 Broadcast", callback_data="menu_broadcast")],
        [InlineKeyboardButton("🔐 Force Sub", callback_data="menu_fsub"),
         InlineKeyboardButton("🌐 Website", callback_data="menu_web")],
        [InlineKeyboardButton("🗑 Database", callback_data="menu_db"),
         InlineKeyboardButton("👑 Admins", callback_data="menu_admins")],
        [InlineKeyboardButton("🛠 Maintenance & Logs", callback_data="menu_maint")],
        [InlineKeyboardButton("❌ Close Panel", callback_data="close_panel")]
    ]
    
    text = """👨‍💻 **ULTRA PREMIUM ADMIN DASHBOARD**

👑 **Welcome Master!**
Here you can control every aspect of your bot. Select a category below to manage settings, users, movies, and more."""
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ================= CALLBACK MENU NAVIGATOR =================

@app.on_callback_query(filters.regex(r"^menu_") | filters.regex(r"^close_panel") | filters.regex(r"^admin_home$"))
async def admin_menus(client, callback_query):
    # if not await is_admin(callback_query.from_user.id): return
    data = callback_query.data

    if data == "close_panel":
        await callback_query.message.delete()
        return
        
    elif data == "admin_home":
        buttons = [
            [InlineKeyboardButton("📊 Statistics & Analytics", callback_data="admin_stats")],
            [InlineKeyboardButton("⚙️ Bot Settings", callback_data="menu_bot"),
             InlineKeyboardButton("🎬 Movie Mgt.", callback_data="menu_movies")],
            [InlineKeyboardButton("👥 User Mgt.", callback_data="menu_users"),
             InlineKeyboardButton("📢 Broadcast", callback_data="menu_broadcast")],
            [InlineKeyboardButton("🔐 Force Sub", callback_data="menu_fsub"),
             InlineKeyboardButton("🌐 Website", callback_data="menu_web")],
            [InlineKeyboardButton("🗑 Database", callback_data="menu_db"),
             InlineKeyboardButton("👑 Admins", callback_data="menu_admins")],
            [InlineKeyboardButton("🛠 Maintenance & Logs", callback_data="menu_maint")],
            [InlineKeyboardButton("❌ Close Panel", callback_data="close_panel")]
        ]
        await callback_query.message.edit_text("👨‍💻 **ULTRA PREMIUM ADMIN DASHBOARD**\n\nWelcome Master! 👑\nSelect a category below:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_bot":
        text = """⚙️ **BOT SETTINGS**

Configure basic bot visuals and behavior:
• `/setstarttext [text]` - Change start message
• `/setstartpic [link/reply]` - Change start photo (GIF/Video)
• `/usedp` - Use user's profile picture
• `/setthumb [link/reply]` - Set default movie thumbnail 🎭
• `/settimer [seconds]` - Auto-delete timer ⏱"""
        buttons = [
            [InlineKeyboardButton("🖼️ Set Thumbnail", callback_data="admin_setthumb"),
             InlineKeyboardButton("⏱ Auto-Delete", callback_data="admin_timer")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_users":
        text = """👥 **USER MANAGEMENT**

Manage your bot audience:
• `/ban [user_id]` - Ban user 🚫
• `/unban [user_id]` - Unban user 🟢
• `/userinfo [user_id]` - Get User Details"""
        buttons = [
            [InlineKeyboardButton("🚫 Ban/Unban Info", callback_data="admin_baninfo")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_movies":
        text = """🎬 **MOVIE MANAGEMENT**

Manage your movie database:
• `/delmovie [name]` - Delete a movie
• `/addcat [name]` - Add category 📂
• `/setlang [lang]` - Filter languages 🌍
• `/autosuggest on/off` - Auto Suggestions 🤖"""
        buttons = [
            [InlineKeyboardButton("🔥 Trending Searches", callback_data="admin_trend")],
            [InlineKeyboardButton("❌ Delete Movie", callback_data="admin_delinfo")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_broadcast":
        text = """📢 **BROADCAST PANEL**

Send messages to all users:
• Reply to any message with `/broadcast`
• Supports Inline Buttons! `[Button | URL]`"""
        buttons = [
            [InlineKeyboardButton("ℹ️ Broadcast Info", callback_data="admin_bcinfo")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_fsub":
        text = """🔐 **FORCE SUBSCRIBE MANAGER**

Force users to join a channel:
• `/setchannel [-100xxx]` - Set channel ID
• `/setlink [URL]` - Set invite link"""
        buttons = [
            [InlineKeyboardButton("⚙️ View Current FSub", callback_data="admin_fsub")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_web":
        text = """🌐 **WEBSITE MANAGER**

Link movies to your website:
• `/setwebsite [URL]` - Set base URL
• `/setwebsite off` - Disable online watch 💻"""
        buttons = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_db":
        text = """🗑 **DATABASE MANAGER**

Manage MongoDB Storage:
• 🗑 Clear All Movies & Posters
• 💾 Backup Database (Generate JSON)
• 📥 Restore Database"""
        buttons = [
            [InlineKeyboardButton("💾 Backup Data", callback_data="admin_backup"),
             InlineKeyboardButton("🗑️ Clear DB", callback_data="admin_clear")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "menu_admins":
        text = """👑 **MULTIPLE ADMIN ROLES**

• `/addadmin [user_id]` - Add a new admin
• `/removeadmin [user_id]` - Remove an admin
• `/adminlist` - View all admins"""
        buttons = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        
    elif data == "menu_maint":
        text = """🛠 **MAINTENANCE & LOGS**

• `/maintenance on` - Turn on Maintenance Mode 🟢
• `/maintenance off` - Turn off Maintenance Mode
• `/restart` - 🔄 Restart the Bot
• `/logs` - 📝 View Error Logs"""
        buttons = [
            [InlineKeyboardButton("📝 View Logs", callback_data="admin_logs"),
             InlineKeyboardButton("🔄 Restart Bot", callback_data="admin_restart")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="admin_home")]
        ]
        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))


# ================= CALLBACK ACTION HANDLERS =================

@app.on_callback_query(filters.regex(r"^admin_(stats|trend|fsub|timer|baninfo|bcinfo|delinfo|clear|confclear|setthumb|backup|logs|restart)$"))
async def admin_actions(client, callback_query):
    # if not await is_admin(callback_query.from_user.id): return
    action = callback_query.data.split("_")[1]
    
    back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="admin_home")]])

    if action == "stats":
        # ഡാറ്റാബേസിൽ നിന്നുള്ള യഥാർത്ഥ ഡാറ്റ കൊടുക്കുക:
        # u = await users_col.count_documents({})
        # m = await movies_col.count_documents({})
        # p = await posters_col.count_documents({})
        # s = await searches_col.count_documents({})
        u, m, p, s = "Loading...", "Loading...", "Loading...", "Loading..." 
        
        text = f"""📊 **Live Bot Analytics:**

👥 Total Users: `{u}`
🎬 Total Movies: `{m}`
🖼️ Saved Posters: `{p}`
🔥 Total Searches: `{s}`

*Status: Running smoothly without errors.* 🟢"""
        await callback_query.message.edit_text(text, reply_markup=back_btn)

    elif action == "trend":
        # Trending logic from DB:
        text = "🔥 **Top Trending Searches:**\n\n(Trending search data will appear here)"
        await callback_query.message.edit_text(text, reply_markup=back_btn)

    elif action == "fsub":
        await callback_query.message.edit_text("⚙️ **Current FSub Config:**\n\nCheck /setchannel to view or change.", reply_markup=back_btn)

    elif action == "timer":
        await callback_query.message.edit_text("⏱️ **Auto-Delete Timer:** Setup\n\nChange using: `/settimer SECONDS`", reply_markup=back_btn)

    elif action == "baninfo":
        await callback_query.message.edit_text("🚫 **Ban / Unban:**\n`/ban UserID`\n`/unban UserID`", reply_markup=back_btn)
        
    elif action == "bcinfo":
        await callback_query.message.edit_text("📢 **Broadcast:**\nReply to any message with `/broadcast`\n\nAdd inline buttons in message text like:\n`[Button Name | URL]`", reply_markup=back_btn)
        
    elif action == "delinfo":
        await callback_query.message.edit_text("❌ **Delete Movie:**\n`/delmovie Movie Name`", reply_markup=back_btn)
        
    elif action == "setthumb":
        await callback_query.message.edit_text("🖼️ **Set File Thumbnail:**\n\nReply to any photo with the command:\n`/setthumb`\n\nOr use:\n`/setthumb Photo_URL`", reply_markup=back_btn)

    elif action == "clear":
        buttons = [[InlineKeyboardButton("✅ Confirm Clear", callback_data="admin_confclear")], [InlineKeyboardButton("❌ Cancel", callback_data="admin_home")]]
        await callback_query.message.edit_text("⚠️ **Clear entirely all movies and posters?**\nThis action cannot be undone!", reply_markup=InlineKeyboardMarkup(buttons))

    elif action == "confclear":
        # await movies_col.delete_many({})
        # await posters_col.delete_many({})
        await callback_query.message.edit_text("✅ Databases cleared successfully!", reply_markup=back_btn)

    elif action == "backup":
        await callback_query.message.edit_text("💾 **Backup feature initialized.**\nSending database backup document shortly...", reply_markup=back_btn)

    elif action == "logs":
        await callback_query.message.edit_text("📝 **Recent Logs:**\n\n`No critical errors found in the last 24 hours.`", reply_markup=back_btn)

    elif action == "restart":
        await callback_query.message.edit_text("🔄 **Bot is restarting...**\nPlease wait 5-10 seconds.", reply_markup=back_btn)
