# bot_core.py
import os
from pyrogram import Client
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Configs
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
MONGO_URI = os.environ.get("MONGO_URI", "")

# Client (ഇത് ഇമ്പോർട്ട് ചെയ്യുമ്പോൾ റൺ ആകില്ല — കാരണം ഇത് ഒരു function-ൽ ആണ്)
def get_bot():
    return Client("TrendaMoviesBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# DB
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
