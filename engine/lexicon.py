"""Finance-tuned sentiment lexicon.

VADER is our base sentiment engine. It was originally built for social media,
which is exactly why we picked it: it handles slang, ALL-CAPS, emoji and
negation ("not good") out of the box, which matters a lot for the tweet side
of our data. It is also instant on CPU, so the demo runs live.

But VADER's general lexicon does not know finance jargon - words like
"downgrade", "contagion", "buyback" or "guidance" are neutral to it. So we
extend its lexicon with a curated finance lexicon. Every entry below was
added by hand after looking at what our sample feeds actually contained.
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# word -> added valence (-4 .. +4 scale, same as VADER's own lexicon)
FINANCE_LEXICON = {
    # --- strong negatives -------------------------------------------------
    "bankruptcy": -3.5, "bankrupt": -3.5, "insolvency": -3.4, "chapter 11": -3.4,
    "default": -3.0, "defaulted": -3.0, "defaults": -2.8,
    "downgrade": -2.6, "downgraded": -2.6, "downgrades": -2.6,
    "fraud": -3.6, "scandal": -3.0, "probe": -2.2, "lawsuit": -2.4,
    "litigation": -2.2, "investigation": -2.4, "charges": -2.0,
    "recall": -2.6, "contamination": -3.0, "contagion": -2.8,
    "layoffs": -2.4, "restructuring": -1.8, "profit warning": -3.2,
    "warning": -1.8, "selloff": -2.6, "plunge": -2.8, "plunged": -2.8,
    "slump": -2.2, "crash": -3.0, "recession": -2.8, "downturn": -2.4,
    "shortage": -2.0, "disruption": -1.8, "misses": -1.6, "miss": -1.4,
    "antitrust": -2.2, "sanctions": -2.8, "tariff": -2.2, "tariffs": -2.2,
    "trade war": -2.6, "subprime": -2.4, "ransomware": -3.0, "breach": -2.4,
    "cyberattack": -2.8, "unemployment": -2.0, "wiped out": -3.4,
    "getting wrecked": -3.0, "nightmare": -2.6, "terrifying": -2.4,
    "not good": -2.4, "contagion risk": -3.0, "getting nervous": -2.0,
    "provision": -1.2, "haircut": -1.8, "halting": -1.6, "delay": -1.6,
    "delays": -1.8, "volatile": -1.4, "volatility": -1.6, "cracking": -1.8,
    "weakening": -1.8, "pressured": -1.6, "concerns": -1.6, "worries": -1.8,
    "gloom": -2.0, "headwinds": -1.4, "overdone": -1.0, "fears": -2.0,

    # --- strong positives -------------------------------------------------
    "record": 2.4, "surge": 2.6, "surged": 2.6, "rally": 2.4, "rallied": 2.4,
    "beat": 2.2, "beats": 2.4, "crushed": 2.4, "upgrade": 2.4, "upgraded": 2.4,
    "buyback": 2.6, "dividend": 2.2, "profitable": 2.4, "approval": 2.6,
    "approved": 2.4, "breakthrough": 2.8, "expansion": 1.8, "accelerates": 2.0,
    "accelerated": 2.0, "rebound": 2.0, "rebounded": 2.0, "wins": 2.4,
    "won": 2.2, "unveils": 1.6, "debuts": 1.6, "launch": 1.6, "growth": 2.0,
    "milestone": 2.2, "banger": 2.2, "insane": 2.2, "off the charts": 2.6,
    "to the moon": 2.8, "bullish": 2.4, "soft landing": 2.0, "steady": 1.4,
    "strong": 2.0, "success": 2.2, "profit": 2.0, "boosting": 1.8,
    "boosts": 1.8, "boost": 1.6, "gains": 1.8, "upturn": 1.6, "upside": 1.6,
    "turnaround": 1.8, "quietly having a great": 2.2, "steadi": 1.2,
    "humbled" : -0.8, "safe": 0.8, "defensive": 0.4,
}

_analyzer.lexicon.update(FINANCE_LEXICON)


def score_sentiment(text: str) -> float:
    """Return sentiment in [-1, 1] (VADER compound score)."""
    return round(float(_analyzer.polarity_scores(text)["compound"]), 4)


def label_sentiment(score: float) -> str:
    """Map a numeric score onto a human label (thresholds tuned by hand)."""
    if score >= 0.15:
        return "positive"
    if score <= -0.15:
        return "negative"
    return "neutral"
