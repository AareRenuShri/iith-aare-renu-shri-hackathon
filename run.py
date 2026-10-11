"""RiskRadar - one-command launcher.

    python run.py            -> simulator + live connectors (if keys/net), dashboard
                               at http://localhost:8000
    python run.py --offline  -> bundled feeds only (demo-safe, zero network)
    python run.py --fast     -> faster feed for a quick walkthrough
    python run.py --port 8001-> different port

What starts up:
  1. the Risk Engine (ingestion -> NLP -> structured signals)
  2. Module A (index rebalancer) and Module B (stress tester) - both subscribed
  3. the REST API + live dashboard
"""
import argparse
import logging
import threading
import webbrowser

from src.engine import RiskEngine
from src.engine.ingest import build_default_sources
from src.engine.store import SignalStore
from src.modules import IndexRebalancer, StressTester
from src.api.server import create_app

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("riskradar")


def main():
    ap = argparse.ArgumentParser(description="RiskRadar launcher")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--offline", action="store_true",
                    help="skip live connectors, use bundled feeds only")
    ap.add_argument("--fast", action="store_true", help="faster simulated feed")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    # --- wire the system together -----------------------------------------
    engine = RiskEngine(store=SignalStore())
    module_a = IndexRebalancer(engine)          # subscribes to sentiment
    module_b = StressTester(engine)             # subscribes to event + impact
    sources = build_default_sources(live=not args.offline, fast=args.fast)

    engine.start_sources(sources)
    log.info("engine online · provider=%s · %d sources started",
             engine.provider.name, len(sources))

    app = create_app(engine, module_a, module_b)
    url = f"http://localhost:{args.port}"
    log.info("dashboard live at %s  (Ctrl+C to stop)", url)
    if not args.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()

    app.run(host="0.0.0.0", port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
