import os
import feedparser
from datetime import datetime
import pytz
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from deep_translator import GoogleTranslator

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = 843629315

RSS_FEEDS = [
    "https://www.fxstreet.com/rss/news",
    "https://www.forexlive.com/feed",
    "https://www.investing.com/rss/news_25.rss",
    "https://www.instaforex.com/rss/calendar",
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
        print(f"[!] Помилка перекладу: {e}")
        return text

def analyze_sentiment(text):
    text = text.lower()
    if any(w in text for w in ["rise", "gains", "bullish", "rally", "strengthens", "higher", "hawkish"]):
        return "⬆️ Потенціал зростання"
    elif any(w in text for w in ["fall", "weakens", "bearish", "drops", "lower", "dovish"]):
        return "⬇️ Потенціал падіння"
    else:
        return "↔️ Нейтрально/невизначено"

def impact_level(text):
    if any(w in text for w in ["ECB", "FOMC", "CPI", "NFP", "interest rate", "inflation", "Fed"]):
        return "🔴 Сильний вплив"
    elif any(w in text for w in ["ISM", "PMI", "GDP", "jobless", "unemployment"]):
        return "🟠 Середній вплив"
    else:
        return "🟢 Слабкий/новини"

def format_news_message(entry):
    title = entry.get("title", "")
    link = entry.get("link", "#")
    translated_title = translate(title)

    published_parsed = entry.get('published_parsed')
    if published_parsed:
        dt_utc = datetime(*published_parsed[:6], tzinfo=pytz.UTC)
        dt_local = dt_utc.astimezone(PRAGUE_TZ)
        now = datetime.now(PRAGUE_TZ)
        time_diff = now - dt_local
        hours_ago = int(time_diff.total_seconds() // 3600)
        minutes_ago = int((time_diff.total_seconds() % 3600) // 60)
        time_str = dt_local.strftime("%H:%M")
        ago_str = f"{hours_ago} год {minutes_ago} хв тому" if hours_ago > 0 else f"{minutes_ago} хв тому"
    else:
        time_str = "??:??"
        ago_str = "час невідомий"

    impact = impact_level(title)
    sentiment = analyze_sentiment(title)

    return (
        f"📰 {translated_title}\n"
        f"🕒 {time_str} ({ago_str})\n"
        f"{impact} | {sentiment}\n"
        f"🔗 {link}"
    )

async def send_news(app):
    global sent_news_ids
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        sorted_entries = sorted(
            feed.entries,
            key=lambda e: e.get('published_parsed', (1970,1,1,0,0,0,0,0,0)),
            reverse=False
        )
        for entry in sorted_entries:
            published_parsed = entry.get('published_parsed')
            if published_parsed:
                dt_utc = datetime(*published_parsed[:6], tzinfo=pytz.UTC)
                dt_local = dt_utc.astimezone(PRAGUE_TZ)
                now = datetime.now(PRAGUE_TZ)

                # ⛔ Пропускаємо все, що не з сьогоднішнього дня
                if dt_local.date() != now.date():
                    continue

            text = (entry.get("title", "") + " " + entry.get("summary", "")).lower()
            if any(keyword in text for keyword in KEYWORDS):
                news_id = entry.get("id", entry.get("link"))
                if news_id not in sent_news_ids:
                    sent_news_ids.add(news_id)
                    message = format_news_message(entry)
                    try:
                        await app.bot.send_message(chat_id=CHAT_ID, text=message)
                    except Exception as e:
                        print(f"[!] Помилка надсилання: {e}")

async def news_job(context: ContextTypes.DEFAULT_TYPE):
    await send_news(context.application)

async def start(update, context):
    await update.message.reply_text("👋 Привіт! Я надсилатиму сьогоднішні новини по EUR/USD українською.")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(news_job, interval=1800, first=10)
    app.run_polling()
