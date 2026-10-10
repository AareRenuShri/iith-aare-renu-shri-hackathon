"""Headless end-to-end run - no browser needed.

Processes every bundled news + social item through the full stack
(engine -> Module A -> Module B), then prints a compact report and writes
matplotlib charts to demo_outputs/. Used for:
  * verifying the pipeline works (smoke test)
  * generating the figures used in the report/presentation
  * a no-browser fallback if a demo machine misbehaves

    python demo.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from engine import RiskEngine, NewsItem
from engine.ingest import JSONLSource, load_jsonl, DATA_DIR
from modules import IndexRebalancer, StressTester

OUT = Path(__file__).resolve().parent / "demo_outputs"
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "#111a2c", "axes.facecolor": "#111a2c",
    "axes.edgecolor": "#33435f", "axes.labelcolor": "#dbe4f3",
    "text.color": "#dbe4f3", "xtick.color": "#8496b3", "ytick.color": "#8496b3",
    "font.size": 10, "font.family": "sans-serif",
})


def load_items():
    items = []
    for p in [DATA_DIR / "news_sample.jsonl", DATA_DIR / "social_sample.jsonl"]:
        for d in load_jsonl(p):
            items.append(NewsItem.from_dict(d))
    # process in chronological order like a real feed
    items.sort(key=lambda x: x.published_at, reverse=True)
    return items


def main():
    engine = RiskEngine(store=None)             # no persistence for the demo run
    rebalancer = IndexRebalancer(engine)
    stress = StressTester(engine)

    items = load_items()
    print(f"processing {len(items)} items (28 news + 30 social)…\n")

    signals = [engine.process(it) for it in items]

    # ---------------- summary table --------------------------------------
    print(f"{'source':7s} {'sent':>6s}  {'event':<18s} {'imp':>4s}  companies")
    for s in signals[:12]:
        cos = ",".join(c.ticker for c in s.companies) or "-"
        print(f"{s.source:7s} {s.sentiment:+6.2f}  {s.event_type:<18s} {s.impact:>4g}  {cos}")
    print(f"… and {len(signals)-12} more\n")

    stats = engine.stats()
    print("engine stats:", json.dumps(stats, indent=2)[:600], "\n")

    print(f"Module A: {rebalancer.signals_seen} rebalancing signals, "
          f"{len(rebalancer.rebalance_log)} weight changes")
    top = sorted(rebalancer.weights.items(), key=lambda kv: -kv[1])[:3]
    print("  top weights:", ", ".join(f"{t} {w*100:.1f}%" for t, w in top))
    bottom = sorted(rebalancer.weights.items(), key=lambda kv: kv[1])[:3]
    print("  bottom weights:", ", ".join(f"{t} {w*100:.1f}%" for t, w in bottom), "\n")

    print(f"Module B: {stress.tests_run} stress tests triggered "
          f"(threshold: impact >= {stress.trigger})")
    for t in stress.history:
        print(f"  - {t['scenario']}: loss ${t['total_loss']:,}m "
              f"({t['loss_pct']}%) | trigger: {t['trigger']['event_type']} "
              f"impact {t['trigger']['impact']}")

    # ---------------- figures for the report ------------------------------
    # 1. event distribution
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ev = sorted(stats["by_event"].items(), key=lambda kv: -kv[1])
    ax.barh([e[0] for e in ev][::-1], [e[1] for e in ev][::-1], color="#4da3ff")
    ax.set_title("Signals by event classification")
    fig.tight_layout(); fig.savefig(OUT / "fig_events.png", dpi=160); plt.close(fig)

    # 2. module A weight history
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    hist = rebalancer.history
    movers = sorted(rebalancer.weights.items(), key=lambda kv: -kv[1])[:5] + \
             sorted(rebalancer.weights.items(), key=lambda kv: kv[1])[:3]
    for tk, _ in movers:
        ax.plot([h["weights"][tk] * 100 for h in hist], label=tk, lw=1.8)
    ax.axhline(5, color="#8496b3", lw=0.8, ls="--")
    ax.set_ylabel("weight %"); ax.set_xlabel("rebalancing events →")
    ax.set_title("Module A — index weights drift from equal weight")
    ax.legend(ncol=4, fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(OUT / "fig_module_a.png", dpi=160); plt.close(fig)

    # 3. module B stress test result
    if stress.last:
        t = stress.last
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.6, 3.2))
        ax1.bar(["Before", "After"], [t["value_before"]/1000, t["value_after"]/1000],
                color=["#4da3ff", "#ff5d73"], width=0.55)
        ax1.set_ylabel("$bn"); ax1.set_title(f"Stress test — {t['scenario']}")
        for i, v in enumerate([t["value_before"]/1000, t["value_after"]/1000]):
            ax1.text(i, v + 0.02, f"{v:.2f}bn", ha="center", fontsize=9)
        pc = sorted(t["pnl_by_class"].items(), key=lambda kv: kv[1])
        colors = ["#ff5d73" if v < 0 else "#2ecc8f" for _, v in pc]
        ax2.barh([k for k, _ in pc], [v for _, v in pc], color=colors)
        ax2.set_title("P&L by asset class ($m)")
        fig.tight_layout(); fig.savefig(OUT / "fig_module_b.png", dpi=160); plt.close(fig)

    # 4. sentiment scatter by event type
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    for et in {s.event_type for s in signals}:
        xs = [s.impact for s in signals if s.event_type == et]
        ys = [s.sentiment for s in signals if s.event_type == et]
        ax.scatter(xs, ys, s=26, alpha=0.85, label=et)
    ax.set_xlabel("impact score (1-10)"); ax.set_ylabel("sentiment (-1..1)")
    ax.axhline(0, color="#8496b3", lw=0.8)
    ax.set_title("Every signal: sentiment vs impact")
    ax.legend(fontsize=7, frameon=False, ncol=3)
    fig.tight_layout(); fig.savefig(OUT / "fig_scatter.png", dpi=160); plt.close(fig)

    # raw outputs for the report
    with open(OUT / "signals.json", "w") as f:
        json.dump([s.to_dict() for s in signals], f, indent=1)
    print(f"\nfigures + signals written to {OUT}/")


if __name__ == "__main__":
    main()
