"""Fill missing email/phone for sponsor rows via general web search (not just LinkedIn).

For each sponsor company still missing contact info, searches the web for its contact
email/press-contact/phone number and scrapes the top results for anything concrete
(a published email/phone). Always keeps the source URL so the team can verify before
using it. Deliberately doesn't try to guess a named person's name from these generic
pages — unlike a LinkedIn profile, a company contact page rarely names an actual
individual, so that heuristic just produced noise ("Contact Us", "Query Java", etc)
in testing and was dropped rather than shipped.
"""
import csv
import os
import re

from bs4 import BeautifulSoup
from ddgs import DDGS

from scrape_sponsors import EMAIL_RE, PHONE_RE, fetch_html

CACHE_PATH = os.path.join("data", "sponsors_cache.csv")
FIELDS = ["event_url", "company", "contact_name", "email", "phone", "linkedin_url", "contact_source"]

MAX_RESULTS_PER_QUERY = 3

# third-party lead-database/people-search sites show email-format templates, redacted
# placeholders, or paywalled guesses — not real published addresses — so they're worse than
# useless here; only trust emails/phones found on the company's own pages or real coverage of it
UNRELIABLE_DOMAINS = ("leadiq.com", "prospeo.io", "contactout.com", "zoominfo.com", "rocketreach.co", "signalhire.com")


def load_rows():
    if not os.path.exists(CACHE_PATH):
        return []
    with open(CACHE_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r.setdefault("contact_source", "")
    return rows


def save_rows(rows):
    with open(CACHE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def search_web(company, max_results=MAX_RESULTS_PER_QUERY):
    queries = [
        f"{company} contact email",
        f"{company} press contact",
        f"{company} contact number Hyderabad",
    ]
    urls = []
    with DDGS() as ddgs:
        for q in queries:
            for r in ddgs.text(q, max_results=max_results):
                url = r.get("href")
                if url and not any(d in url.lower() for d in UNRELIABLE_DOMAINS):
                    urls.append(url)
    return urls


def _normalize(name):
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _company_emails(emails, company):
    """Third-party listing/aggregator pages often surface the *host site's* support email
    (e.g. an Internshala company-profile page returning Internshala's own address) instead of
    the target company's — only trust an email whose domain actually relates to the company."""
    token = _normalize(company)
    return [e for e in emails if token in _normalize(e.split("@", 1)[1])]


def find_contact_details(company):
    """Returns (email, phone, source_url) — any field may be empty."""
    for url in search_web(company):
        html = fetch_html(url)
        if not html:
            continue
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)

        emails = _company_emails(EMAIL_RE.findall(text), company)
        phones = PHONE_RE.findall(text)
        if emails or phones:
            return emails[0] if emails else "", phones[0] if phones else "", url
    return "", "", ""


def enrich(dry_run=False):
    rows = load_rows()
    targets = [r for r in rows if not r.get("email") and not r.get("phone")]

    if not targets:
        print("Nothing to enrich.")
        return

    if dry_run:
        print(f"Would search the web for {len(targets)} compan(ies):")
        for r in targets:
            print(f"  - {r['company']}")
        return

    for row in targets:
        print(f"Searching the web for {row['company']}")
        email, phone, source = find_contact_details(row["company"])
        if email or phone:
            row["email"], row["phone"], row["contact_source"] = email, phone, source
            print(f"  found: email={email!r} phone={phone!r} (source: {source})")
        else:
            print("  nothing found")

    save_rows(rows)
    print(f"Updated {len(targets)} row(s) in {CACHE_PATH}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    enrich(dry_run=args.dry_run)
