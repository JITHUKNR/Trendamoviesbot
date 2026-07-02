import os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi

# Bot Configs
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
MONGO_URI = os.environ.get("MONGO_URI", "")

# MongoDB Setup
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
