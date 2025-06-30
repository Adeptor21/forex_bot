import telebot
import requests
from bs4 import BeautifulSoup
import feedparser
import hashlib
import time
import re

from telegram import Bot
import asyncio

async def delete_webhook(bot_token):
    bot = Bot(bot_token)
    await bot.delete_webhook(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(delete_webhook(BOT_TOKEN))
    main()  # твоя основна функція запуску бота

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

bot = telebot.TeleBot(BOT_TOKEN)

last_sent_ids = set()

RSS_FEEDS = [
    "https://www.fxstreet.com/rss/news",
    "https://www.forexlive.com/feed",
    "https://www.investing.com/rss/news_25.rss",
    "https://www.instaforex.com/rss/calendar",
]

def clean_text(text):
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def make_prediction(actual, forecast, currency):
    try:
        a = float(actual.replace('%','').replace(',', '.'))
        f = float(forecast.replace('%','').replace(',', '.'))
        if currency == "EUR":
            if a > f: return "Євро зміцнюється 📈"
            elif a < f: return "Євро слабшає 📉"
        if currency == "USD":
            if a > f: return "Долар зміцнюється 📈"
            elif a < f: return "Долар слабшає 📉"
        return "Ринок стабільний 🔍"
    except:
        return "Немає повних даних"

def parse_news():
    url = "https://www.investing.com/economic-calendar/"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    output = []
    table = soup.find("table", {"id": "economicCalendarData"})
    if not table:
        return []

    rows = table.find_all("tr", {"class": "js-event-item"})

    for row in rows:
        event_id = row.get("data-event-id")
        if not event_id or event_id in last_sent_ids:
            continue

        time_tag = row.get("data-event-datetime")
        currency = row.get("data-event-currency")
