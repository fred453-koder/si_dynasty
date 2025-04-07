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
    feed = feedparser.parse(feed_url)
    for entry in feed.entries:
        link = entry.link
        title = entry.title.strip()
        summary = entry.summary.strip()
        published = entry.get("published_parsed")

        if not published:
            continue

        date = datetime.fromtimestamp(time.mktime(published))
        if datetime.utcnow() - date > timedelta(hours=72):
            print(f"Пропущено: стара новина — {title}")
            continue

        if link in posted_links:
            continue

        if not any(keyword.lower() in title.lower() for keyword in KEYWORDS):
            print(f"Пропущено: не по ключовим словам — {title}")
            continue

        print(f"[OK] {title}")
        rewritten = rewrite_news(title, summary, extract_source_name(link))
        post_to_telegram(rewritten)
        posted_links.add(link)
        time.sleep(1)

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
# ====== Тест однієї новини вручну ======
def test_single_news():
    test_title = "China to modernize Ream Naval Base in Cambodia amid geopolitical tensions"
    test_summary = "The Chinese government has announced a significant modernization of the Ream Naval Base in Cambodia, including construction of new docks and training centers. Experts believe this move is aimed at increasing China’s regional maritime influence and ensuring supply chain security."
    test_source = "scmp.com"

    rewritten = rewrite_news(test_title, test_summary, test_source)
    print("\n=== Результат переписаної новини ===\n")
    print(rewritten)

# Виклик тесту:
#test_single_news()
