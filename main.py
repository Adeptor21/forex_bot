import os
import asyncio
import feedparser
from datetime import datetime
import pytz
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = 843629315

# Джерела RSS (приклади)
RSS_FEEDS = [
    "https://www.forexfactory.com/ffcal-weekly.xml",      # ForexFactory календар
    "https://www.investing.com/rss/news_25.rss",         # Investing.com Forex News
    "https://www.dailyfx.com/feeds/all",                  # DailyFX RSS (загальний)
    "https://www.fxstreet.com/rss/news",                  # FXStreet News RSS
    "https://www.forexlive.com/rss",                      # Forexlive RSS
    # Bloomberg немає відкритого RSS - треба парсити вручну або API
]

# Ключові слова для фільтрації по EUR/USD
KEYWORDS = [
    "eurusd", "eur/usd", "usd", "euro", "eurozone", "us inflation", "fed", "ecb", "cpi", "interest rate",
    "inflation", "usdollar", "usdollar index", "eur", "usd economic", "usd data"
]

# Часова зона Праги
PRAGUE_TZ = pytz.timezone("Europe/Prague")

# Збереження надісланих новин
sent_news_ids = set()

def format_date(date_obj):
    return date_obj.strftime("%A, %d %B")

def format_news_message(entry):
    # Припускаємо, що entry містить title, published, summary (або description), link
    
    # Перетворення дати в часовий пояс Праги
    published_parsed = entry.get('published_parsed')
    if published_parsed:
        dt_utc = datetime(*published_parsed[:6], tzinfo=pytz.UTC)
        dt_local = dt_utc.astimezone(PRAGUE_TZ)
        date_str = format_date(dt_local)
        time_str = dt_local.strftime("%H:%M")
        now = datetime.now(PRAGUE_TZ)
        if dt_local.date() != now.date():
        continue
    else:
        date_str = "Невідома дата"
        time_str = "??:??"
    
    # Парсимо текст новини (summary або title) на предмет ключових даних — спрощено
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    
    # Фіктивні поля, оскільки не всі RSS дають структуру
    impact = "Високий"
    potential = "50–90 піпсів"
    scenario = "Якщо CPI нижче → USD падає → EUR/USD вгору"
    
    # Форматування повідомлення
    message = (
        f"📆 {date_str}\n\n"
        f"💥 Важлива новина через 1 год:\n"
        f"🇺🇸 {title}\n"
        f"⏰ Час: {time_str} (за Прагой)\n"
        f"📈 Прогноз: - | Попереднє: -\n\n"
        f"🎯 Вплив на EUR/USD: {impact}\n"
        f"⚖️ Потенціал руху: {potential}\n"
        f"📌 Сценарій: {scenario}"
    )
    return message

async def send_news(app):
    global sent_news_ids
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        # Сортуємо від найстаріших до найновіших
        sorted_entries = sorted(
            feed.entries,
            key=lambda e: e.get('published_parsed', (1970,1,1,0,0,0,0,0,0)),
            reverse=False
        )
        for entry in sorted_entries:
            # Фільтрація по ключових словах у заголовку або описі
            text = (entry.get("title","") + " " + entry.get("summary","")).lower()
            if any(keyword in text for keyword in KEYWORDS):
                news_id = entry.get("id", entry.get("link"))
                if news_id not in sent_news_ids:
                    sent_news_ids.add(news_id)
                    message = format_news_message(entry)
                    try:
                        await app.bot.send_message(chat_id=CHAT_ID, text=message)
                    except Exception as e:
                        print(f"Помилка відправки новини: {e}")

async def news_job(context: ContextTypes.DEFAULT_TYPE):
    await send_news(context.application)

async def start(update, context):
    await update.message.reply_text(
        "Привіт! Я надсилатиму тобі важливі новини по EUR/USD кожні 30 хвилин."
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(news_job, interval=1800, first=10)
    app.run_polling()
