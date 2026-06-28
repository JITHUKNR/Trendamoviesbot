import os
from pyrogram import Client, filters

# Render Environment-ൽ നിന്നും വിവരങ്ങൾ എടുക്കാൻ
API_ID = int(os.environ.get("API_ID"))
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
