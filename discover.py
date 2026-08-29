"""Find Hyderabad E-Summit event website URLs via web search, cache them in data/seeds.csv."""
import csv
import os

from ddgs import DDGS

SEEDS_PATH = os.path.join("data", "seeds.csv")

QUERIES = [
    "E-Summit Hyderabad sponsors",
    "E-Summit Hyderabad partners",
    "E-Cell Hyderabad E-Summit",
    "E-Summit IIT Hyderabad sponsors",
    "E-Summit BITS Hyderabad sponsors",
    "E-Summit ISB Hyderabad sponsors",
]

# ponytail: keyword filter is a naive heuristic, tighten if false positives pile up
KEYWORDS = ("e-summit", "esummit", "e summit")
HYDERABAD_KEYWORDS = ("hyderabad", "iiit.ac.in", "iith.ac.in", "isb.edu", "lords.ac.in")

# news/press coverage and social feeds never list sponsor contact details, only official event
# sites do — skip the former so we don't waste scrape time on pages that can't have leads
NON_LEAD_DOMAINS = (
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com/posts",
    "linkedin.com/feed", "news.", "aglasem.com", "startupstorymedia.com", "mystartupnews.in",
    "startuphyderabad.com", "exhibit.tech", "krctimes.com", "knowafest.com", "f6s.com",
    "all.events",
)


def load_seeds():
    if not os.path.exists(SEEDS_PATH):
        return set()
    with open(SEEDS_PATH, newline="", encoding="utf-8") as f:
        return {row["url"] for row in csv.DictReader(f)}


def save_seeds(urls):
    os.makedirs("data", exist_ok=True)
    with open(SEEDS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["url"])
        for url in sorted(urls):
            writer.writerow([url])


def discover(max_results_per_query=10):
    seeds = load_seeds()
    before = len(seeds)
    with DDGS() as ddgs:
        for query in QUERIES:
            for result in ddgs.text(query, max_results=max_results_per_query):
                url = result.get("href") or result.get("link")
                if not url:
                    continue
                haystack = f"{url} {result.get('title', '')} {result.get('body', '')}".lower()
                if any(k in url.lower() for k in NON_LEAD_DOMAINS):
                    continue
                if any(k in haystack for k in KEYWORDS) and any(k in haystack for k in HYDERABAD_KEYWORDS):
                    seeds.add(url)
    save_seeds(seeds)
    print(f"Discovered {len(seeds) - before} new event URL(s), {len(seeds)} total in {SEEDS_PATH}")
    return seeds


if __name__ == "__main__":
    discover()
