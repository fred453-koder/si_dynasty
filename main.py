import feedparser
import openai
import tldextract
import logging
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError
import os
import time

# ====== Налаштування ======
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

bot = Bot(token=TELEGRAM_TOKEN)

# ====== RSS джерела ======
FEEDS = [
    "http://www.xinhuanet.com/english/rss/worldrss.xml",
    "http://www.chinadaily.com.cn/rss/china_rss.xml",
    "https://www.scmp.com/rss/91/feed"
]

# ====== Ключові теми ======
KEYWORDS = [
    "China", "Chinese", "Beijing", "Xi Jinping", "PLA", "Taiwan", "BRI",
    "AI", "drones", "military", "investment", "chip", "semiconductor",
    "Bangladesh", "Cambodia", "Laos", "Ream", "naval", "base", "supply chains",
    "geopolitics", "BRICS", "conflict", "Taipei", "aircraft carrier", "blockade",
    "diplomatic", "joint", "security", "Pentagon", "Silk Road", "Beidou",
    "Huawei", "TikTok", "ByteDance"
]

# ====== Історія новин для антиповтору ======
posted_links = set()

# ====== Обробка одного RSS ======
def parse_feed(feed_url):
    print(f"Потік: {feed_url}")
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get('title', '')
            summary = entry.get('summary', '')
            link = entry.get('link', '')
            published = entry.get('published', '')

            # ===== Фільтр дати (тимчасово на 720 годин для тесту) =====
            if 'published_parsed' in entry:
                pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                if datetime.now() - pub_date > timedelta(hours=720):  # було 72
                    print(f"Пропущено: стара новина — {title}")
                    continue

            if not any(kw.lower() in title.lower() for kw in KEYWORDS):
                continue

            source = extract_source_name(link)
            rewritten = rewrite_news(title, summary, source)
            post_to_telegram(rewritten)
            posted_links.add(link)

    except Exception as e:
        print(f"❌ Помилка обробки стрічки {feed_url}: {e}")


# ====== Перепис новини через OpenAI ======
def rewrite_news(title, summary, source):
    prompt = f"""
Ти — аналітичний редактор. Створи Telegram-пост про Китай у форматі «Династія Сі». Будь суворим літредактором: прибирай русизми, кальки, повтори. Уникай канцеляризмів. Пиши сучасною, живою, але нейтральною українською.

❗ Структура:
1. **Жирний заголовок** — короткий, інформативний, не клікбейт, але чіпляє. Без складних конструкцій.
2. Перший абзац — короткий виклад суті події.
3. Другий абзац — аналітичне розширення: поясни, чому це важливо, як це впливає на регіон або глобальний баланс сил. Завжди згадуй роль Китаю.
4. Третій абзац у форматі `code` — сухий, фактичний прогноз на 1–3 речення. Не пиши слово "Прогноз".
5. Четвертий абзац — курсивом цитата одного китайського мислителя. Вибір мислителя залежить від теми:
   - Сунь Цзи — якщо йдеться про війну або тактику;
   - Мао Цзедун — для тем боротьби, виживання, опору;
   - Дэн Сяопін — для економіки, адаптації, стратегії мʼякої сили;
   - Хань Фей-цзи — для тем управління, сили, покарання або контролю.
6. П’ятий абзац — _Підписуйся на Династію 🛸_

Оформи джерело наприкінці як: 📌 Джерело: [назва]

Подія: {title}
Опис: {summary}
Джерело: {source}
Мова: українська
"""


    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ти — аналітичний редактор українського Telegram-каналу про політику Китаю."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

# ====== Вивантаження в Telegram ======
def post_to_telegram(text):
    try:
        bot.send_message(chat_id=TELEGRAM_CHANNEL_ID, text=text, parse_mode='Markdown')
    except TelegramError as e:
        logging.error(f"Помилка Telegram: {e}")

# ====== Джерело з URL ======
def extract_source_name(url):
    extracted = tldextract.extract(url)
    return f"{extracted.domain}.{extracted.suffix}"

# ====== Старт ======
if __name__ == '__main__':
    print("Скрипт запущен — починаємо обробку RSS")
    for feed in FEEDS:
        parse_feed(feed)
        time.sleep(2)
