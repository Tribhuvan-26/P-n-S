"""Minimal self-check for brochure text extraction — run with: python test_brochure_scrape.py"""
from brochure_scrape import extract_sponsors_from_text

SAMPLE_TEXT = """
E-Summit 2026
About the event
This year we welcome founders from across the country.

Our Sponsors
Acme Corp
contact@acme.com
Beta Industries
Gamma Labs
gamma@labs.io

Schedule
9:00 AM Registration
"""


def test_extracts_companies_in_sponsor_zone():
    rows = extract_sponsors_from_text(SAMPLE_TEXT, "https://example.com/brochure.pdf")
    companies = {r["company"] for r in rows}
    assert companies == {"Acme Corp", "Beta Industries", "Gamma Labs"}, companies


def test_attributes_email_only_to_nearby_company():
    rows = extract_sponsors_from_text(SAMPLE_TEXT, "https://example.com/brochure.pdf")
    by_company = {r["company"]: r for r in rows}
    assert by_company["Acme Corp"]["email"] == "contact@acme.com"
    assert by_company["Gamma Labs"]["email"] == "gamma@labs.io"
    assert by_company["Beta Industries"]["email"] == ""


def test_ignores_non_sponsor_sections():
    rows = extract_sponsors_from_text(SAMPLE_TEXT, "https://example.com/brochure.pdf")
    companies = {r["company"] for r in rows}
    assert "About the event" not in companies
    assert "Schedule" not in companies


if __name__ == "__main__":
    test_extracts_companies_in_sponsor_zone()
    test_attributes_email_only_to_nearby_company()
    test_ignores_non_sponsor_sections()
    print("OK")
