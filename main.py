import telebot
import requests
from bs4 import BeautifulSoup
import feedparser
import hashlib
import time
import re

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID = 843629315

bot = telebot.TeleBot(BOT_TOKEN)

last_sent_ids = set()

RSS_FEEDS = [
    "https://www.fxstreet.com/rss/news",
    "https://www.forexlive.com/feed",
    "https://www.investing.com/rss/news_25.rss",
    "https://www.instaforex.com/rss/calendar",
]

def clean_text(text):
    # Видаляємо всі HTML теги
    text = BeautifulSoup(text, "html.parser").get_text()
    # Видаляємо посилання (http, www)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    # Видаляємо зайві пробіли та нові рядки
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
        impact = row.get("data-impact")  # "3"=high, "2"=medium
        title = row.find("td", {"class": "event"}).get_text(strip=True)
        actual = row.get("data-actual")
        forecast = row.get("data-forecast")

        if currency in ("EUR", "USD") and impact in ("3", "2"):
            msg = f"🕐 {time_tag[-5:]}\n"
            msg += f"📊 {currency}: {title}\n"
            msg += f"Факт: {actual or '—'} | Прогноз: {forecast or '—'}\n"
            msg += f"📈 {make_prediction(actual, forecast, currency)}"
            output.append((event_id, msg))
    return output

def parse_rss_news():
    output = []
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get('title', '')
            summary = entry.get('summary', '')

            title_clean = clean_text(title)
            summary_clean = clean_text(summary)

            if not any(sym in title_clean.upper() for sym in ["EUR", "USD", "EUR/USD"]):
                continue

            id_hash = hashlib.md5(title_clean.encode("utf-8")).hexdigest()
            if id_hash in last_sent_ids:
                continue

            if len(summary_clean) > 200:
                summary_clean = summary_clean[:197] + "..."

            msg = f"📢 {title_clean}\n{summary_clean}"
            output.append((id_hash, msg))
    return output

def job():
    global last_sent_ids
    news_from_calendar = parse_news()
    news_from_rss = parse_rss_news()

    all_news = news_from_calendar + news_from_rss
    new_news = [(nid, msg) for nid, msg in all_news if nid not in last_sent_ids]

    for nid, msg in new_news:
        bot.send_message(CHAT_ID, msg)
        last_sent_ids.add(nid)

def main():
    while True:
        try:
            job()
        except Exception as e:
            print(f"Error in job: {e}")
        time.sleep(300)

if __name__ == "__main__":
    main()
