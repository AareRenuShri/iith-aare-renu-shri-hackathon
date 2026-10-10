"""Module B - Strategic Portfolio Stress Testing (event-driven).

Subscribes to the Event Classification + Impact Score stream. Whenever a
high-impact event lands (impact >= 7 - the threshold the case study
suggests), I run a simplified stress test over a synthetic wholesale
banking portfolio (defined in data/portfolio.csv):

    Geopolitical  -> equities -12%, credit spreads +180bp, oil-sector stress
    Macroeconomic -> rates +2% across the curve, equities -10%
    Credit Event  -> spreads +250bp, equity -8%, loan haircuts
    Cybersecurity -> equity -6%, one-off operational loss
    Regulatory    -> sector equity -6%, compliance costs
    (default)     -> mild general shock

Position math (first-order, deliberately transparent):
    Bonds/Loans  : dV = -notional * duration * d_rate - notional * d_spread
    Equities     : dV = -notional * pct_shock
    Swaps        : pay-fixed gains when rates rise (+), receive-fixed loses
    CDS sold     : loses when credit spreads widen
    Commitments  : drawdown risk -> small notional haircut

Everything is computed live in Python - no external risk engine - and the
output is a before/after valuation with P&L per asset class, which the
dashboard renders as the "impact of the simulated event".
"""
import csv
import threading
import time
from pathlib import Path
from typing import List

from engine.models import Signal

PORTFOLIO_PATH = Path(__file__).resolve().parent.parent / "data" / "portfolio.csv"

# Shock scenarios per event type: (rate_delta %, spread_delta bp, equity_pct, extra)
SCENARIOS = {
    "Geopolitical":   {"rate": 0.005, "spread": 180, "equity": -0.12, "loan_haircut": 0.01, "label": "Geopolitical shock"},
    "Macroeconomic":  {"rate": 0.020, "spread": 60,  "equity": -0.10, "loan_haircut": 0.01, "label": "Rates shock (+200bp)"},
    "Credit Event":   {"rate": 0.010, "spread": 250, "equity": -0.08, "loan_haircut": 0.03, "label": "Credit shock"},
    "Cybersecurity":  {"rate": 0.000, "spread": 40,  "equity": -0.06, "loan_haircut": 0.005, "label": "Cyber incident"},
    "Regulatory/Legal": {"rate": 0.000, "spread": 50, "equity": -0.06, "loan_haircut": 0.005, "label": "Regulatory action"},
    "Merger/Acquisition": {"rate": 0.000, "spread": 30, "equity": -0.03, "loan_haircut": 0.0, "label": "M&A disruption"},
    "Market Volatility": {"rate": 0.005, "spread": 80, "equity": -0.10, "loan_haircut": 0.01, "label": "Volatility spike"},
    "default":        {"rate": 0.002, "spread": 50,  "equity": -0.04, "loan_haircut": 0.005, "label": "General shock"},
}

TRIGGER_IMPACT = 7.0   # the case study's suggested threshold


def load_portfolio(path: Path = PORTFOLIO_PATH) -> List[dict]:
    positions = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row["notional_musd"] = float(row["notional_musd"])
            row["duration_years"] = float(row["duration_years"])
            row["credit_spread_bp"] = float(row["credit_spread_bp"])
            positions.append(row)
    return positions


class StressTester:
    def __init__(self, engine, positions: List[dict] = None, trigger: float = TRIGGER_IMPACT):
        self.positions = positions or load_portfolio()
        self.trigger = trigger
        self.history: List[dict] = []          # past stress tests
        self.last: dict = None                 # most recent result
        self.tests_run = 0
        self._lock = threading.Lock()

        engine.subscribe(self.on_signal)

    # ------------------------------------------------------------------ #
    def on_signal(self, signal: Signal):
        if signal.impact < self.trigger:
            return
        # Only truly *risky* event types trigger the full machine.
        # (A high-impact Product Launch is an opportunity, not a stress.)
        trigger_types = {"Geopolitical", "Macroeconomic", "Credit Event",
                         "Cybersecurity", "Regulatory/Legal", "Market Volatility",
                         "Merger/Acquisition", "Supply Chain", "Operational/Quality"}
        if signal.event_type not in trigger_types:
            return
        self.run_stress_test(signal)

    # ------------------------------------------------------------------ #
    def run_stress_test(self, trigger_signal: Signal) -> dict:
        scenario = SCENARIOS.get(trigger_signal.event_type, SCENARIOS["default"])
        positions_pnl, class_pnl = [], {}

        for p in self.positions:
            n = p["notional_musd"]
            dur = p["duration_years"]
            pnl = 0.0
            ac = p["asset_class"]

            if ac in ("Government Bond", "Corporate Bond", "Mortgage Bond"):
                # duration effect of the rate shock + spread widening
                pnl -= n * dur * scenario["rate"]
                if ac != "Government Bond":
                    pnl -= n * (scenario["spread"] / 10000.0)
            elif ac in ("Corporate Loan", "CRE Loan"):
                pnl -= n * (scenario["spread"] / 10000.0)
                pnl -= n * scenario["loan_haircut"]
            elif ac == "Direct Equity":
                # equity_shock_pct is already signed (negative) -> direct P&L
                pnl += n * scenario["equity"]
            elif ac == "Derivative":
                d = p.get("direction", "")
                if "pay_fixed" in d:
                    pnl += n * dur * scenario["rate"]        # pay-fixed gains when rates rise
                elif "receive_fixed" in d:
                    pnl -= n * dur * scenario["rate"]
                elif "long" in d:
                    pnl += n * scenario["equity"]
                elif "sold_cds" in d:
                    pnl -= n * (scenario["spread"] / 10000.0)
            elif ac == "Loan Commitment":
                pnl -= n * scenario["loan_haircut"] * 0.5    # drawdown risk

            if abs(pnl) > 1e-9:
                positions_pnl.append({
                    "position_id": p["position_id"], "asset_class": ac,
                    "counterparty": p["counterparty"],
                    "notional": n, "pnl": round(pnl, 2),
                })
            class_pnl[ac] = class_pnl.get(ac, 0.0) + pnl

        before = sum(p["notional_musd"] for p in self.positions)
        after = before + sum(x["pnl"] for x in positions_pnl)

        result = {
            "ts": time.time(),
            "trigger": {
                "signal_id": trigger_signal.signal_id,
                "event_type": trigger_signal.event_type,
                "impact": trigger_signal.impact,
                "risk_flag": trigger_signal.risk_flag,
                "text": trigger_signal.text[:160],
                "source": trigger_signal.source_name,
            },
            "scenario": scenario["label"],
            "shocks": {
                "rate_shock_bp": round(scenario["rate"] * 10000),
                "spread_shock_bp": scenario["spread"],
                "equity_shock_pct": round(scenario["equity"] * 100),
                "loan_haircut_pct": round(scenario["loan_haircut"] * 100, 1),
            },
            "value_before": round(before, 1),
            "value_after": round(after, 1),
            "total_loss": round(before - after, 1),
            "loss_pct": round((before - after) / before * 100, 2),
            "pnl_by_class": {k: round(v, 1) for k, v in
                             sorted(class_pnl.items(), key=lambda kv: kv[1])},
            "top_positions": sorted(positions_pnl, key=lambda x: x["pnl"])[:8],
        }

        with self._lock:
            self.tests_run += 1
            self.last = result
            self.history.append(result)
            self.history = self.history[-40:]
        return result

    # ------------------------------------------------------------------ #
    def state(self) -> dict:
        with self._lock:
            positions = [
                {k: p[k] for k in ("position_id", "asset_class", "counterparty",
                                   "sector", "notional_musd", "rating", "duration_years")}
                for p in self.positions
            ]
            by_class: dict = {}
            for p in self.positions:
                by_class[p["asset_class"]] = by_class.get(p["asset_class"], 0) + p["notional_musd"]
            return {
                "positions": positions,
                "by_class": by_class,
                "total_value": round(sum(p["notional_musd"] for p in self.positions), 1),
                "n_positions": len(positions),
                "last_test": self.last,
                "tests_run": self.tests_run,
                "history": self.history,
                "trigger_impact": self.trigger,
            }
