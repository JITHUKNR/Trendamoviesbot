import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())

import os
import uuid
import certifi
from pyrogram import Client, filters
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
    return "Trenda Bot is Running with PRO, Admin & MongoDB Features!"

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
MONGO_URI = os.environ.get("MONGO_URI", "") 

FORCE_SUB_CHANNEL = int(os.environ.get("FORCE_SUB_CHANNEL", -1003903891234)) 
FORCE_SUB_LINK = os.environ.get("FORCE_SUB_LINK", "https://t.me/YourChannelLinkHere")
AUTO_DELETE_TIME = 300 

app = Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# MongoDB Setup (Timeout വെച്ചിട്ടുണ്ട്, അതിനാൽ ബോട്ട് ഫ്രീസ് ആവില്ല)
if MONGO_URI:
    mongo_client = AsyncIOMotorClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    db = mongo_client["trenda_movies"]
    movies_col = db["movies"]
    users_col = db["users"]
    searches_col = db["searches"]
else:
    print("⚠️ WARNING: MONGO_URI is not set!", flush=True)

# Add New User (Error Catching)
async def add_user(user_id):
    try:
        await users_col.update_one(
            {"user_id": user_id},
            {"$setOnInsert": {"user_id": user_id, "is_banned": 0}},
            upsert=True
        )
        return True
    except Exception as e:
        print(f"MongoDB Error: {e}", flush=True)
        return False

# Check Access (Ban & FSub)
async def check_user_access(client, message):
    user_id = message.from_user.id
    
    try:
        user = await users_col.find_one({"user_id": user_id})
        if user and user.get("is_banned") == 1:
            await message.reply_text("⛔ **You are banned from using this bot.**")
            return False
    except Exception:
        pass
            
    try:
        await client.get_chat_member(FORCE_SUB_CHANNEL, user_id)
    except UserNotParticipant:
        btn = [[InlineKeyboardButton("📢 Join Channel", url=FORCE_SUB_LINK)]]
        await message.reply_text(
            "⚠️ **Please join our channel first!**\n\nYou can search for movies only after joining our main channel.", 
            reply_markup=InlineKeyboardMarkup(btn)
        )
        return False
    except Exception:
        pass 
        
    return True

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    db_status = await add_user(message.from_user.id)
    if not db_status:
        # ഡാറ്റാബേസ് കണക്ട് ആയില്ലെങ്കിൽ ബോട്ട് ഇത് റിപ്ലൈ തരും
        await message.reply_text("⚠️ **Database is not connected yet!**\nPlease wait a minute and try again.")
        return
        
    if not await check_user_access(client, message):
        return
    await message.reply_text("👋 **Hello! I am the Trenda Cinema Bot.**\n\nPlease type the name of the movie you want to search.")


# ================= ADMIN PANEL & COMMANDS =================

@app.on_message(filters.command("admin") & filters.private)
async def admin_panel(client, message):
    if message.from_user.id != ADMIN_ID: return
    buttons = [
        [InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🗑️ Clear Movies DB", callback_data="admin_cleardb")]
    ]
    await message.reply_text("👨‍💻 **Welcome to the Admin Panel!**\nSelect an option below:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^admin_"))
async def admin_callbacks(client, callback_query):
    if callback_query.from_user.id != ADMIN_ID:
        await callback_query.answer("You are not authorized!", show_alert=True)
        return

    action = callback_query.data.split("_")[1]

    if action == "stats":
        users_count = await users_col.count_documents({})
        movies_count = await movies_col.count_documents({})
        text = f"📊 **Trenda Bot Statistics**\n\n👥 Total Users: {users_count}\n🎬 Total Movies: {movies_count}"
        await callback_query.message.edit_text(text)

    elif action == "cleardb":
        buttons = [
            [InlineKeyboardButton("✅ Yes, Clear All", callback_data="admin_confirmclear")],
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_cancelclear")]
        ]
        await callback_query.message.edit_text("⚠️ **Are you sure you want to delete ALL movies?**\nThis action cannot be undone.", reply_markup=InlineKeyboardMarkup(buttons))
        
    elif action == "confirmclear":
        await movies_col.delete_many({})
        await callback_query.message.edit_text("✅ All movies have been successfully deleted from the database!")
        
    elif action == "cancelclear":
        await callback_query.message.edit_text("❌ Database clear cancelled.")

    elif action == "broadcast":
        info_text = "📢 **How to Broadcast:**\n\nTo send a message to all users, type:\n`/broadcast Your message here`"
        await callback_query.message.edit_text(info_text)

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_message(client, message):
    if message.from_user.id != ADMIN_ID: return
    if len(message.command) < 2:
        await message.reply_text("Please provide a message. Example:\n`/broadcast Hello users!`")
        return

    broadcast_text = message.text.split(" ", 1)[1]
    success, failed = 0, 0
    reply = await message.reply_text("📢 Broadcast starting...")
    
    async for user in users_col.find({}):
        try:
            await client.send_message(chat_id=user["user_id"], text=broadcast_text)
            success += 1
            await asyncio.sleep(0.1) 
        except Exception:
            failed += 1
            
    await reply.edit_text(f"✅ **Broadcast Completed!**\n\nDelivered: {success}\nFailed: {failed}")

@app.on_message(filters.command("ban") & filters.private)
async def ban_user(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.command[1])
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 1}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` has been BANNED.")
    except Exception:
        await message.reply_text("Usage: `/ban UserID`")

@app.on_message(filters.command("unban") & filters.private)
async def unban_user(client, message):
    if message.from_user.id != ADMIN_ID: return
    try:
        target_id = int(message.command[1])
        await users_col.update_one({"user_id": target_id}, {"$set": {"is_banned": 0}}, upsert=True)
        await message.reply_text(f"✅ User `{target_id}` has been UNBANNED.")
    except Exception:
        await message.reply_text("Usage: `/unban UserID`")

@app.on_message(filters.command("trending") & filters.private)
async def trending_searches(client, message):
    if message.from_user.id != ADMIN_ID: return
    
    cursor = searches_col.find().sort("count", -1).limit(10)
    results = await cursor.to_list(length=10)
    
    if not results:
        await message.reply_text("No searches recorded yet!")
        return
        
    text = "🔥 **Top Trending Movies:**\n\n"
    for idx, res in enumerate(results, 1):
        text += f"{idx}. {res['_id'].title()} - ({res['count']} searches)\n"
    await message.reply_text(text)

# ==========================================================

@app.on_message((filters.document | filters.video) & filters.channel)
async def save_file(client, message):
    file = message.document or message.video
    if file:
        f_name = getattr(file, "file_name", "Unknown_Movie")
        short_id = uuid.uuid4().hex[:8] 
        try:
            await movies_col.update_one(
                {"file_id": file.file_id},
                {"$setOnInsert": {
                    "file_name": f_name, 
                    "file_size": getattr(file, "file_size", 0),
                    "short_id": short_id
                }},
                upsert=True
            )
        except Exception as e:
            print(f"Error saving file: {e}", flush=True)

@app.on_message(filters.text & filters.private)
async def search_file(client, message):
    if message.text.startswith("/"): return
    
    db_status = await add_user(message.from_user.id)
    if not db_status:
        await message.reply_text("⚠️ **Database is not connected yet!**\nPlease wait a minute and try again.")
        return

    if not await check_user_access(client, message):
        return
        
    query = message.text
    
    await searches_col.update_one(
        {"_id": query.lower()},
        {"$inc": {"count": 1}},
        upsert=True
    )
    
    cursor = movies_col.find({"file_name": {"$regex": query, "$options": "i"}}).limit(50)
    results = await cursor.to_list(length=50)
    
    if not results:
        google_url = f"https://www.google.com/search?q={quote(query)}+movie+official+name"
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search on Google", url=google_url)],
            [InlineKeyboardButton("📩 Request to Admin", callback_data=f"req_{query[:30]}")]
        ])
        await message.reply_text("Sorry, this movie is not available in our database.", reply_markup=keyboard)
        return

    buttons = []
    for result in results:
        size_mb = round(result["file_size"] / (1024 * 1024), 2)
        btn_text = f"[{size_mb}MB] {result['file_name']}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"send_{result['short_id']}")])

    await message.reply_text("Here are the search results:", reply_markup=InlineKeyboardMarkup(buttons))

@app.on_callback_query(filters.regex(r"^req_"))
async def request_movie(client, callback_query):
    query = callback_query.data.split("_", 1)[1]
    user = callback_query.from_user
    
    if ADMIN_ID != 0:
        req_text = f"🆕 **New Movie Request!**\n\n🎬 Movie: `{query}`\n👤 User: {user.mention} (`{user.id}`)"
        try:
            await client.send_message(ADMIN_ID, req_text)
            await callback_query.answer("Your request has been sent to the admin!", show_alert=True)
        except Exception:
            await callback_query.answer("Failed to contact the admin.", show_alert=True)
    else:
         await callback_query.answer("Admin ID is not configured.", show_alert=True)

async def delete_after_delay(message, delay):
    await asyncio.sleep(delay)
    try:
        await message.delete()
    except Exception:
        pass

@app.on_callback_query(filters.regex(r"^send_"))
async def send_file(client, callback_query):
    if not await check_user_access(client, callback_query):
        return
        
    short_id = callback_query.data.split("_")[1]
    result = await movies_col.find_one({"short_id": short_id})
    
    if result:
        await callback_query.answer("Sending file...")
        sent_msg = await client.send_cached_media(
            chat_id=callback_query.message.chat.id, 
            file_id=result["file_id"], 
            caption=f"🎥 **{result['file_name']}**\n\n⚠️ *This file will be automatically deleted in 5 minutes.*"
        )
        asyncio.create_task(delete_after_delay(sent_msg, AUTO_DELETE_TIME))
    else:
        await callback_query.answer("File not found!", show_alert=True)

print("Bot started successfully with Pro Features & MongoDB!", flush=True)
app.run()
