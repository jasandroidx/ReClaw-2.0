"""Socrata scraper helpers."""

from tools.socrata_scraper import SocrataScraper, _guess_amount_column
import pandas as pd


def test_guess_amount_column():
    df = pd.DataFrame({"Payment Amount": [100, 200], "vendor": ["A", "B"]})
    assert _guess_amount_column(df) == "Payment Amount"


def test_domain_normalization():
    s = SocrataScraper("https://data.example.gov/", "abcd-1234")
    assert s.domain == "data.example.gov"
    assert "abcd-1234" in s.base_url