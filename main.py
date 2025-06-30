import telebot
import requests
from bs4 import BeautifulSoup
import feedparser
import hashlib
import time
import re
import threading

BOT_TOKEN = "8053411183:AAGPglnG3gQ5-V052RA1e9qqGQR9x8tPMB0"
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
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def make_prediction(actual, forecast, currency):
    try:
        a = float(actual.replace('%','').replace(',', '.'))
        f = float(forecast.replace('%','').replace(',', '.'))
        if currency == "EUR":
            if a > f: return "📈 Євро зміцнюється"
            elif a < f: return "📉 Євро слабшає"
        if currency == "USD":
            if a > f: return "📈 Долар зміцнюється"
            elif a < f: return "📉 Долар слабшає"
        return "🔍 Ринок стабільний"
    except:
        return "ℹ️ Немає даних для прогнозу"

def format_news_message(title, summary):
    sentences = summary.split('. ')
    short_summary = '. '.join(sentences[:3])
    if len(short_summary) > 300:
        short_summary = short_summary[:297] + "..."
    return f"*{title}*\n\n{short_summary}"

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
        impact = row.get("data-impact")
        title = row.find("td", {"class": "event"}).get_text(strip=True)
        actual = row.get("data-actual")
        forecast = row.get("data-forecast")

        if currency in ("EUR", "USD") and impact in ("3", "2"):
            prediction = make_prediction(actual, forecast, currency)
            msg = f"🕐 {time_tag[-5:]}\n"
            msg += f"📊 {currency}: *{title}*\n"
            msg += f"Факт: {actual or '—'} | Прогноз: {forecast or '—'}\n"
            msg += f"{prediction}"
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

            # Фільтр по EUR/USD у заголовку
            if not any(sym in title_clean.upper() for sym in ["EUR", "USD", "EUR/USD"]):
                continue

            id_hash = hashlib.md5(title_clean.encode("utf-8")).hexdigest()
            if id_hash in last_sent_ids:
                continue

            msg = format_news_message(title_clean, summary_clean)
            output.append((id_hash, msg))
    return output

def job():
    global last_sent_ids
    news_from_calendar = parse_news()
    news_from_rss = parse_rss_news()

    all_news = news_from_calendar + news_from_rss
    new_news = [(nid, msg) for nid, msg in all_news if nid not in last_sent_ids]

    for nid, msg in new_news:
        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
        last_sent_ids.add(nid)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Вітаю! Я надсилатиму свіжі новини по парі EUR/USD кожні 5 хвилин.")

def main():
    # Запускаємо цикл новин у фоновому потоці
    def news_loop():
        while True:
            try:
                job()
            except Exception as e:
                print(f"Error in job: {e}")
            time.sleep(300)

    threading.Thread(target=news_loop, daemon=True).start()

    # Запускаємо Telegram polling
    bot.polling()

if __name__ == "__main__":
    main()
