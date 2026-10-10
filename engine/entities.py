"""Company dictionary + lightweight entity extraction.

We maintain a hand-curated dictionary of the 20 companies in our mock index
(a subset of the S&P 100, spread across sectors). Extraction is simple
case-insensitive keyword matching with word boundaries - deliberately not a
full NER model. For a hackathon index of 20 names this is fast, transparent
and has zero false positives on names like "Apple" inside other words.

Each company carries aliases so "Google" maps to Alphabet (GOOGL), etc.
"""
import re
from typing import List

from .models import CompanyMention

# ticker -> (name, sector, aliases)
COMPANIES = {
    "AAPL": ("Apple",             "Technology",   ["apple", "iphone", "macbook"]),
    "MSFT": ("Microsoft",         "Technology",   ["microsoft", "azure"]),
    "NVDA": ("Nvidia",            "Technology",   ["nvidia", "$nvda"]),
    "AMZN": ("Amazon",            "Consumer",    ["amazon", "prime day", "aws"]),
    "GOOGL": ("Alphabet",         "Technology",  ["alphabet", "google", "android"]),
    "META": ("Meta Platforms",    "Technology",   ["meta", "facebook", "instagram"]),
    "TSLA": ("Tesla",             "Auto",        ["tesla", "$tsla"]),
    "JPM":  ("JPMorgan Chase",    "Financials",   ["jpmorgan", "jp morgan", "jpm"]),
    "BAC":  ("Bank of America",   "Financials",   ["bank of america", "bofa", "$bac"]),
    "GS":   ("Goldman Sachs",     "Financials",   ["goldman sachs", "goldman"]),
    "XOM":  ("Exxon Mobil",       "Energy",       ["exxon", "exxon mobil", "$xom"]),
    "CVX":  ("Chevron",           "Energy",       ["chevron", "$cvx"]),
    "JNJ":  ("Johnson & Johnson", "Healthcare",   ["johnson & johnson", "j&j", "jnj"]),
    "PFE":  ("Pfizer",            "Healthcare",   ["pfizer"]),
    "KO":   ("Coca-Cola",         "Consumer",     ["coca-cola", "coke", "coca cola"]),
    "MCD":  ("McDonald's",        "Consumer",     ["mcdonald", "mcdonalds", "mcd"]),
    "WMT":  ("Walmart",           "Consumer",     ["walmart", "$wmt"]),
    "DIS":  ("Walt Disney",       "Media",        ["disney", "disney+", "hulu"]),
    "BA":   ("Boeing",            "Industrial",   ["boeing", "737"]),
    "CAT":  ("Caterpillar",       "Industrial",   ["caterpillar", "$cat"]),
}

# Pre-compile one regex per alias for speed and word-boundary safety.
_ALIAS_RE = {}
for _tk, (_name, _sec, _aliases) in COMPANIES.items():
    for _a in _aliases:
        _ALIAS_RE[_a] = (re.compile(r"(?<![\w$])" + re.escape(_a) + r"(?![\w])"), _tk)

# A couple of common entities we mention but do NOT hold in the index;
# mapping them keeps sentiment flowing into "market-wide" buckets.
WATCHLIST_EXTRA = {
    "V": ("Visa", "Financials", ["visa"]),
    "MA": ("Mastercard", "Financials", ["mastercard"]),
    "AMD": ("AMD", "Technology", ["amd"]),
    "SPY": ("S&P 500", "Index", ["s&p 500", "s&p", "sp500"]),
}


def extract_companies(text: str, include_watchlist: bool = True) -> List[CompanyMention]:
    """Find every company mentioned in `text` (order preserved, no duplicates)."""
    text_l = text.lower()
    found, seen = [], set()
    pool = dict(_ALIAS_RE)
    if include_watchlist:
        for tk, (_n, _s, aliases) in WATCHLIST_EXTRA.items():
            for a in aliases:
                pool[a] = (re.compile(r"(?<![\w$])" + re.escape(a) + r"(?![\w])"), tk)

    for alias, (regex, ticker) in pool.items():
        if ticker in seen:
            continue
        if regex.search(text_l):
            info = COMPANIES.get(ticker) or WATCHLIST_EXTRA.get(ticker)
            if info:
                seen.add(ticker)
                found.append(CompanyMention(ticker=ticker, name=info[0], sector=info[1]))
    return found
