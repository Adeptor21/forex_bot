import os
import asyncio
import feedparser
from datetime import datetime
import pytz
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from deep_translator import GoogleTranslator

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

RSS_FEEDS = [
    "https://www.fxstreet.com/rss/news",
    "https://www.forexlive.com/feed",
    "https://www.investing.com/rss/news_25.rss",
]

KEYWORDS = [
    "eurusd", "eur/usd", "usd", "euro", "eurozone", "us inflation", "fed", "ecb",
    "cpi", "interest rate", "inflation", "eur", "usd economic", "usd data"
]

PRAGUE_TZ = pytz.timezone("Europe/Prague")
sent_news_ids = set()

def translate(text, to_lang="uk"):
    try:
        return GoogleTranslator(source='auto', target=to_lang).translate(text)
    except Exception as e:
        print(f"Помилка перекладу: {e}")
        return text  # fallback: повертаємо оригінал, якщо переклад не вдався

def format_date(date_obj):
    return date_obj.strftime("%A, %d %B")

def format_news_message(entry):
    published_parsed = entry.get('published_parsed')
    if published_parsed:
        dt_utc = datetime(*published_parsed[:6], tzinfo=pytz.UTC)
        dt_local = dt_utc.astimezone(PRAGUE_TZ)
        date_str = format_date(dt_local)
        time_str = dt_local.strftime("%H:%M")
    else:
        date_str = "Невідома дата"
        time_str = "??:??"

    title = entry.get("title", "")
    summary = entry.get("summary", "")

    # Переклад заголовку та короткого опису
    title_ua = translate(title)
    summary_ua = translate(summary)

    message = (
        f"📆 {date_str}\n\n"
        f"📰 {title_ua}\n\n"
        f"🔍 {summary_ua}\n\n"
        f"⏰ Час: {time_str} (за Прагою)\n"
        f"🔗 [Читати повністю]({entry.get('link')})"
    )
    return message

async def send_news(app):
    global sent_news_ids
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
            if any(keyword in text for keyword in KEYWORDS):
                news_id = entry.get("id", entry.get("link"))
                if news_id not in sent_news_ids:
                    sent_news_ids.add(news_id)
                    message = format_news_message(entry)
                    try:
                        await app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode='Markdown')
                    except Exception as e:
                        print(f"Помилка надсилання: {e}")

async def news_job(context: ContextTypes.DEFAULT_TYPE):
    await send_news(context.application)

async def start(update, context):
    await update.message.reply_text("👋 Привіт! Я надсилатиму тобі новини по EUR/USD перекладені українською.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(news_job, interval=1800, first=10)
    app.run_polling()
