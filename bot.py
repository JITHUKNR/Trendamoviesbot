import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import aiosqlite
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant
from flask import Flask
from threading import Thread
from urllib.parse import quote

# --- Web Server ---
web_app = Flask(__name__)
@web_app.route('/')
def home():
    return "Trenda Bot is Running with PRO & Admin Features!"

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

# ഫോഴ്‌സ് സബ്‌സ്ക്രൈബ് (FSub) സെറ്റിംഗ്സ്
FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", -1004402285436)) 
FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/നിങ്ങളുടെ_ചാനൽ_ലിങ്ക്_ഇവിടെ_കൊടുക്കുക")

# ഓട്ടോ ഡിലീറ്റ് സമയം (5 മിനിറ്റ് = 300 സെക്കൻഡ്)
AUTO_DELETE_TIME = 300 

app = Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ഡാറ്റാബേസ് സെറ്റപ്പ്
async def init_db():
    async with aiosqlite.connect("movies.db") as db:
        await db.execute("CREATE TABLE IF NOT EXISTS movies (file_id TEXT PRIMARY KEY, file_name TEXT, file_size INTEGER)")
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, is_banned INTEGER DEFAULT 0)")
        await db.execute("CREATE TABLE IF NOT EXISTS searches (query TEXT PRIMARY KEY, count INTEGER DEFAULT 1)")
        await db.commit()

# പുതിയ യൂസറെ സേവ് ചെയ്യാൻ
async def add_user(user_id):
    async with aiosqlite.connect("movies.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        await db.commit()

# Ban & Force Subscribe ചെക്ക് ചെയ്യാനുള്ള ഫംഗ്ഷൻ
async def check_user_access(client, message):
    user_id = message.from_user.id
    
    # 1. Ban Check
    async with aiosqlite.connect("movies.db") as db:
        cursor = await db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        user = await cursor.fetchone()
        if user and user[0] == 1:
            await message.reply_text("⛔ നിങ്ങളെ ഈ ബോട്ട് ഉപയോഗിക്കുന്നതിൽ നിന്ന് വിലക്കിയിരിക്കുന്നു (Banned).")
            return False
            
    # 2. Force Subscribe Check
    try:
        await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
    except UserNotParticipant:
        btn = [[InlineKeyboardButton("📢 Join Channel", url=FORCE_SUB_LINK)]]
        await message.reply_text(
            "⚠️ **ആദ്യം ഞങ്ങളുടെ ചാനലിൽ ജോയിൻ ചെയ്യുക!**\nചാനലിൽ ജോയിൻ ചെയ്ത ശേഷം മാത്രം സിനിമകൾ സെർച്ച് ചെയ്യുക.", 
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return False
    except Exception:
        pass # ബോട്ട് അഡ്മിൻ അല്ലെങ്കിൽ അവഗണിക്കുക
        
    return True

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await add_user(message.from_user.id)
    if not await check_user_access(client, message):
        return
    await message.reply_text("Hello! I am the Trenda Cinema Search Bot. Please type the name of the movie you want to search.")


# ================= ADMIN PANEL & COMMANDS =================

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if message.from_user.id != ADMIN_ID: return

    buttons = [
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🗑️ Clear Movies DB", callback_data="admin_cleardb")]
    ]
    await message.reply_text(
        "👋 **അഡ്മിൻ പാനലിലേക്ക് സ്വാഗതം!**\nതാഴെ കാണുന്ന ഓപ്ഷനുകളിൽ ഒന്ന് തിരഞ്ഞെടുക്കുക:", 
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query(filters.regex(r"^admin_"))
async def admin_callbacks(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("You are not authorized!", show_alert=True)
        return

    action = callback_query.data.split("_")[1]

    if action == "stats":
        async with aiosqlite.connect("movies.db") as db:
            users_count = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
            movies_count = await (await db.execute("SELECT COUNT(*) FROM movies")).fetchone()
        text = f"📊 **Trenda Bot Statistics**\n\n👥 Total Users: {users_count[0]}\n🎬 Total Movies: {movies_count[0]}"
        await callback_query.message.edit_text(text)

    elif action == "cleardb":
        async with aiosqlite.connect("movies.db") as db:
            await db.execute("DELETE FROM movies")
            await db.commit()
        await callback_query.message.edit_text("✅ ഡാറ്റാബേസിലെ എല്ലാ സിനിമകളും വിജയകരമായി ഡിലീറ്റ് ചെയ്തു!")

    elif action == "broadcast":
        info_text = "📢 **ബ്രോഡ്‌കാസ്റ്റ് ചെയ്യാനുള്ള വഴി:**\n\nഎല്ലാ യൂസർമാർക്കും മെസ്സേജ് അയക്കാൻ താഴെ കാണുന്ന പോലെ ടൈപ്പ് ചെയ്യുക:\n\n`/broadcast നിങ്ങളുടെ മെസ്സേജ് ഇവിടെ ടൈപ്പ് ചെയ്യുക`"
        await callback_query.message.edit_text(info_text)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_message(client, message):
    if message.from_user.id != ADMIN_ID: return
    if len(message.command) < 2:
        await message.reply_text("ദയവായി മെസ്സേജ് കൂടി ടൈപ്പ് ചെയ്യുക. ഉദാഹരണം:\n`/broadcast ഹലോ ഡിയർ യൂസേഴ്സ്`")
        return

    broadcast_text = message.text.split(" ", 1)[1]
    async with aiosqlite.connect("movies.db") as db:
        cursor = await db.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()

    success, failed = 0, 0
    reply = await message.reply_text("📢 ബ്രോഡ്‌കാസ്റ്റ് തുടങ്ങുന്നു...")
    
    for user in users:
        try:
            await client.send_message(chat_id=user[0], text=broadcast_text)
            success += 1
            await asyncio.sleep(0.1) 
        except Exception:
            failed += 1
            
    await reply.edit_text(f"✅ ബ്രോഡ്‌കാസ്റ്റ് പൂർത്തിയായി!\n\nലഭിച്ചവർ: {success}\nപരാജയപ്പെട്ടവർ: {failed}")

@app.on_message(filters.command("ban") & filters.private)
async def ban_user(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.command[1])
        async with aiosqlite.connect("movies.db") as db:
            await db.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
            await db.commit()
        await message.reply_text(f"✅ User `{target_id}` has been BANNED.")
    except Exception:
        await message.reply_text("ഉപയോഗിക്കേണ്ട രീതി: `/ban UserID`")

@app.on_message(filters.command("unban") & filters.private)
async def unban_user(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.command[1])
        async with aiosqlite.connect("movies.db") as db:
            await db.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (target_id,))
            await db.commit()
        await message.reply_text(f"✅ User `{target_id}` has been UNBANNED.")
    except Exception:
        await message.reply_text("ഉപയോഗിക്കേണ്ട രീതി: `/unban UserID`")

@app.on_message(filters.command("trending") & filters.private)
async def trending_searches(client, message):
    if message.from_user.id != ADMIN_ID: return
    async with aiosqlite.connect("movies.db") as db:
        cursor = await db.execute("SELECT query, count FROM searches ORDER BY count DESC LIMIT 10")
        results = await cursor.fetchall()
    
    if not results:
        await message.reply_text("ഇതുവരെ ആരും ഒന്നും തിരഞ്ഞിട്ടില്ല!")
        return
        
    text = "🔥 **ഏറ്റവും കൂടുതൽ തിരഞ്ഞ സിനിമകൾ:**\n\n"
    for idx, (query, count) in enumerate(results, 1):
        text += f"{idx}. {query.title()} - ({count} searches)\n"
    await message.reply_text(text)

# ==========================================================

# ഫയൽ സേവ് ചെയ്യുന്ന ഭാഗം
@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if file:
        f_name = getattr(file, "file_name", "Unknown_Movie")
        async with aiosqlite.connect("movies.db") as db:
            await db.execute("INSERT OR IGNORE INTO movies VALUES (?, ?, ?)", 
                             (file.file_id, f_name, getattr(file, "file_size", 0)))
            await db.commit()

# സെർച്ച് ചെയ്യുന്ന ഭാഗം
@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    if message.text.startswith("/"): return
    
    await add_user(message.from_user.id)
    if not await check_user_access(client, message):
        return
        
    query = message.text
    async with aiosqlite.connect("movies.db") as db:
        await db.execute("""
            INSERT INTO searches (query, count) VALUES (?, 1)
            ON CONFLICT(query) DO UPDATE SET count = count + 1
        """, (query.lower(),))
        
        cursor = await db.execute("SELECT rowid, file_name, file_size FROM movies WHERE file_name LIKE ?", (f'%{query}%',))
        results = await cursor.fetchall()
        await db.commit()
    
    if not results:
        google_url = f"https://www.google.com/search?q={quote(query)}+movie+official+name"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search on Google", url=google_url)],
            [InlineKeyboardButton("📩 Request to Admin", callback_data=f"req_{query[:30]}")]
        ])
        await message.reply_text("ക്ഷമിക്കണം, ഈ സിനിമ എന്റെ ഡാറ്റാബേസിൽ ലഭ്യമല്ല.", reply_markup=keyboard)
        return

    buttons = []
    for result in results:
        size_mb = round(result[2] / (1024 * 1024), 2)
        btn_text = f"[{size_mb}MB] {result[1]}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{result[0]}")])

    await message.reply_text("Here are the search results:", reply_markup=InlineKeyboardMarkup(buttons))

# Movie Request Button Logic
@app.on_callback_query(filters.regex(r"^req_"))
async def request_movie(client, callback_query):
    query = callback_query.data.split("_", 1)[1]
    user = callback_query.from_user
    
    if ADMIN_ID != 0:
        req_text = f"🆕 **New Movie Request!**\n\n🎬 Movie: `{query}`\n👤 User: {user.mention} (`{user.id}`)"
        try:
            await client.send_message(ADMIN_ID, req_text)
            await callback_query.answer("നിങ്ങളുടെ റിക്വസ്റ്റ് അഡ്മിന് അയച്ചിട്ടുണ്ട്!", show_alert=True)
        except Exception:
            await callback_query.answer("അഡ്മിനെ ബന്ധപ്പെടാൻ കഴിഞ്ഞില്ല.", show_alert=True)
    else:
         await callback_query.answer("അഡ്മിൻ ഐഡി സെറ്റ് ചെയ്തിട്ടില്ല.", show_alert=True)

# Auto-Delete Task Function
async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

# ഫയൽ അയക്കുന്ന ഭാഗം & Auto-Delete
@app.on_callback_query(filters.regex(r"^send_"))
async def send_file(client, callback_query):
    if not await check_user_access(client, callback_query):
        return
        
    row_id = callback_query.data.split("_")[1]
    async with aiosqlite.connect("movies.db") as db:
        cursor = await db.execute("SELECT file_id, file_name FROM movies WHERE rowid = ?", (row_id,))
        result = await cursor.fetchone()
    
    if result:
        await callback_query.answer("Sending file...")
        sent_msg = await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result[0], 
            caption=f"🎥 **{result[1]}**\n\n⚠️ *ഈ ഫയൽ 5 മിനിറ്റിനുള്ളിൽ തനിയെ ഡിലീറ്റ് ആകുന്നതാണ്.*"
        )
        asyncio.create_task(delete_after_delay(sent_msg, AUTO_DELETE_TIME))
    else:
        await callback_query.answer("File not found!", show_alert=True)

print("Bot started successfully with ALL features!")
loop = asyncio.get_event_loop()
loop.run_until_complete(init_db())
app.run()
