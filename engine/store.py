"""Persistence - every signal is written to SQLite *and* appended to a
JSONL file. This satisfies the "make signals available via API or file"
requirement in the most literal way: we do both.

SQLite powers history/stats queries; the JSONL file is the simple,
grep-able, human-friendly view of the same stream.
"""
import json
import sqlite3
import threading
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "riskradar.db"
JSONL_PATH = DATA_DIR / "signals.jsonl"


class SignalStore:
    def __init__(self, db_path: Path = DB_PATH, jsonl_path: Path = JSONL_PATH):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path, self.jsonl_path = db_path, jsonl_path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                ts REAL, ts_iso TEXT, source TEXT, source_name TEXT,
                text TEXT, url TEXT,
                sentiment REAL, event_type TEXT, impact REAL,
                risk_flag TEXT, companies TEXT
            )
        """)
        self._conn.commit()

    def save(self, signal):
        d = signal.to_dict()
        row = (
            d["signal_id"], d["ts"], d["ts_iso"], d["source"], d["source_name"],
            d["text"], d["url"], d["sentiment"], d["event_type"], d["impact"],
            d["risk_flag"], json.dumps(d["companies"]),
        )
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", row)
            self._conn.commit()
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(d) + "\n")

    def count(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM signals").fetchone()[0]

    def close(self):
        self._conn.close()
