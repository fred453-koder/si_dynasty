import requests

RSS_FEEDS = [
    "http://www.xinhuanet.com/english/rss/worldrss.xml",     # Китай — часто блокируется
    "https://www.cgtn.com/rss/World.xml",                    # CGTN — может быть недоступен
    "https://www.scmp.com/rss/91/feed",                      # SCMP — частично доступен
    "https://feeds.bbci.co.uk/news/rss.xml",                 # BBC — почти всегда доступен
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml" # NYT — доступен
]

for url in RSS_FEEDS:
    try:
        response = requests.get(url, timeout=5)
        print(f"{url} — Status: {response.status_code}")
    except Exception as e:
        print(f"{url} — ❌ Error: {e}")
