import telebot
import requests
from bs4 import BeautifulSoup
import schedule
import time
from datetime import datetime

# Встав свій токен нижче
bot = telebot.TeleBot(BOT_TOKEN)

# Встав свій chat_id нижче
CHAT_ID = "YOUR_CHAT_ID"

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
        time_tag = row.get("data-event-datetime")
        currency = row.get("data-event-currency")
        impact = row.get("data-impact")
        title = row.find("td", {"class": "event"}).get_text(strip=True)
        actual = row.get("data-actual")
        forecast = row.get("data-forecast")
        previous = row.get("data-previous")

        if currency in ["EUR", "USD"] and impact == "3":  # high impact only
            msg = f"🕐 {time_tag[-5:]}
"
            msg += f"📊 {currency}: {title}
"
            msg += f"Факт: {actual or '—'} | Прогноз: {forecast or '—'}
"
            msg += f"📈 {make_prediction(actual, forecast, currency)}"
            output.append(msg)
    return output

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

def job():
    news = parse_news()
    if news:
        for msg in news:
            bot.send_message(CHAT_ID, msg)
    else:
        bot.send_message(CHAT_ID, "🔔 Поки що важливих новин немає.")

schedule.every(5).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
