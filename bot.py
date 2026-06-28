import asyncio
# പൈത്തൺ എറർ ഒഴിവാക്കാൻ ഇത് സഹായിക്കും
asyncio.set_event_loop(asyncio.new_event_loop())

import os
from pyrogram import Client, filters
from flask import Flask
from threading import Thread

# --- ഡമ്മി വെബ് സർവർ (Render എറർ ഒഴിവാക്കാൻ) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Trenda Bot is Running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)

# വെബ് സർവർ ബാക്ക്ഗ്രൗണ്ടിൽ റൺ ചെയ്യാൻ
Thread(target=run_server).start()
# -----------------------------------------------

# ടെലിഗ്രാം ബോട്ടിൻ്റെ വിവരങ്ങൾ
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# ബോട്ട് ക്രിയേറ്റ് ചെയ്യുന്നു
app = Client(
    "TrendaMoviesBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("ഹലോ! ഞാൻ Trenda സിനിമാ സെർച്ച് ബോട്ട് ആണ്. എന്നെ ഉപയോഗിക്കാൻ തുടങ്ങാം.")

print("ബോട്ട് സ്റ്റാർട്ട് ആയിട്ടുണ്ട്...")
app.run()
