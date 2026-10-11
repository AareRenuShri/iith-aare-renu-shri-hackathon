# Demo Video (≤10 min) & Live Jury Pitch Script

> Guidelines allow **up to 10 minutes**, suggested flow below lands at ~6 —
> tight is better than long. Record the screen + mic (QuickTime: File → New
> Screen Recording, or OBS). **Upload to YouTube as UNLISTED** (not Drive —
> the guidelines explicitly require YouTube unlisted; verify it plays in an
> incognito window before submitting).
>
> Setup before recording: `pip install -r requirements.txt`, then
> `python run.py --fast`. Keep a terminal visible next to the browser.

---

## PART A — the recorded video (~6 min, follow the guidelines' flow)

### 0:00–0:30 · Intro (30s)

> "Markets move on news — but news is text, and risk systems only eat
> numbers. RiskRadar is the bridge: it reads news and social media in real
> time and converts them into three numbers a machine can act on —
> sentiment, event type, and impact. And then two modules act on those
> numbers: an index rebalancer and a portfolio stress tester. This is
> running live, entirely offline, on one laptop."

### 0:30–1:00 · Setup / Run (30s) — show the README commands working

Type/say:
> "Everything runs in one command. Clone the repo, install four light
> dependencies, `python run.py` — and the engine, both modules, the API
> and this dashboard all boot together. No GPU, no API keys, no internet
> needed — by design, so this demo cannot break."
(Show the terminal: `python run.py` → log lines → browser opens.)

### 1:00–4:00 · End-to-end walkthrough (3 min)

**Engine tab (1 min 15s):** live signal table ("new rows every few
seconds — each one a tweet or headline that just got processed"). Read one
row + its scores: *"bankruptcy story: sentiment −0.97, Credit Event,
impact 10, high-risk flag — and the engine tells you why: matched keywords
and impact drivers are stored on every signal."*

**The inject box (45s) — the money shot:** type a fresh headline no one has
seen, e.g. `BREAKING: Massive layoffs at Tesla as regulators probe demand
collapse`, hit Analyze → read the verdict aloud, then point at the two
chips: "Module A just rebalanced TSLA, and Module B just triggered a stress
test. One text in, two systems moved."

**Module A tab (45s):** "20 stocks started equal-weighted at 5%. After the
feed ran, Walmart and McDonald's floated up to ~7%, Boeing and Bank of
America sank to ~2.6%. Formula is on the card — new weight = old × (1 +
0.25 × sentiment), clamped 2–12%, renormalized. Every weight change is in
the audit trail with the signal that caused it."

**Module B tab (15s):** "Same signals, opposite timescale — this one waits
for high-impact events. $5.36bn portfolio, 38 positions, nine asset
classes."

### 4:00–5:00 · Results & impact (60s)

- Module B charts: "the last trigger was a credit event — portfolio drops
  from $5.36bn to $5.00bn, about 6.6%. You can see exactly where it hurt:
  corporate loans and high-yield bonds. Worst-hit positions table — what a
  risk officer looks at first."
- Numbers card: "58 items, 93% meaningfully classified, 0.3 milliseconds
  per signal — about 3,300 signals a second on one laptop core, with every
  number explaining itself. That's the auditability a real risk desk
  actually needs."

### 5:00–5:30 · Close (30s)

> "One engine, three explainable numbers, two consumers — tactical
> rebalancing and strategic stress testing — running live, offline, on a
> laptop. The code, deck and detailed report are all in the repo. Thank
> you."

---

## PART B — live jury pitch (5 min, if shortlisted)

Same beats, compressed: **pitch (15s) → inject box live (90s, judges
choose the headline) → Module A (60s) → Module B (60s) → wrap (30s)**.
Leave the remaining ~60s for Q&A. Before the pitch: `python run.py`
running and ready, README open.

---

## Recording checklist

- [ ] Resolution ≥1080p, browser zoomed so the dashboard fills most of the frame
- [ ] Terminal visible when running setup commands
- [ ] Record one take with the script beside you; pause-editing is fine
- [ ] Upload → YouTube **Unlisted** → test in incognito window
- [ ] Paste link into README (`Demo Video Link`) + the submission form
