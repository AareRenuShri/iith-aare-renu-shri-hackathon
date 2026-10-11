"""Data ingestion - where unstructured text enters the system.

The engine only needs *something* that yields NewsItem objects, so every
source implements the same tiny interface:

    source.run(push)   -> push(NewsItem) repeatedly, from its own thread

Sources included:
  - JSONLSource        : replay a bundled .jsonl file (news or social)
  - LiveFeedSimulator  : streams the bundled files with fresh timestamps and
                         jitter, mimicking a real-time feed (great for demos)
  - NewsAPISource      : live headlines via newsapi.org (needs NEWSAPI_KEY)
  - GDELTSource        : live global news via the free GDELT DOC 2.0 API
  - RedditSource       : live social posts from r/wallstreetbets & r/stocks

Live connectors fail soft: if there is no key or no internet, the engine
logs it and carries on with the simulator - the demo never breaks.
"""
import json
import os
import random
import threading
import time
from pathlib import Path
from typing import Callable, List

import requests

from .models import NewsItem

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
PushFn = Callable[[NewsItem], None]


def load_jsonl(path: Path) -> List[dict]:
    """Load a .jsonl file that contains JSON objects.

    Handles both strict JSONL (one object per line) and "pretty" files
    where each object spans several lines - the bundled samples are
    pretty-printed so they stay human-readable and diff-friendly.
    """
    raw = Path(path).read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    items, idx, n = [], 0, len(raw)
    while idx < n:
        while idx < n and raw[idx] in " \t\r\n":
            idx += 1
        if idx >= n:
            break
        obj, end = decoder.raw_decode(raw, idx)
        items.append(obj)
        idx = end
    return items


class BaseSource:
    name = "base"

    def run(self, push: PushFn):
        raise NotImplementedError


class JSONLSource(BaseSource):
    """Replay every item in a .jsonl file once (used by tests/headless demo)."""

    def __init__(self, path: Path, name: str):
        self.path, self.name = path, name

    def run(self, push: PushFn):
        for d in load_jsonl(self.path):
            push(NewsItem.from_dict(d))


class LiveFeedSimulator(BaseSource):
    """Streams bundled items like a live feed: one item every few seconds,
    with jitter, forever. Used in demos when live APIs are not
    available - the rest of the system cannot tell the difference."""

    def __init__(self, paths: List[Path], min_gap: float = 2.0, max_gap: float = 5.0):
        self.name = "live-simulator"
        self.paths = paths
        self.min_gap, self.max_gap = min_gap, max_gap
        self._items = []
        for p in paths:
            self._items.extend(load_jsonl(p))
        # shuffle so news/social interleave like a real multi-source firehose
        random.shuffle(self._items)
        self._i = 0

    def run(self, push: PushFn):
        while True:
            item = self._items[self._i % len(self._items)]
            self._i += 1
            push(NewsItem.from_dict(item))
            time.sleep(random.uniform(self.min_gap, self.max_gap))


class NewsAPISource(BaseSource):
    """Live financial headlines from newsapi.org (free dev tier).
    Requires NEWSAPI_KEY in the environment."""

    def __init__(self, query: str = "(stocks OR earnings OR merger OR inflation)"):
        self.name = "newsapi"
        self.query = query
        self.key = os.environ.get("NEWSAPI_KEY", "")

    def run(self, push: PushFn):
        if not self.key:
            return  # fail soft - engine notes the source is inactive
        url = "https://newsapi.org/v2/everything"
        while True:
            try:
                r = requests.get(url, params={
                    "q": self.query,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 20,
                    "apiKey": self.key,
                }, timeout=10)
                for art in r.json().get("articles", []):
                    push(NewsItem.from_dict({
                        "id": art.get("url", "")[-40:],
                        "source": "news",
                        "source_name": f"NewsAPI - {(art.get('source') or {}).get('name', 'unknown')}",
                        "title": art.get("title", ""),
                        "text": art.get("description", "") or "",
                        "url": art.get("url", ""),
                        "published_at": art.get("publishedAt", ""),
                    }))
            except Exception:
                pass  # no internet / rate limit: just try again later
            time.sleep(120)  # free tier: poll every 2 minutes


class GDELTSource(BaseSource):
    """Live global news from the GDELT DOC 2.0 API (free, no key)."""

    def __init__(self, query: str = "(bankruptcy OR merger OR inflation)", max_items: int = 25):
        self.name = "gdelt"
        self.query, self.max_items = query, max_items

    def run(self, push: PushFn):
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        while True:
            try:
                r = requests.get(url, params={
                    "query": self.query,
                    "mode": "ArtList",
                    "maxrecords": self.max_items,
                    "format": "json",
                    "timespan": "1d",
                }, timeout=15)
                for art in r.json().get("articles", []):
                    push(NewsItem.from_dict({
                        "id": str(art.get("url", ""))[-40:],
                        "source": "news",
                        "source_name": f"GDELT - {art.get('domain', 'unknown')}",
                        "title": art.get("title", ""),
                        "text": "",
                        "url": art.get("url", ""),
                        "published_at": art.get("seendate", ""),
                    }))
            except Exception:
                pass
            time.sleep(300)  # GDELT updates every 15 min; be polite


class RedditSource(BaseSource):
    """Live social-media posts from investing subreddits (free public JSON)."""

    def __init__(self, subreddits=("wallstreetbets", "stocks")):
        self.name = "reddit"
        self.subreddits = subreddits

    def run(self, push: PushFn):
        headers = {"User-Agent": "RiskRadar/1.0 (hackathon demo)"}
        while True:
            for sub in self.subreddits:
                try:
                    r = requests.get(
                        f"https://www.reddit.com/r/{sub}/top.json",
                        params={"t": "day", "limit": 15},
                        headers=headers, timeout=10)
                    for post in r.json().get("data", {}).get("children", []):
                        d = post["data"]
                        push(NewsItem.from_dict({
                            "id": d.get("id", ""),
                            "source": "social",
                            "source_name": f"Reddit r/{sub} - u/{d.get('author', '?')}",
                            "title": d.get("title", ""),
                            "text": "",
                            "url": f"https://reddit.com{d.get('permalink', '')}",
                            "published_at": str(d.get("created_utc", "")),
                        }))
                except Exception:
                    pass
            time.sleep(300)


def build_default_sources(live: bool = True, fast: bool = False) -> List[BaseSource]:
    """Assemble the standard source list used by run.py.

    live=True -> include the real connectors (they fail soft without keys)
    fast=True -> tight simulator gaps for quick demos
    """
    sources: List[BaseSource] = [
        LiveFeedSimulator(
            [DATA_DIR / "news_sample.jsonl", DATA_DIR / "social_sample.jsonl"],
            min_gap=0.8 if fast else 2.0,
            max_gap=1.8 if fast else 5.0,
        )
    ]
    if live:
        sources.append(NewsAPISource())
        sources.append(GDELTSource())
        sources.append(RedditSource())
    return sources
