"""REST API + dashboard server.

Endpoints (all JSON, consumed by the dashboard):

    GET /api/health        -> engine status, provider, sources
    GET /api/signals       -> recent signals (structured risk output)
    GET /api/stats         -> aggregate stats (by event type, source, alerts)
    GET /api/companies     -> average sentiment per mentioned company
    GET /api/module_a      -> index weights, history, rebalance audit trail
    GET /api/module_b      -> portfolio, latest stress test, history
    POST /api/inject       -> analyze an arbitrary text live (great for Q&A!)
"""
import logging
from flask import Flask, jsonify, request, send_from_directory

from pathlib import Path

log = logging.getLogger("riskradar.api")
DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"


def create_app(engine, rebalancer, stress_tester) -> Flask:
    app = Flask(__name__, static_folder=None)

    # ------------------------------------------------------------------ #
    @app.route("/")
    def dashboard():
        return send_from_directory(DASHBOARD_DIR, "index.html")

    @app.route("/<path:fname>")
    def static_files(fname):
        return send_from_directory(DASHBOARD_DIR, fname)

    # ------------------------------------------------------------------ #
    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "provider": engine.provider.name,
            "processed": engine.processed,
            "sources": engine.source_status,
            "modules": {"A_index_rebalancing": True, "B_stress_testing": True},
        })

    @app.route("/api/signals")
    def signals():
        limit = int(request.args.get("limit", 40))
        return jsonify([s.to_dict() for s in engine.recent(limit)])

    @app.route("/api/stats")
    def stats():
        return jsonify(engine.stats())

    @app.route("/api/companies")
    def companies():
        return jsonify(engine.company_sentiment())

    @app.route("/api/module_a")
    def module_a():
        return jsonify(rebalancer.state())

    @app.route("/api/module_b")
    def module_b():
        return jsonify(stress_tester.state())

    @app.route("/api/inject", methods=["POST"])
    def inject():
        """Analyze any text on the fly - we use this live in the demo:
        type a headline, watch it flow through engine -> modules."""
        payload = request.get_json(silent=True) or {}
        text = (payload.get("text") or "").strip()
        if not text:
            return jsonify({"error": "provide {\"text\": \"...\"}"}), 400
        from engine.models import NewsItem
        item = NewsItem(id="manual", source="news", source_name="manual inject", text=text)
        sig = engine.process(item)
        return jsonify({
            "signal": sig.to_dict(),
            "module_a_rebalanced": bool(sig.companies),
            "module_b_triggered": sig.impact >= 7.0,
        })

    return app
