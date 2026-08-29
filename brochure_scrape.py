"""Find + download event brochure PDFs and pull sponsor names/emails/phones out of them.

Brochures are often where the real sponsor tier list and contact details live, more so
than the homepage. This is conservative on purpose: an email/phone is only attributed to a
specific company if it appears on the same or next line as that company's name in the PDF
text — otherwise it's kept as a general (unattributed) contact for the event, rather than
risking a wrong attribution like the Bleep/Internshala mixup found earlier in web_enrich.
"""
import io
import os
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from scrape_sponsors import DATE_RE, EMAIL_RE, NAV_JUNK_RE, PHONE_RE, SPONSOR_HEADING_RE

BROCHURE_LINK_RE = re.compile(r"brochure|\.pdf($|\?)", re.I)
MAX_PDF_BYTES = 60 * 1024 * 1024  # 60 MB safety cap — image-heavy brochures run large

# ponytail: a single capitalized word ("Schedule") is structurally identical to a company name
# ("Unstop") — this blocklist of common brochure section titles is the cheap fix, not a real
# grammar; a genuinely unlucky company name matching one of these would be missed
SECTION_TITLE_RE = re.compile(
    r"^(schedule|agenda|timeline|faq|speakers?|judges?|prizes?|track|about|team|contact"
    r"|register|committee|organi[sz]ers?|rules?|eligibility|awards?)\b", re.I
)


def find_brochure_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        haystack = f"{a['href']} {a.get_text(strip=True)}"
        if BROCHURE_LINK_RE.search(haystack):
            links.add(urljoin(base_url, a["href"]))
    return links


def download_pdf_text(url):
    try:
        resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
        resp.raise_for_status()
        if "pdf" not in resp.headers.get("Content-Type", "").lower() and not url.lower().endswith(".pdf"):
            return None
        content = resp.raw.read(MAX_PDF_BYTES + 1, decode_content=True)
        if len(content) > MAX_PDF_BYTES:
            return None
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except (requests.RequestException, Exception) as e:
        print(f"  brochure fetch/parse failed for {url}: {e}")
        return None


def _looks_like_company(line):
    line = line.strip()
    if not (2 <= len(line) <= 60):
        return False
    if EMAIL_RE.search(line) or PHONE_RE.search(line):
        return False
    if NAV_JUNK_RE.match(line) or DATE_RE.match(line) or SECTION_TITLE_RE.match(line):
        return False
    return bool(re.match(r"^[A-Z][A-Za-z0-9&.\-' ]+$", line))


def extract_sponsors_from_text(text, source_url):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    rows = []

    sponsor_zone = False
    for i, line in enumerate(lines):
        if SPONSOR_HEADING_RE.search(line) and len(line) < 40:
            sponsor_zone = True
            continue
        if not sponsor_zone:
            continue

        is_contact_line = bool(EMAIL_RE.fullmatch(line) or PHONE_RE.fullmatch(line))
        if not _looks_like_company(line):
            if not is_contact_line:
                sponsor_zone = False  # hit unrelated content (e.g. a new section) — end the zone
            continue

        # attribute an email/phone only if it's on this line or the very next one
        nearby = " ".join(lines[i : i + 2])
        emails = EMAIL_RE.findall(nearby)
        phones = PHONE_RE.findall(nearby)
        rows.append({
            "event_url": source_url,
            "company": line,
            "contact_name": "",
            "email": emails[0] if emails else "",
            "phone": phones[0] if phones else "",
            "linkedin_url": "",
            "contact_source": source_url,
        })

    return rows


def scrape_brochures_for_url(event_url, html):
    rows = []
    for pdf_url in find_brochure_links(html, event_url):
        print(f"  found brochure link: {pdf_url}")
        text = download_pdf_text(pdf_url)
        if not text:
            continue
        rows.extend(extract_sponsors_from_text(text, pdf_url))
    return rows
