import os
import asyncio
import tempfile
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import Groq
import edge_tts
import requests
from tools import (search_web, get_current_time, save_note, read_notes,
                   get_weather, get_weather_by_coords, get_news,
                   osint_ip, osint_domain, osint_phone, osint_breach,
                   osint_username, osint_email, fake_profile)
from memory import ConversationMemory
from apscheduler.schedulers.asyncio import AsyncIOScheduler

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
memory = ConversationMemory()
ALLOWED_USER = int(os.getenv("YOUR_TELEGRAM_ID"))
scheduler = AsyncIOScheduler()

SYSTEM_PROMPT = """You are ASENA, a personal AI assistant. Your name is ASENA.
You speak English only. You are smart, helpful, direct and concise.
You help with anything the user asks: questions, web search, notes, weather, news, reminders, and OSINT.
When asked about OSINT commands, tell the user:
- ip <address> → IP lookup
- domain <domain> → Domain info
- phone <number> → Phone lookup
- breach <email> → Data breach check
- email <email> → Email validation
- username <name> → Username search across platforms
- fake → Generate fake profile"""

async def text_to_voice(text):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    communicate = edge_tts.Communicate(text, voice="en-US-JennyNeural")
    await communicate.save(tmp.name)
    return tmp.name

async def get_groq_response(user_id, user_message):
    memory.add_message(user_id, "user", user_message)
    msg = user_message.lower().strip()

    # OSINT commands
    if msg.startswith("ip "):
        return osint_ip(user_message.split(" ", 1)[1].strip())
    if msg.startswith("domain "):
        return osint_domain(user_message.split(" ", 1)[1].strip())
    if msg.startswith("phone "):
        return osint_phone(user_message.split(" ", 1)[1].strip())
    if msg.startswith("breach "):
        return osint_breach(user_message.split(" ", 1)[1].strip())
    if msg.startswith("email "):
        return osint_email(user_message.split(" ", 1)[1].strip())
    if msg.startswith("username "):
        return osint_username(user_message.split(" ", 1)[1].strip())
    if msg.startswith("fake"):
        return fake_profile()

    # Other commands
    if any(w in msg for w in ["weather", "temperature", "rain", "sunny", "forecast"]):
        return get_weather()
    if any(w in msg for w in ["news", "headlines", "latest"]):
        return get_news()
    if "save note" in msg and ":" in user_message:
        parts = user_message.split(":", 1)
        return save_note(parts[0].replace("save note", "").strip(), parts[1].strip())
    if any(w in msg for w in ["my notes", "show notes", "list notes"]):
        return read_notes()
    if any(w in msg for w in ["time", "date", "what day", "what time"]):
        return get_current_time()
        context = user_message
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in memory.get_messages(user_id)[:-1]:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": context})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024
    )

    reply = response.choices[0].message.content
    memory.add_message(user_id, "assistant", reply)
    return reply

async def send_reply(update, reply):
    await update.message.reply_text(reply)
    voice_file = await text_to_voice(reply)
    with open(voice_file, "rb") as audio:
        await update.message.reply_voice(audio)
    os.unlink(voice_file)

async def send_reminder(bot, user_id, text):
    await bot.send_message(chat_id=user_id, text=f"⏰ Reminder: {text}")
    voice_file = await text_to_voice(f"Reminder: {text}")
    with open(voice_file, "rb") as audio:
        await bot.send_voice(chat_id=user_id, voice=audio)
    os.unlink(voice_file)

async def send_morning_briefing(bot, user_id):
    news = get_news()
    weather = get_weather()
    message = f"Good morning! Here is your daily briefing:\n\n{weather}\n\n{news}"
    await bot.send_message(chat_id=user_id, text=message)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER:
        await update.message.reply_text("⛔ Unauthorized.")
        return

    await update.message.reply_text("🎤 Got your voice, thinking...")

    try:
        voice = update.message.voice
        file = await context.bot.get_file(voice.file_id)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp:
            await file.download_to_drive(tmp.name)
            with open(tmp.name, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=("voice.ogg", audio_file, "audio/ogg"),
                    model="whisper-large-v3",
                    language="en"
                )

        user_text = transcription.text
        await update.message.reply_text(f"🗣 You: {user_text}")
        reply = await get_groq_response(user_id, user_text)
        await send_reply(update, reply)

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER:
        await update.message.reply_text("⛔ Unauthorized.")
        return

    lat = update.message.location.latitude
    lon = update.message.location.longitude
    reply = get_weather_by_coords(lat, lon)
    await send_reply(update, reply)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ALLOWED_USER:
        await update.message.reply_text("⛔ Unauthorized.")
        return

    await update.message.reply_text("⏳ Thinking...")
    msg = update.message.text.lower()

    if "remind" in msg:
        try:
            time_match = re.search(r'(\d{1,2}):(\d{2})', update.message.text)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                scheduler.add_job(
                    send_reminder,
                    'cron',
                    hour=hour,
                    minute=minute,
                    args=[context.bot, user_id, update.message.text],
                    id=f"reminder_{hour}_{minute}",
                    replace_existing=True
                )
                reply = f"✅ Reminder set for {hour:02d}:{minute:02d}!"
            else:
                reply = "Please include a time. Example: Remind me at 15:30 to call mom"
        except Exception as e:
            reply = f"Could not set reminder: {str(e)}"
    else:
        reply = await get_groq_response(user_id, update.message.text)

    await send_reply(update, reply)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = (
        "Hey! I'm ASENA, your personal AI assistant!\n\n"
        "Here's what I can do:\n"
        "Voice messages supported\n"
        "Weather: just ask\n"
        "News: just ask\n"
        "Reminders: remind me at 15:30 to...\n"
        "Notes: save note title: content\n"
        "Share location for local weather\n\n"
        "OSINT commands:\n"
        "ip <address>\n"
        "domain <domain>\n"
        "phone <number>\n"
        "breach <email>\n"
        "email <email>\n"
        "username <name>\n"
        "fake"
    )
    await send_reply(update, reply)

async def post_init(application):
    scheduler.add_job(
        send_morning_briefing,
        'cron',
        hour=8,
        minute=0,
        args=[application.bot, ALLOWED_USER]
    )
    scheduler.start()

def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.LOCATION, handle_location))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("🤖 ASENA is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
