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
        await db.execute("CREATE TABLE IF NOT EXISTS movies (file_id TEXT, file_name TEXT, file_size INTEGER)")
        await db.commit()

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text("Hello! I am the Trenda Cinema Search Bot. Please type the name of the movie you want to search.")

@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if file:
        # പേര് കിട്ടിയില്ലെങ്കിൽ ഫയൽ ഐഡി ഉപയോഗിക്കാം
        f_name = getattr(file, "file_name", "Unknown_Movie")
        async with aiosqlite.connect("movies.db") as db:
            cursor = await db.execute("SELECT * FROM movies WHERE file_id = ?", (file.file_id,))
            if not await cursor.fetchone():
                await db.execute("INSERT INTO movies VALUES (?, ?, ?)", (file.file_id, f_name, getattr(file, "file_size", 0)))
                await db.commit()

@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    query = message.text
    async with aiosqlite.connect("movies.db") as db:
        cursor = await db.execute("SELECT rowid, file_name, file_size FROM movies WHERE file_name LIKE ?", (f'%{query}%',))
        results = await cursor.fetchall()
    
    if not results:
        google_url = f"https://www.google.com/search?q={quote(query)}+movie"
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Search on Google", url=google_url)]])
        await message.reply_text("Sorry, I couldn't find that movie.", reply_markup=keyboard)
        return

    buttons = []
    for result in results:
        # result[0] = rowid (ID), result[1] = file_name
        size_mb = round(result[2] / (1024 * 1024), 2)
        btn_text = f"[{size_mb}MB] {result[1]}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"get_{result[0]}")])

    await message.reply_text("Here are the search results:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^get_"))
async def send_file(client, callback_query):
    row_id = callback_query.data.split("_")[1]
    async with aiosqlite.connect("movies.db") as db:
        cursor = await db.execute("SELECT file_id, file_name FROM movies WHERE rowid = ?", (row_id,))
        result = await cursor.fetchone()
    
    if result:
        await client.send_cached_media(chat_id=callback_query.message.chat.id, file_id=result[0], caption=f"🎥 {result[1]}")
    else:
        await callback_query.answer("File not found!")

loop = asyncio.get_event_loop()
loop.run_until_complete(init_db())
app.run()
