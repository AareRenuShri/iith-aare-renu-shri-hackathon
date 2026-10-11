"""Module A - Tactical Index Rebalancing (sentiment-driven).

Subscribes to the Sentiment Score stream from the Risk Engine and tilts a
mock index of 20 large caps (subset of the S&P 100) accordingly:

    positive sentiment  ->  weight up
    negative sentiment  ->  weight down

The rebalancing rule (kept deliberately simple and defensible):

    w_new = w_old * (1 + k * sentiment)        # multiplicative tilt, k = 0.25
    w     = clamp(w, 2%, 12%)                  # position limits (risk control)
    w    /= sum(w)                            # renormalize to 100%

The multiplicative form means a stock needs *positive* sentiment to gain
share and *negative* to lose it, and the 2-12% band stops any single name
from dominating - which is exactly what a real index team would demand.
Every rebalance keeps an audit trail: ticker, sentiment, old weight ->
new weight.
"""
import threading
import time
from typing import Callable, List

from src.engine.entities import COMPANIES
from src.engine.models import Signal

# The mock index: every company in the entities dictionary (20 names,
# one per sector-heavy S&P 100 subset). The "index" starts equal-weighted.
UNIVERSE: List[str] = list(COMPANIES.keys())


class IndexRebalancer:
    def __init__(self, engine, k: float = 0.25,
                 min_w: float = 0.02, max_w: float = 0.12):
        self.engine = engine
        self.k, self.min_w, self.max_w = k, min_w, max_w
        self._lock = threading.Lock()

        n = len(UNIVERSE)
        self.weights = {t: 1.0 / n for t in UNIVERSE}     # current weights
        self.history: List[dict] = []                      # weight snapshots
        self.rebalance_log: List[dict] = []                # audit trail
        self.signals_seen = 0
        self._snapshot("init (equal weight)")

        engine.subscribe(self.on_signal)

    # ------------------------------------------------------------------ #
    def on_signal(self, signal: Signal):
        """Called by the engine for every new signal (the subscription)."""
        tickers = [c.ticker for c in signal.companies if c.ticker in self.weights]
        if not tickers:
            return  # signal not about any index member - nothing to do

        self.signals_seen += 1
        with self._lock:
            for tk in tickers:
                old = self.weights[tk]
                new = old * (1 + self.k * signal.sentiment)
                self.weights[tk] = new
                self.rebalance_log.append({
                    "ts": time.time(), "ticker": tk,
                    "sentiment": signal.sentiment,
                    "event_type": signal.event_type,
                    "impact": signal.impact,
                    "old_w": round(old, 4), "new_w": round(new, 4),
                    "signal_id": signal.signal_id,
                })
            # clamp to position limits, then renormalize
            for tk in self.weights:
                self.weights[tk] = max(self.min_w, min(self.max_w, self.weights[tk]))
            total = sum(self.weights.values())
            for tk in self.weights:
                self.weights[tk] /= total
            self._snapshot(f"{signal.event_type}: {', '.join(tickers)}")

    def _snapshot(self, label: str):
        self.history.append({
            "ts": time.time(), "label": label,
            "weights": {t: round(w, 4) for t, w in self.weights.items()},
        })
        self.history = self.history[-300:]   # keep the chart snappy

    # ------------------------------------------------------------------ #
    def state(self) -> dict:
        with self._lock:
            weights = {t: round(w, 4) for t, w in sorted(
                self.weights.items(), key=lambda kv: -kv[1])}
            hist = self.history[-80:]
            log_ = list(reversed(self.rebalance_log[-25:]))
        return {
            "universe": UNIVERSE,
            "weights": weights,
            "history": hist,
            "rebalance_log": log_,
            "signals_used": self.signals_seen,
            "k": self.k, "min_w": self.min_w, "max_w": self.max_w,
        }
