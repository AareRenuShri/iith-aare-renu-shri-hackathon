"""Impact scoring - how severe is this event, on a 1-10 scale?

We wanted an impact score that a judge can audit in 10 seconds, so it is a
small transparent formula instead of a learned model:

    impact = clamp( base(event_type)            # typical severity of category
                  + urgency      (+1 breaking/flash/just announced)
                  + magnitude    (+1 record/massive/major, -1 minor/slight)
                  + negativity   (+1 if sentiment is strongly negative)
                  + scope       , # +1 if multiple companies / global / nationwide
                  1, 10 )

Every driver is recorded, so each signal ships with its own explanation -
e.g. "8 = base 7 (Credit Event) + 1 breaking + 1 strongly negative".
"""
import re
from typing import List

# Typical severity per event category (domain judgement, documented in report)
BASE_IMPACT = {
    "Credit Event": 7.0,
    "Geopolitical": 6.5,
    "Macroeconomic": 6.0,
    "Cybersecurity": 5.5,
    "Merger/Acquisition": 5.0,
    "Regulatory/Legal": 5.0,
    "Market Volatility": 4.5,
    "Supply Chain": 4.0,
    "Operational/Quality": 4.5,
    "Earnings": 3.5,
    "Product Launch": 3.0,
    "Other": 2.5,
}

URGENT_WORDS = ["breaking", "flash", "just announced", "surprise", "urgent", "escalates", "escalating"]
MAGNITUDE_UP = ["record", "massive", "major", "historic", "sweeping", "largest", "huge", "global", "nationwide", "$12 billion", "$20 billion", "$30 billion"]
MAGNITUDE_DOWN = ["minor", "slight", "small", "modest", "routine", "quiet"]
SCOPE_WORDS = ["global", "nationwide", "sector", "market", "major us banks", "economy", "contagion", "several", "all"]


def score_impact(event_type: str, sentiment: float, text: str, n_companies: int) -> tuple:
    """Return (impact: float 1-10, drivers: List[str])."""
    text_l = text.lower()
    drivers: List[str] = []

    base = BASE_IMPACT.get(event_type, 3.0)
    drivers.append(f"base {base:g} ({event_type})")
    impact = base

    if any(w in text_l for w in URGENT_WORDS):
        impact += 1.0
        drivers.append("+1 urgency (breaking/surprise)")

    if any(w in text_l for w in MAGNITUDE_UP):
        impact += 1.0
        drivers.append("+1 magnitude (record/massive)")

    if any(w in text_l for w in MAGNITUDE_DOWN):
        impact -= 1.0
        drivers.append("-1 minor")

    if sentiment <= -0.55:
        impact += 1.0
        drivers.append("+1 strongly negative sentiment")
    elif sentiment >= 0.55:
        impact -= 0.5
        drivers.append("-0.5 strongly positive sentiment")

    if n_companies >= 2 or any(w in text_l for w in SCOPE_WORDS):
        impact += 1.0
        drivers.append("+1 broad scope (multi-company / sector-wide)")

    impact = max(1.0, min(10.0, round(impact * 2) / 2))  # clamp + 0.5 steps
    return impact, drivers


def risk_flag(sentiment: float, impact: float) -> str:
    """Simple triage used for the alert ticker on the dashboard."""
    if impact >= 7.0 and sentiment <= -0.3:
        return "high"
    if impact >= 5.0 and sentiment <= -0.15:
        return "watch"
    return "none"
