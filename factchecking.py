import feedparser
import requests
import argparse
import os
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")


RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best",
    "https://apnews.com/hub/ap-top-news?format=xml"
]


def fetch_rss_articles():
    articles = []
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:  # limit to 10 each
            articles.append({
                "title": entry.get("title", ""),
                "summary": entry.get("summary", ""),
                "link": entry.get("link", "")
            })
    return articles


def fetch_newsapi_articles(query):
    if not NEWSAPI_KEY:
        return []

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "relevancy",
        "pageSize": 10,
        "apiKey": NEWSAPI_KEY
    }

    r = requests.get(url, params=params)
    data = r.json()

    if data.get("status") != "ok":
        return []

    articles = []
    for a in data.get("articles", []):
        articles.append({
            "title": a.get("title"),
            "summary": a.get("description"),
            "link": a.get("url")
        })
    return articles


def score_relevance(claim, article):
    claim_words = set(claim.lower().split())
    title_words = set(article["title"].lower().split())
    overlap = len(claim_words & title_words)
    return overlap


def fact_check(claim):
    print("\n🔍 Checking claim:", claim)

    rss_results = fetch_rss_articles()
    api_results = fetch_newsapi_articles(claim)

    all_articles = rss_results + api_results

    # Score and filter
    scored = []
    for art in all_articles:
        score = score_relevance(claim, art)
        if score > 0:
            scored.append((score, art))

    scored.sort(reverse=True, key=lambda x: x[0])

    return scored[:5]  # top 5


def main():
    parser = argparse.ArgumentParser(description="Simple fact-checking CLI")
    parser.add_argument("claim", type=str, help="Headline or claim to check")
    args = parser.parse_args()

    results = fact_check(args.claim)

    if not results:
        print("\n❗ No relevant news found.")
        return

    print("\n📌 Results:")
    for score, art in results:
        print("\n-----------------------------")
        print("Score:", score)
        print("Title:", art["title"])
        print("Summary:", art["summary"])
        print("Link:", art["link"])


if __name__ == "__main__":
    main()
