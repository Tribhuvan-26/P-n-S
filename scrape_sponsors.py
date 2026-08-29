"""Scrape sponsor company names + any published email/phone/LinkedIn links from event pages."""
import csv
import os
import re

import requests
from bs4 import BeautifulSoup

SEEDS_PATH = os.path.join("data", "seeds.csv")
CACHE_PATH = os.path.join("data", "sponsors_cache.csv")
FIELDS = ["event_url", "company", "contact_name", "email", "phone", "linkedin_url", "contact_source"]

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")
SPONSOR_HEADING_RE = re.compile(r"sponsor|partner", re.I)


def load_seeds():
    if not os.path.exists(SEEDS_PATH):
        return []
    with open(SEEDS_PATH, newline="", encoding="utf-8") as f:
        return [row["url"] for row in csv.DictReader(f)]


def load_cache_keys():
    if not os.path.exists(CACHE_PATH):
        return set()
    with open(CACHE_PATH, newline="", encoding="utf-8") as f:
        return {(row["event_url"], row["company"]) for row in csv.DictReader(f)}


def fetch_html(url):
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as e:
        print(f"  fetch failed for {url}: {e}")
        return None


def fetch_html_rendered(url):
    """Fallback for JS-rendered sites where sponsor content isn't in the raw HTML."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, timeout=30000)
        html = page.content()
        browser.close()
        return html


# ponytail: nav-junk filter is a naive blocklist, tighten if a site's menu still leaks through
NAV_JUNK_RE = re.compile(r"^(home|about|our |contact|team|events?|workshops?|blog|login|register|>|\d)", re.I)
DATE_RE = re.compile(
    r"^(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}$", re.I
)


def _section_scope(heading):
    """Elements between a heading and the next heading of the same/higher level (sibling-based, not
    whole-ancestor, so we don't sweep in the entire page's nav/footer via a big wrapping div)."""
    if not re.match(r"^h[1-6]$", heading.name):
        # already a sponsor-tagged container (e.g. <div class="sponsors">) — its own subtree is the scope
        return [heading]
    level = int(heading.name[1])
    scope = [heading]
    for sib in heading.find_next_siblings():
        if re.match(r"^h[1-6]$", sib.name or "") and int(sib.name[1]) <= level:
            break
        scope.append(sib)
    if len(scope) == 1:
        # heading has no useful siblings (e.g. wrapped tightly with content) — fall back to its parent
        parent = heading.find_parent(["section", "div"])
        return [parent] if parent else scope
    return scope


SPONSOR_ASSET_RE = re.compile(r"/sponsors?/([^/\"'?#]+)\.(?:svg|png|jpe?g|webp)", re.I)


def _name_from_filename(filename):
    name = re.sub(r"[-_]+", " ", filename).strip()
    return name.title() if name.islower() or name.isupper() else name


def _sponsor_asset_rows(soup, event_url):
    """Some sites (esp. Next.js) only reference sponsor logos as image file paths
    (e.g. <link rel="preload" href="/sponsors/amazon.svg">), with no alt text or heading."""
    rows = []
    seen = set()
    for tag in soup.find_all(["img", "link", "a"]):
        for attr in ("src", "href"):
            match = SPONSOR_ASSET_RE.search(tag.get(attr, ""))
            if match and match.group(1).lower() not in seen:
                seen.add(match.group(1).lower())
                rows.append({
                    "event_url": event_url,
                    "company": _name_from_filename(match.group(1)),
                    "contact_name": "",
                    "email": "",
                    "phone": "",
                    "linkedin_url": "",
                })
    return rows


def extract_sponsors(html, event_url):
    soup = BeautifulSoup(html, "html.parser")
    rows = _sponsor_asset_rows(soup, event_url)

    headings = [h for h in soup.find_all(re.compile("^h[1-6]$")) if SPONSOR_HEADING_RE.search(h.get_text())]

    # some sites mark the sponsor block by class/id instead of a heading (e.g. <div class="sponsors">)
    def _has_sponsor_attr(tag):
        attrs = " ".join(tag.get("class", []) + [tag.get("id", "")])
        return bool(SPONSOR_HEADING_RE.search(attrs))

    headings += [tag for tag in soup.find_all(_has_sponsor_attr) if tag not in headings]

    for heading in headings:
        scope = _section_scope(heading)
        emails, phones, linkedin_links, candidates = [], [], [], set()

        for el in scope:
            text = el.get_text(" ", strip=True)
            emails += EMAIL_RE.findall(text)
            phones += PHONE_RE.findall(text)

            imgs = ([el] if el.name == "img" else []) + el.find_all("img", alt=True)
            links = ([el] if el.name == "a" else []) + el.find_all("a")

            linkedin_links += [a["href"] for a in links if "linkedin.com" in a.get("href", "")]

            for img in imgs:
                alt = img.get("alt", "").strip()
                if alt and len(alt) < 60 and not NAV_JUNK_RE.match(alt) and not DATE_RE.match(alt):
                    candidates.add(alt)
            for a in links:
                text_a = a.get_text(strip=True)
                if text_a and len(text_a) < 60 and not NAV_JUNK_RE.match(text_a) and not DATE_RE.match(text_a):
                    candidates.add(text_a)

        for company in candidates:
            rows.append({
                "event_url": event_url,
                "company": company,
                "contact_name": "",
                "email": emails[0] if emails else "",
                "phone": phones[0] if phones else "",
                "linkedin_url": linkedin_links[0] if linkedin_links else "",
            })

    return rows


def scrape_all():
    seeds = load_seeds()
    cached_keys = load_cache_keys()
    new_rows = []

    for url in seeds:
        print(f"Scraping {url}")
        html = fetch_html(url)
        rows = extract_sponsors(html, url) if html else []
        if not rows:
            # static HTML had nothing usable (common for JS-rendered sites) — retry with a real browser
            try:
                html = fetch_html_rendered(url)
                rows = extract_sponsors(html, url) if html else []
            except Exception as e:
                print(f"  rendered fetch failed for {url}: {e}")

        if html:
            import brochure_scrape  # deferred: brochure_scrape imports from this module, avoid a cycle

            rows += brochure_scrape.scrape_brochures_for_url(url, html)

        for row in rows:
            key = (row["event_url"], row["company"])
            if key in cached_keys:
                continue
            cached_keys.add(key)
            new_rows.append(row)

    if new_rows:
        write_header = not os.path.exists(CACHE_PATH)
        os.makedirs("data", exist_ok=True)
        with open(CACHE_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if write_header:
                writer.writeheader()
            writer.writerows(new_rows)

    print(f"Added {len(new_rows)} new sponsor row(s) to {CACHE_PATH}")
    return new_rows


if __name__ == "__main__":
    scrape_all()
