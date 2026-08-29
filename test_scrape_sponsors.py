"""Minimal self-check for extract_sponsors — run with: python test_scrape_sponsors.py"""
from scrape_sponsors import extract_sponsors

SAMPLE_HTML = """
<html><body>
<section>
  <h2>Our Sponsors</h2>
  <p>Contact: contact@acme.com | +919876543210</p>
  <a href="https://linkedin.com/company/acme">Acme Corp</a>
  <img src="x.png" alt="Beta Industries">
</section>
<section>
  <h2>About the event</h2>
  <p>This has nothing to do with sponsors.</p>
</section>
</body></html>
"""


def test_extracts_company_email_phone_linkedin():
    rows = extract_sponsors(SAMPLE_HTML, "https://example.com/event")
    companies = {r["company"] for r in rows}
    assert "Acme Corp" in companies, rows
    assert "Beta Industries" in companies, rows
    acme = next(r for r in rows if r["company"] == "Acme Corp")
    assert acme["email"] == "contact@acme.com", acme
    assert acme["phone"] == "+919876543210", acme
    assert acme["linkedin_url"] == "https://linkedin.com/company/acme", acme
    print("OK")


if __name__ == "__main__":
    test_extracts_company_email_phone_linkedin()
