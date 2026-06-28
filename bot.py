import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import aiosqlite
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread
from urllib.parse import quote

# --- Web Server ---
web_app = Flask(__name__)
@web_app.route('/')
def home():
    return "Trenda Bot is Running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_server).start()
# ------------------

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

app = Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ഡാറ്റാബേസ് സെറ്റപ്പ്
async def init_db():
    async with aiosqlite.connect("movies.db") as db:
        # rowid ഓട്ടോമാറ്റിക് ആയി ലഭിക്കും, അതിനാൽ PRIMARY KEY മാത്രം മതി
        await db.execute("CREATE TABLE IF NOT EXISTS movies (file_id TEXT PRIMARY KEY, file_name TEXT, file_size INTEGER)")
        await db.commit()

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text("Hello! I am the Trenda Cinema Search Bot. Please type the name of the movie you want to search.")

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
    query = message.text
    async with aiosqlite.connect("movies.db") as db:
        # file_id മുഴുവനായി ബട്ടണിൽ ഇടാതെ, rowid ഉപയോഗിക്കുന്നു
        cursor = await db.execute("SELECT rowid, file_name, file_size FROM movies WHERE file_name LIKE ?", (f'%{query}%',))
        results = await cursor.fetchall()
    
    if not results:
        google_url = f"https://www.google.com/search?q={quote(query)}+movie+official+name"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Search on Google", url=google_url)]])
        await message.reply_text("Sorry, I couldn't find that movie. Please check the spelling on Google and try again.", reply_markup=keyboard)
        return

    buttons = []
    for result in results:
        # result[0] = rowid, result[1] = file_name
        size_mb = round(result[2] / (1024 * 1024), 2)
        btn_text = f"[{size_mb}MB] {result[1]}"
        # ബട്ടൺ ഡാറ്റയിൽ 'send_' എന്ന് ചേർക്കുന്നു
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{result[0]}")])

    await message.reply_text("Here are the search results:", reply_markup=InlineKeyboardMarkup(buttons))

# ഫയൽ അയക്കുന്ന ഭാഗം (ഇതാണ് പ്രധാന മാറ്റം)
@app.on_callback_query(filters.regex(r"^send_"))
async def send_file(client, callback_query):
    row_id = callback_query.data.split("_")[1]
    async with aiosqlite.connect("movies.db") as db:
        cursor = await db.execute("SELECT file_id, file_name FROM movies WHERE rowid = ?", (row_id,))
        result = await cursor.fetchone()
    
    if result:
        await callback_query.answer("Sending file...")
        await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result[0], 
            caption=f"🎥 **{result[1]}**\n\nUploaded via Trenda Bot"
        )
    else:
        await callback_query.answer("File not found!", show_alert=True)

print("Bot started successfully!")
loop = asyncio.get_event_loop()
loop.run_until_complete(init_db())
app.run()
