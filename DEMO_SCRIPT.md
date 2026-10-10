# 5-Minute Live Demo Script

> Setup before the demo: `pip install -r requirements.txt`, then
> `python run.py --fast`. The dashboard opens automatically.
> Keep a terminal open next to the browser — it makes the "it's really
> processing" point for you.

---

## 0:00 — The pitch (15s)

> "Markets move on news — but news is text, and risk systems only eat
> numbers. RiskRadar is the bridge: it reads news and social media in
> real time and converts them into three numbers a machine can act on —
> sentiment, event type, and impact. Then I built two things that *act*
> on those numbers."

## 0:15 — Risk Engine tab (1 min 15s)

- Point at the **live feed table**: "Every row is a tweet or headline that
  just got processed. Watch — new ones appear every few seconds."
- Pick one row, read it aloud, then read its scores:
  > "This one: sentiment **-0.97**, event **Credit Event**, impact **10** —
  it's the bankruptcy story. And look, the engine even tells you *why*: the
  matched keywords and impact drivers are stored on every signal."
- **The money shot — "Try it live" box.** Type a headline nobody in this room
  has seen, e.g.:
  `BREAKING: Nvidia faces massive antitrust probe as regulators investigate chip supply shortages`
  hit Analyze → read the verdict: sentiment -0.79, Regulatory/Legal, impact 8,
  high-risk flag, **and note the two chips at the bottom**: Module A just
  rebalanced NVDA and Module B just triggered a stress test. One text in,
  two systems moved.
- Mention sources: "two feed types minimum were required — there are news and
  social bundled, plus live NewsAPI, GDELT and Reddit connectors when keys
  and internet are available. Fail-soft by design: the demo never depends on a
  network."

## 1:30 — Module A tab (1 min 15s)

- "Module A is the tactical user of sentiment. Twenty S&P 100 stocks start
  equal-weighted at 5%."
- Show **current weights**: "After the feed ran, sentiment moved Walmart and
  McDonald's up to ~7%, pushed Boeing and Bank of America down to ~2.6%.
  The formula is right there on the card: new weight = old × (1 + 0.25 ×
  sentiment), clamped between 2% and 12% so nothing dominates, then
  renormalized to 100%."
- Show **weights over time**: "This is the whole point — the index *drifts*
  with sentiment in real time."
- Show the **audit trail**: "Every weight change is logged with the signal
  that caused it — you can reconstruct any decision."

## 2:45 — Module B tab (1 min 15s)

- "Module B is the strategic user. Same signals, opposite timescale — it
  doesn't care about daily sentiment, it waits for high-impact events."
- Show portfolio card: "Synthetic wholesale banking portfolio — $5.36bn,
  38 positions, nine asset classes: corporate loans, CRE, government bonds,
  corporates, MBS, derivatives, commitments, equity."
- "Whenever a signal lands with impact ≥ 7, I run a stress scenario keyed
  to the event type. Rates shock for Macroeconomic, credit shock for a
  default, and so on."
- Show **before/after chart** + P&L by class: "The last trigger was a credit
  event — the portfolio dropped from $5.36bn to $5.00bn, about 6.6%. You can
  see exactly where it hurt: corporate loans and bonds."
- "Worst-hit positions table — this is what a risk officer would actually
  look at first."

## 4:00 — Wrap (1 min)

- "To recap: one engine, three explainable numbers, and two very different
  consumers — a tactical rebalancer and a strategic stress tester — all
  running live, offline, on a laptop."
- If asked "what's real vs mocked": sources are simulated feeds of realistic
  items (live connectors included, they activate with keys), the index is a
  mock by requirement, the portfolio is synthetic by requirement — the
  *engine, API, both modules and dashboard are fully real*.
- Know your numbers (see cheat sheet in `Project_Report.pdf`): 93% of items
  classified, ~10ms per signal, k=0.25, 2-12% band, trigger at 7, biggest
  stress loss 8.1% ($435m).
