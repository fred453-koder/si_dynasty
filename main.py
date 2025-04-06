import feedparser
import time
import openai
import tldextract
import re
from datetime import datetime, timedelta
from telegram import Bot
import os

# === НАСТРОЙКИ ===
TELEGRAM_TOKEN = "7725055774:AAHRf_3tfVO-ZufWBZZpTT92P5WQS5GRoUQ"
CHANNEL_ID = "@xi_dynasty"
OPENAI_API_KEY = "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"

POSTED_LINKS_FILE = "posted_links.txt"

RSS_FEEDS = [
    "http://www.xinhuanet.com/english/rss/worldrss.xml",
    "http://www.chinadaily.com.cn/rss/china_rss.xml",
    "https://www.scmp.com/rss/91/feed",
    "https://www.fmprc.gov.cn/mfa_eng/rss.xml",
    "https://thediplomat.com/feed/",
    "https://www.asiapacificsecuritymagazine.com/feed/",
    "https://www.indiatoday.in/rss/1206514",
    "https://eastasiaforum.org/feed/",
    "https://venturebeat.com/category/ai/feed/"
]

KEYWORDS = [
    "China", "Beijing", "Taiwan", "Xi Jinping", "PLA", "Chinese military",
    "AI", "artificial intelligence", "drones", "semiconductors",
    "Silk Road", "BRI", "space program", "spy balloon", "trade war", "sanctions",
    "army", "tariffs", "USA", "Ukraine", "Zelensky", "Putin", "Moscow",
    "war", "deal", "business", "investments", "condemned", "official visit",
    "Taiwan", "oil", "gas", "yuan", "Indo-Pacific", "ASEAN", "Blinken",
    "Biden", "South China Sea", "diplomacy", "Philippines", "maritime", "nuclear"
]

EXCLUDE_PATTERNS = [
    "crash", "accident", "injured", "fire", "killed", "police", "arrested",
    "dies", "dead", "murder", "suicide", "hospital"
]

bot = Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

def send_message_safe(text):
    try:
        bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode='HTML',
            disable_web_page_preview=True,
            timeout=20
        )
    except Exception as e:
        print(f"Ошибка отправки сообщения в Telegram: {e}")

def extract_source(url):
    ext = tldextract.extract(url)
    if ext.domain == "scmp":
        return "South China Morning Post"
    return ext.domain.capitalize()

def rewrite_news(title, summary, source):
    prompt = f"""
Ти працюєш як команда з трьох професіоналів:
1. журналіст — викладає суть подій;
2. аналітик — формулює короткий прогноз;
3. редактор-перекладач — адаптує текст українською без суржику і кальки.

Твоя задача — створити пост для аналітичного Telegram-каналу про геополітику Китаю. Якщо джерело — це публіцистика або колонка, перероби її в короткий виклад і додай прогноз. Якщо інформація слабка або вторинна — краще нічого не пиши.

📌 Формат:
1. <b>Жирний заголовок</b>
2. Перший абзац — виклад подій
3. Другий абзац — аналітичне пояснення
4. <b>Прогноз:</b> у вигляді абзацу, без тега <code>
5. <i>Цитата китайського мислителя</i> — з іменем автора
6. “Підписуйся на Династію 🛸”
7. 📌 Джерело: {source}

✍️ Обов'язково:
- Кожне речення — не довше 14 слів.
- Уникай складнопідрядних речень і канцеляризмів.
- Перевіряй правильність відмінків.
- Не додавай зайвого пафосу. Пиши лаконічно, сильно і смачно.
- Якщо це авторська колонка — згадай автора у другому абзаці.
- Діли складні речення на два. Не бійся крапок.

Заголовок: {title}
Опис: {summary}
"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Ти працюєш як команда журналіста, аналітика і редактора. Створюєш стратегічні публікації для аналітичного Telegram-каналу про Китай. Вмієш відрізняти новину від публіцистики і не вигадуєш інформацію."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content.strip().replace("Рідпишись", "Підпишись")

def load_posted_links():
    if not os.path.exists(POSTED_LINKS_FILE):
        return set()
    with open(POSTED_LINKS_FILE, "r") as f:
        return set(line.strip() for line in f)

def save_posted_link(link):
    with open(POSTED_LINKS_FILE, "a") as f:
        f.write(link + "\n")

if __name__ == "__main__":
    print("Скрипт запущен — починаємо обробку RSS")
    posted_links = load_posted_links()

    for feed_url in RSS_FEEDS:
        print(f"Потік: {feed_url}")
        feed = feedparser.parse(feed_url)

        for entry in feed.entries[:10]:
            if not hasattr(entry, 'published_parsed'):
                print(f"Пропущено: немає дати — {entry.get('title', '')}")
                continue

            published = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            if datetime.now() - published > timedelta(hours=96):
                print(f"Пропущено: стара новина — {entry.get('title', '')}")
                continue

            title = entry.get("title", "[Без заголовка]")
            summary = re.sub('<[^<]+?>', '', entry.get("summary", ""))
            link = entry.get("link", "[Без посилання]")

            if link in posted_links:
                print(f"Пропущено: вже було — {title}")
                continue

            combined_text = f"{title} {summary}".lower()

            if not any(keyword.lower() in combined_text for keyword in KEYWORDS):
                print(f"Пропущено: не по ключовим словам — {title}")
                continue

            if any(pattern in combined_text for pattern in EXCLUDE_PATTERNS):
                print(f"Пропущено: побут/ДТП — {title}")
                continue

            print(f"[OK] {title}\n{link}\n")

            source = extract_source(link)
            rewritten = rewrite_news(title, summary, source)
            send_message_safe(rewritten)
            save_posted_link(link)

        time.sleep(1)
