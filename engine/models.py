"""RiskRadar - core data structures.

Two small dataclasses carry everything through the pipeline:

    NewsItem  -> raw unstructured text entering the engine
    Signal    -> the structured, machine-readable risk signal leaving it

Keeping these in one place makes the whole system easy to reason about.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional
import time
import uuid


@dataclass
class NewsItem:
    """A single piece of unstructured content pulled from any source."""
    id: str
    source: str              # "news" | "social" | ...
    source_name: str         # e.g. "Reuters", "X (Twitter) - @handle"
    text: str                # the raw text we analyze
    url: str = ""
    published_at: str = ""   # ISO timestamp from the source (if any)

    @classmethod
    def from_dict(cls, d: dict) -> "NewsItem":
        # Sources may give us "title", "text" or both - we just concatenate,
        # because both headline and body carry sentiment.
        text = " ".join(x for x in [d.get("title", ""), d.get("text", "")] if x).strip()
        return cls(
            id=str(d.get("id") or uuid.uuid4().hex[:10]),
            source=str(d.get("source", "unknown")),
            source_name=str(d.get("source_name", d.get("source", "unknown"))),
            text=text,
            url=str(d.get("url", "")),
            published_at=str(d.get("published_at", "")),
        )


@dataclass
class CompanyMention:
    ticker: str
    name: str
    sector: str


@dataclass
class Signal:
    """The structured output of the Risk Engine for one NewsItem."""
    signal_id: str
    ts: float                                    # processing time (epoch)
    item_id: str
    source: str
    source_name: str
    text: str
    url: str
    # --- the three required output fields -------------------------------
    sentiment: float                             # -1.0 .. 1.0
    event_type: str                              # e.g. "Credit Event"
    impact: float                                 # 1 .. 10
    # --- supporting detail (makes every score explainable) --------------
    sentiment_label: str = "neutral"              # positive / negative / neutral
    companies: List[CompanyMention] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)   # why this event class
    impact_drivers: List[str] = field(default_factory=list)     # why this impact score
    risk_flag: str = "none"                       # none / watch / high

    def to_dict(self) -> dict:
        d = asdict(self)
        d["companies"] = [{"ticker": c.ticker, "name": c.name, "sector": c.sector}
                          for c in self.companies]
        d["ts_iso"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.ts))
        return d
