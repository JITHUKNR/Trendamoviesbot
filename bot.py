from pyrogram import Client, filters

# നിങ്ങളുടെ ടെലിഗ്രാം വിവരങ്ങൾ ഇവിടെ നൽകുക
API_ID = "നിങ്ങളുടെ_API_ID" 
API_HASH = "നിങ്ങളുടെ_API_HASH"
BOT_TOKEN = "നിങ്ങളുടെ_BOT_TOKEN"

# ബോട്ട് ക്രിയേറ്റ് ചെയ്യുന്നു
app = Client(
    "AutoFilterBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ആരെങ്കിലും /start കമാൻഡ് നൽകിയാൽ ബോട്ട് റിപ്ലൈ നൽകാൻ
@app.on_message(filters.command("start"))
def start_command(client, message):
    message.reply_text("ഹലോ! ഞാൻ ഒരു സിനിമാ സെർച്ച് ബോട്ട് ആണ്. എന്നെ ഉപയോഗിക്കാൻ തുടങ്ങാം.")

print("ബോട്ട് സ്റ്റാർട്ട് ആയിട്ടുണ്ട്...")
app.run()
