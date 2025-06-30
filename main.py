import logging
import os
import requests
from bs4 import BeautifulSoup
from googletrans import Translator
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, JobQueue

# Основна конфігурація
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
CHAT_ID = 843629315

# Набір ID новин, щоб не повторювати повідомлення
sent_news_ids = set()
translator = Translator()

def extract_impact(text):
    text = text.lower()
    if any(word in text for word in ["high", "високий"]):
        return "💥 Високий вплив"
    elif any(word in text for word in ["medium", "середній"]):
        return "⚠️ Середній вплив"
    elif any(word in text for word in ["low", "низький"]):
        return "📌 Низький вплив"
    return "❔ Невідомий вплив"

def extract_sentiment(text):
    text = text.lower()
    if any(word in text for word in ["bullish", "оптимістично"]):
        return "📈 Позитивний прогноз"
    elif any(word in text for word in ["bearish", "песимістично"]):
        return "📉 Негативний прогноз"
    return "❔ Нейтрально"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот працює. Новини надсилатимуться автоматично.")

async def news_job(context: ContextTypes.DEFAULT_TYPE):
    global sent_news_ids

    url = "https://www.forexfactory.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")
    rows = soup.select("tr.calendar__row")

    for row in rows:
        id_tag = row.get("data-eventid")
        if not id_tag or id_tag in sent_news_ids:
            continue

        time_tag = row.select_one("td.time")
        currency_tag = row.select_one("td.currency")
        impact_tag = row.select_one("td.impact")
        title_tag = row.select_one("td.event")
        forecast_tag = row.select_one("td.forecast")
        actual_tag = row.select_one("td.actual")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        if not any(key in title.lower() for key in ["eur", "usd", "cpi", "ecb", "inflation", "non-farm", "retail"]):
            continue

        impact = extract_impact(impact_tag.get("title") if impact_tag else "")
        sentiment = extract_sentiment(title)
        forecast = forecast_tag.get_text(strip=True) if forecast_tag else "—"
        actual = actual_tag.get_text(strip=True) if actual_tag else "—"
        time_val = time_tag.get_text(strip=True) if time_tag else "—"
        currency = currency_tag.get_text(strip=True) if currency_tag else "—"

        translated_title = translator.translate(title, dest="uk").text
        message = (
            f"🕐 {time_val}
"
            f"📊 {currency}: {translated_title}
"
            f"{impact}
"
            f"Факт: {actual} | Прогноз: {forecast}
"
            f"{sentiment}"
        )

        await context.bot.send_message(chat_id=CHAT_ID, text=message)
        sent_news_ids.add(id_tag)

def main():
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.job_queue.run_repeating(news_job, interval=300, first=5)  # кожні 5 хвилин
    app.run_polling()

if __name__ == "__main__":
    main()
