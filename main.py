import telebot
import requests
from bs4 import BeautifulSoup
import feedparser
import hashlib
import time
import re
import threading
from deep_translator import GoogleTranslator

# --- Налаштування ---
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

# --- Допоміжні функції ---

def clean_text(text):
    text = BeautifulSoup(text, "html.parser").get_text()
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def translate_text(text, target_lang="uk"):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    except Exception as e:
        print(f"Translation error: {e}")
        return text

def make_prediction(actual, forecast, currency):
    try:
        a = float(actual.replace('%','').replace(',', '.'))
        f = float(forecast.replace('%','').replace(',', '.'))
        if currency == "EUR":
            if a > f: return "📈 Прогноз: Євро зміцнюється"
            elif a < f: return "📉 Прогноз: Євро слабшає"
        if currency == "USD":
            if a > f: return "📈 Прогноз: Долар зміцнюється"
            elif a < f: return "📉 Прогноз: Долар слабшає"
        return "🔍 Прогноз: Ринок стабільний"
    except:
        return "ℹ️ Прогноз: Немає даних"

def format_news_message(title, summary, source=None, impact=None, prediction=None):
    # Переклад заголовка і опису
    title_uk = translate_text(title)
    summary_uk = translate_text(summary)

    # Чистка тексту і скорочення до 2 речень
    summary_uk = clean_text(summary_uk)
    sentences = re.split(r'(?<=[.!?]) +', summary_uk)
    short_summary = ' '.join(sentences[:2])
    if len(short_summary) > 350:
        short_summary = short_summary[:347] + "..."

    # Формування повідомлення з іконками
    msg = ""
    if source:
        msg += f"📰 Джерело: {source}\n"
    msg += f"🗞️ *{title_uk}*\n\n"
    msg += f"{short_summary}\n\n"
    if impact:
        impact_uk = translate_text(impact)
        msg += f"⚡ Вплив: {impact_uk}\n"
    if prediction:
        msg += f"{prediction}\n"
    return msg

# --- Функція парсингу економічного календаря Investing.com ---

def parse_news():
    url = "https://www.investing.com/economic-calendar/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"Error fetching calendar: {e}")
        return []

    output = []
    table = soup.find("table", {"id": "economicCalendarData"})
    if not table:
        return []

    rows = table.find_all("tr", {"class": "js-event-item"})
    for row in rows:
        event_id = row.get("data-event-id")
        if not event_id or event_id in last_sent_ids:
            continue

        time_tag = row.get("data-event-datetime")  # формат: "2025-06-30 07:30:00"
        time_str = time_tag[-8:-3] if time_tag else "—"

        currency = row.get("data-event-currency")
        impact = row.get("data-impact")
        title = row.find("td", {"class": "event"}).get_text(strip=True)
        actual = row.get("data-actual") or "—"
        forecast = row.get("data-forecast") or "—"

        # Фільтр по валюті і впливу (3 - високий, 2 - середній)
        if currency in ("EUR", "USD") and impact in ("3", "2"):
            prediction = make_prediction(actual, forecast, currency)
            source = "Investing.com"
            msg = f"🕒 {time_str}\n"
            msg += format_news_message(
                title=title,
                summary=f"Факт: {actual} | Прогноз: {forecast}",
                source=source,
                impact=f"Високий" if impact == "3" else "Середній",
                prediction=prediction
            )
            output.append((event_id, msg))
    return output

# --- Функція парсингу RSS-стрічок ---

def parse_rss_news():
    output = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as e:
            print(f"Error parsing feed {feed_url}: {e}")
            continue

        for entry in feed.entries:
            title = entry.get('title', '')
            summary = entry.get('summary', '') or entry.get('description', '')

            title_clean = clean_text(title)
            # Фільтр по EUR/USD у заголовку
            if not any(sym in title_clean.upper() for sym in ["EUR", "USD", "EUR/USD"]):
                continue

            id_hash = hashlib.md5(title_clean.encode("utf-8")).hexdigest()
            if id_hash in last_sent_ids:
                continue

            # Джерело беремо із feed_url для простоти
            source = re.findall(r'https?://(?:www\.)?([^/]+)/', feed_url)
            source_name = source[0] if source else "Новини"

            msg = format_news_message(title, summary, source=source_name)
            output.append((id_hash, msg))
    return output

# --- Основна робота: збір новин і надсилання ---

def job():
    global last_sent_ids
    news_from_calendar = parse_news()
    news_from_rss = parse_rss_news()

    all_news = news_from_calendar + news_from_rss
    new_news = [(nid, msg) for nid, msg in all_news if nid not in last_sent_ids]

    for nid, msg in new_news:
        try:
            bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
            last_sent_ids.add(nid)
        except Exception as e:
            print(f"Error sending message: {e}")

# --- Обробник команди /start ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 Вітаю! Я надсилатиму свіжі новини по парі EUR/USD кожні 5 хвилин.")

# --- Головна функція запуску ---

def main():
    def news_loop():
        while True:
            try:
                job()
            except Exception as e:
                print(f"Error in job: {e}")
            time.sleep(300)  # 5 хвилин

    threading.Thread(target=news_loop, daemon=True).start()
    bot.polling()

if __name__ == "__main__":
    main()
