"""NLP provider abstraction.

The whole analysis stack sits behind one tiny interface so the engine never
has to care *which* model produced a signal:

    provider.analyze(text) -> (sentiment, event_type, impact, detail)

Our default and demo provider is LexiconProvider (VADER + rules, offline,
instant, explainable). Because the interface is clean, swapping in a
transformer (e.g. FinBERT for sentiment + zero-shot BART for event labels)
or an LLM API later is a drop-in change - we describe this in the report
as our "upgrade path".
"""
from typing import Protocol, Tuple

from . import lexicon, classifier, impact as impact_mod
from .entities import extract_companies


class NLPProvider(Protocol):
    name: str

    def analyze(self, text: str) -> Tuple[float, str, float, dict]:
        """Return (sentiment in [-1,1], event_type, impact 1-10, detail dict)."""
        ...


class LexiconProvider:
    """VADER (finance-tuned) + explainable rule engine. No internet, no GPU."""
    name = "lexicon-vader (finance-tuned)"

    def analyze(self, text: str) -> Tuple[float, str, float, dict]:
        sentiment = lexicon.score_sentiment(text)
        event_type, matched = classifier.classify_event(text)
        companies = extract_companies(text)
        impact, drivers = impact_mod.score_impact(
            event_type, sentiment, text, len(companies)
        )
        detail = {
            "sentiment_label": lexicon.label_sentiment(sentiment),
            "companies": companies,
            "matched_keywords": matched,
            "impact_drivers": drivers,
        }
        return sentiment, event_type, impact, detail


def get_provider() -> NLPProvider:
    """Pick the best available provider. For now: the offline one.

    (We kept this factory so the config can later select "finbert" or "llm"
    without touching any other file - see report, 'What we'd build next'.)
    """
    return LexiconProvider()
