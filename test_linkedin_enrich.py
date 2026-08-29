"""Minimal self-check for the company-match validator — run with: python test_linkedin_enrich.py"""
from linkedin_enrich import _mentions_company_standalone


def test_rejects_substring_of_a_different_company():
    assert not _mentions_company_standalone("PROBATIONARY OFFICER-SOUTH INDIAN BANK", "Indian Bank")


def test_accepts_genuine_mentions():
    assert _mentions_company_standalone("Officer at Indian Bank", "Indian Bank")
    assert _mentions_company_standalone("Marketing Lead, Amazon", "Amazon")
    assert _mentions_company_standalone("Indian Bank Probationary Officer", "Indian Bank")


if __name__ == "__main__":
    test_rejects_substring_of_a_different_company()
    test_accepts_genuine_mentions()
    print("OK")
