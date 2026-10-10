# RiskRadar 📡

**An AI/NLP Risk Engine that turns real-time news & social media into
structured financial risk signals — then acts on them.**

Phase III Case Study · Ingest unstructured text from 2+ sources → output
`sentiment (-1..1)`, `event classification`, `impact score (1-10)` → feed two
downstream modules:

| | Module | What it does |
|---|--------|--------------|
| **A** | Tactical Index Rebalancing | sentiment tilts the weights of a 20-stock mock index (S&P 100 subset), live |
| **B** | Strategic Portfolio Stress Testing | high-impact events (impact ≥ 7) trigger shock scenarios on a $5.36bn synthetic wholesale-banking portfolio |

One process runs everything: ingestion → NLP → signals → both modules →
REST API → live dashboard.

---

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python run.py                      # dashboard → http://localhost:8000
```

That's it. The engine boots with a **live-feed simulator** streaming bundled
news + social items, so everything works offline — no API keys, no internet,
no GPU.

### Live data (optional)

```bash
export NEWSAPI_KEY=...      # free key from newsapi.org
python run.py               # adds live NewsAPI + GDELT + Reddit sources
```

Live connectors **fail soft**: no key or no network → engine logs it and
carries on with the simulator. The demo can never break.

### Other entry points

```bash
python run.py --offline    # bundled feeds only (safest demo mode)
python run.py --fast       # faster feed for a quick walkthrough
python demo.py             # headless end-to-end run + writes figures to demo_outputs/
```

---

## The dashboard (what you show in the demo)

`http://localhost:8000` — three tabs, all live:

1. **Risk Engine** — live signal table (text → sentiment, event, impact,
   companies), event-type distribution, sentiment by source, and an
   **"analyze any headline"** box: type text, watch it flow through the whole
   system in real time.
2. **Module A** — current index weights, weights drifting over time,
   and a full rebalance audit trail (old weight → new weight + the sentiment
   that caused it).
3. **Module B** — portfolio composition, before/after stress-test valuation,
   P&L by asset class, worst-hit positions, and what event triggered it.

## Architecture

```
 sources                     Risk Engine                     consumers
┌────────────┐      ┌───────────────────────────┐      ┌────────────────────┐
│ news  feed │─────▶│  clean → company match    │─────▶│ Module A: rebalance │
│ social feed│─────▶│  sentiment (VADER+)      │─────▶│ Module B: stress    │
│ NewsAPI    │      │  event classification    │─────▶│ REST API  /api/...   │
│ GDELT      │      │  impact score (1-10)      │      │ SQLite + signals.jsonl│
│ Reddit     │      │  → Signal (explainable)   │      │ Dashboard (browser)  │
└────────────┘      └───────────────────────────┘      └────────────────────┘
```

- `engine/` — models, finance-tuned lexicon, classifier, impact scorer,
  provider interface, ingestion connectors, pub-sub pipeline, persistence
- `modules/` — the two downstream modules (subscribers)
- `api/` — Flask REST API (also serves the dashboard)
- `dashboard/` — single-page HTML + bundled Plotly (fully offline)
- `data/` — bundled news/social samples, synthetic portfolio, output files

**Why VADER + rules instead of a neural model?** It runs anywhere instantly
and every score is **explainable** — each signal stores the keywords that
fired and the drivers behind its impact score. The provider interface makes
swapping in FinBERT/LLM a drop-in change later (see the report's "future
work").

## How the scores work

**Sentiment** — VADER compound score, extended with a hand-curated finance
lexicon (`bankruptcy -3.5`, `downgrade -2.6`, `record +2.4` …). VADER was
built for social media, so tweets (emoji, caps, slang) work out of the box.

**Event classification** — priority-ordered keyword rules over 12 categories
(Geopolitical, Macroeconomic, Credit Event, M&A, Regulatory/Legal, …).
Priority resolves conflicts: *a story about a bankruptcy lawsuit is a Credit
Event, not a Legal story.* Matched keywords are stored on every signal.

**Impact (1-10)** — transparent formula, recorded on each signal:
`base(category) ± urgency ± magnitude ± sentiment ± scope`, clamped to 1-10.
e.g. `8.0 = base 5 (Regulatory) + 1 breaking + 1 massive + 1 strongly negative`.

**Module A rule** — `w_new = w_old × (1 + 0.25 × sentiment)`, weights clamped
to 2-12%, renormalized to 100%. Positive sentiment ⇒ weight up, negative ⇒ down.

**Module B scenarios** — event-type shocks, e.g. Macroeconomic ⇒ rates +200bp
& equity -10%: bonds lose `notional × duration × Δrate`, loans take haircuts,
pay-fixed swaps gain. Triggered when `impact ≥ 7` (the case study's threshold).

## Outputs

- `GET /api/signals` — the structured signals (JSON)
- `data/signals.jsonl` — same stream, one JSON object per line (grep-able)
- `data/riskradar.db` — SQLite history for queries
- `demo_outputs/` — figures + full signal dump from the headless run

## Notes

Built for a Phase 3 case study round. Demo walkthrough: `DEMO_SCRIPT.md`.
Full design rationale, results and limitations: `docs/Project_Report_and_QA.pdf`.
7-slide submission deck: `docs/Presentation_Deck.pdf`.
