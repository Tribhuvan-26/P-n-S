"""Fill missing LinkedIn contact for sponsor rows that don't already have one.

WARNING: automating LinkedIn goes against its Terms of Service and can get an
account rate-limited or restricted. This keeps volume low and adds delays,
but the risk is not eliminated. Use sparingly.
"""
import argparse
import csv
import os
import random
import re
import time

from dotenv import load_dotenv

load_dotenv()

CACHE_PATH = os.path.join("data", "sponsors_cache.csv")
STATE_PATH = os.path.join("data", "storage_state.json")
FIELDS = ["event_url", "company", "contact_name", "email", "phone", "linkedin_url", "contact_source"]

MAX_LOOKUPS_PER_RUN = 15
MIN_DELAY, MAX_DELAY = 8, 20


def load_rows():
    if not os.path.exists(CACHE_PATH):
        return []
    with open(CACHE_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_rows(rows):
    with open(CACHE_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def search_query(company):
    return f'"{company}" Hyderabad marketing OR partnerships OR sponsorship'


def ensure_logged_in(page):
    page.goto("https://www.linkedin.com/feed/", timeout=30000)
    if "login" not in page.url and "checkpoint" not in page.url:
        return

    email = os.environ.get("LINKEDIN_EMAIL")
    password = os.environ.get("LINKEDIN_PASSWORD")
    if email and password and "login" in page.url:
        page.goto("https://www.linkedin.com/login", timeout=30000)
        page.locator("input[autocomplete='username']:visible").first.fill(email)
        page.locator("input[autocomplete='current-password']:visible").first.fill(password)
        page.get_by_role("button", name="Sign in", exact=True).first.click()
        page.wait_for_timeout(4000)

    # LinkedIn 2FA/CAPTCHA checkpoints can't be automated — fall back to manual for those
    if "login" in page.url or "checkpoint" in page.url:
        print("Please finish logging into LinkedIn in the opened browser window, then press Enter here...")
        input()


# ponytail: catches "Indian Bank" false-matching inside "South Indian Bank"; won't catch every
# naming collision (e.g. a suffix like "Amazon Web Services") — spot-check matches before trusting them
_CONNECTOR_WORDS = {"the", "at", "for", "of", "with", "by", "and", "@", "-", "|"}


def _mentions_company_standalone(card_text, company):
    for m in re.finditer(re.escape(company), card_text, re.I):
        stripped = card_text[: m.start()].rstrip()
        if not stripped or stripped[-1] in ",|•:-\n":
            return True  # clear separator right before the company name (e.g. "Officer, Amazon")
        prev_word = stripped.split()[-1]
        if prev_word[0].isupper() and prev_word.lower() not in _CONNECTOR_WORDS:
            continue  # likely part of a longer company name (e.g. "South " + "Indian Bank")
        return True
    return False


def _find_verified_match(page, company, max_candidates=10):
    """LinkedIn's keyword search often ignores an unmatched company name and falls back to
    generic results, so we don't trust the top hit blindly — only accept a profile whose own
    result card actually mentions the company on its own (current role, headline, etc)."""
    links = page.query_selector_all("a[href*='/in/']")[:max_candidates]
    for link in links:
        card = link.evaluate_handle("el => el.closest('li') || el.parentElement").as_element()
        if not card:
            continue
        card_text = card.inner_text()
        if not _mentions_company_standalone(card_text, company):
            continue
        name_el = link.query_selector("span[aria-hidden='true']")
        name = name_el.inner_text() if name_el else card_text.split("\n")[0]
        return link.get_attribute("href").split("?")[0], name
    return None


def enrich(dry_run=False):
    rows = load_rows()
    targets = [r for r in rows if not r.get("linkedin_url")][:MAX_LOOKUPS_PER_RUN]

    if not targets:
        print("Nothing to enrich.")
        return

    if dry_run:
        print(f"Would run {len(targets)} LinkedIn search(es):")
        for r in targets:
            print(f"  - {search_query(r['company'])}")
        return

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context_kwargs = {}
        if os.path.exists(STATE_PATH):
            context_kwargs["storage_state"] = STATE_PATH

        browser = p.chromium.launch(headless=False)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        ensure_logged_in(page)
        context.storage_state(path=STATE_PATH)

        for row in targets:
            query = search_query(row["company"])
            print(f"Searching LinkedIn: {query}")
            page.goto(f"https://www.linkedin.com/search/results/people/?keywords={query}", timeout=30000)
            page.wait_for_timeout(3000)

            match = _find_verified_match(page, row["company"])
            if match:
                row["linkedin_url"], row["contact_name"] = match
                print(f"  found: {row['contact_name']} -> {row['linkedin_url']}")
            else:
                print(f"  no result mentioned '{row['company']}' by name — skipping rather than guessing")

            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        browser.close()

    save_rows(rows)
    print(f"Updated {len(targets)} row(s) in {CACHE_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    enrich(dry_run=args.dry_run)
