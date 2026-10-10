"""The RiskEngine itself - orchestration of ingest -> analyze -> publish.

Design: a classic publish/subscribe core. The engine processes each item,
builds a Signal, stores it, and notifies every subscriber (Module A and
Module B both subscribe this way). This decoupling is what makes the
"downstream modules" trivially pluggable - they never talk to sources,
they just react to signals.
"""
import logging
import threading
import time
from typing import Callable, List

from .models import NewsItem, Signal
from .providers import get_provider
from .impact import risk_flag

log = logging.getLogger("riskradar.engine")


class RiskEngine:
    def __init__(self, store=None):
        self.provider = get_provider()
        self.store = store
        self.subscribers: List[Callable[[Signal], None]] = []
        self.signals: List[Signal] = []          # in-memory recent window
        self.source_status: dict = {}            # source -> "active"/"inactive"
        self._lock = threading.Lock()
        self.processed = 0

    # ------------------------------------------------------------------ #
    def subscribe(self, fn: Callable[[Signal], None]):
        """Downstream modules call this to receive every new signal."""
        self.subscribers.append(fn)

    def mark_source(self, name: str, status: str):
        self.source_status[name] = status

    # ------------------------------------------------------------------ #
    def process(self, item: NewsItem) -> Signal:
        """The core path: unstructured text in, structured signal out."""
        t0 = time.time()
        sentiment, event_type, impact, detail = self.provider.analyze(item.text)

        signal = Signal(
            signal_id=f"sig_{int(time.time()*1000)}_{item.id}",
            ts=time.time(),
            item_id=item.id,
            source=item.source,
            source_name=item.source_name,
            text=item.text,
            url=item.url,
            sentiment=sentiment,
            event_type=event_type,
            impact=impact,
            sentiment_label=detail["sentiment_label"],
            companies=detail["companies"],
            matched_keywords=detail["matched_keywords"],
            impact_drivers=detail["impact_drivers"],
            risk_flag=risk_flag(sentiment, impact),
        )

        with self._lock:
            self.signals.append(signal)
            self.signals = self.signals[-500:]          # keep last 500
            self.processed += 1

        if self.store:
            self.store.save(signal)

        for fn in self.subscribers:                     # notify modules
            try:
                fn(signal)
            except Exception:
                log.exception("subscriber failed")

        log.debug("processed %s in %.1fms", item.id, (time.time() - t0) * 1000)
        return signal

    # ------------------------------------------------------------------ #
    # convenience views used by the API / dashboard
    def recent(self, n: int = 50) -> List[Signal]:
        with self._lock:
            return list(reversed(self.signals[-n:]))

    def stats(self) -> dict:
        with self._lock:
            sigs = self.signals
        if not sigs:
            return {"processed": 0}
        by_event = {}
        by_source = {}
        sentiments = []
        for s in sigs:
            by_event[s.event_type] = by_event.get(s.event_type, 0) + 1
            by_source[s.source] = by_source.get(s.source, 0) + 1
            sentiments.append(s.sentiment)
        return {
            "processed": self.processed,
            "recent_window": len(sigs),
            "avg_sentiment": round(sum(sentiments) / len(sentiments), 3),
            "by_event": by_event,
            "by_source": by_source,
            "high_risk": sum(1 for s in sigs if s.risk_flag == "high"),
            "watch": sum(1 for s in sigs if s.risk_flag == "watch"),
        }

    def company_sentiment(self) -> dict:
        """Average sentiment + signal count per mentioned company."""
        agg = {}
        with self._lock:
            sigs = list(self.signals)
        for s in sigs:
            for c in s.companies:
                a = agg.setdefault(c.ticker, {
                    "ticker": c.ticker, "name": c.name, "sector": c.sector,
                    "sum": 0.0, "count": 0, "last_impact": 0,
                })
                a["sum"] += s.sentiment
                a["count"] += 1
                a["last_impact"] = max(a["last_impact"], s.impact)
        out = {}
        for tk, a in agg.items():
            out[tk] = {
                "ticker": a["ticker"], "name": a["name"], "sector": a["sector"],
                "avg_sentiment": round(a["sum"] / a["count"], 3),
                "count": a["count"], "last_impact": a["last_impact"],
            }
        return out

    # ------------------------------------------------------------------ #
    def start_sources(self, sources) -> List[threading.Thread]:
        """Run every source in its own daemon thread, pushing into us."""
        threads = []
        for src in sources:
            def worker(s=src):
                # try a quick connectivity probe for live connectors
                try:
                    if hasattr(s, "key") and getattr(s, "key", "") == "":
                        self.mark_source(s.name, "inactive (no key set)")
                    else:
                        self.mark_source(s.name, "active")
                except Exception:
                    self.mark_source(s.name, "active")
                while True:
                    try:
                        s.run(self.process)
                        break
                    except Exception:
                        log.exception("source %s crashed; restarting", s.name)
                        time.sleep(3)
            t = threading.Thread(target=worker, name=f"src-{src.name}", daemon=True)
            t.start()
            threads.append(t)
        return threads
