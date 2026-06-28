import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import re
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from bson.objectid import ObjectId
from flask import Flask
from threading import Thread

# --- Dummy Web Server (Required for Render) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Trenda Bot is Running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

Thread(target=run_server).start()
# -----------------------------------------------

# Configuration from Render Environment
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_URL = os.environ.get("DATABASE_URL")

# Optimized Database Connection
# tlsAllowInvalidCertificates=True helps bypass certificate issues on Render
db_client = AsyncIOMotorClient(DB_URL, tlsAllowInvalidCertificates=True)
db = db_client["TrendaBot"]
collection = db["movies"]

app = Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# 1. Start Command
@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    await message.reply_text("Hello! I am the Trenda Cinema Search Bot. Please type the name of the movie you want to search.")

# 2. Indexing (Save files from channel to database)
@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if file:
        existing = await collection.find_one({"file_id": file.file_id})
        if not existing:
            file_data = {
                "file_id": file.file_id,
                "file_name": getattr(file, "file_name", "Unknown File"),
                "file_size": getattr(file, "file_size", 0)
            }
            await collection.insert_one(file_data)

# 3. Search (Search files in database)
@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    query = message.text
    regex = re.compile(query, re.IGNORECASE)
    results = await collection.find({"file_name": regex}).to_list(length=10)
    
    if not results:
        await message.reply_text("Sorry, this movie is not available in my database.")
        return

    buttons = []
    for result in results:
        size_mb = round(result['file_size'] / (1024 * 1024), 2)
        btn_text = f"[{size_mb}MB] {result['file_name']}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"get_{str(result['_id'])}")])

    reply_markup = InlineKeyboardMarkup(buttons)
    await message.reply_text("Here are the search results:", reply_markup=reply_markup)

# 4. Button Click (Send file on button click)
@app.on_callback_query(filters.regex(r"^get_"))
async def send_file(client, callback_query):
    file_id_str = callback_query.data.split("_")[1]
    result = await collection.find_one({"_id": ObjectId(file_id_str)})
    
    if result:
        await client.send_cached_media(
            chat_id=callback_query.message.chat.id,
            file_id=result["file_id"],
            caption=f"🎥 **{result['file_name']}**\n\nUploaded via Trenda Bot"
        )
        await callback_query.answer("Sending File...")
    else:
        await callback_query.answer("File not found!", show_alert=True)

print("Bot has started successfully...")
app.run()
