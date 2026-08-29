"""Minimal self-check for the company-domain email filter — run with: python test_web_enrich.py"""
from web_enrich import _company_emails


def test_rejects_unrelated_host_email():
    assert _company_emails(["complaints@internshala.com"], "Bleep") == []


def test_accepts_matching_domain():
    assert _company_emails(["info@exfinityventures.com"], "Exfinity") == ["info@exfinityventures.com"]
    assert _company_emails(["finance@henryharvin.com"], "Henry Harvin") == ["finance@henryharvin.com"]


if __name__ == "__main__":
    test_rejects_unrelated_host_email()
    test_accepts_matching_domain()
    print("OK")
