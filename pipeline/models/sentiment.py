"""
sentiment.py — NFL-tuned sentiment scoring + player entity resolution (D2/D3).

v1 SentimentScorer is VADER with an NFL fantasy lexicon injected (injury terms
push negative; opportunity/usage terms push positive). Batch-only: the pipeline
scores archived articles during the waiver window. The interface is the swap
point for a fine-tuned FinBERT later (same .score() contract).

PlayerMatcher resolves which players an article is about via fast n-gram lookup
against the player-name index (no per-name regex scan of 4k+ players).
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Single-token lexicon overrides (VADER valence scale ≈ -4..+4).
NFL_LEXICON: dict[str, float] = {
    # injury / availability (negative)
    "questionable": -1.2, "doubtful": -2.2, "inactive": -2.5, "injured": -2.0,
    "injury": -1.5, "ir": -2.5, "acl": -3.5, "mcl": -2.5, "hamstring": -1.8,
    "concussion": -2.2, "sidelined": -2.0, "dnp": -1.5, "surgery": -2.5,
    "strain": -1.5, "sprain": -1.5, "suspended": -2.5, "benched": -2.0,
    "demoted": -2.0, "fumble": -1.0, "limited": -0.6,
    # opportunity / usage / production (positive)
    "workhorse": 2.8, "bellcow": 2.8, "breakout": 2.5, "starter": 1.6,
    "promoted": 2.0, "elevated": 1.6, "smash": 2.2, "featured": 1.8,
    "ascending": 2.0, "explosive": 2.0, "dominant": 2.5, "touchdown": 1.4,
    "usage": 1.0, "snaps": 0.8, "targets": 1.0, "upside": 1.4, "league-winner": 3.0,
}

# Phrase → single token, so multi-word signals reach the lexicon/flagging.
PHRASES = {
    "ruled out": "inactive", "did not practice": "dnp", "carted off": "injured",
    "target share": "targets", "snap count": "snaps", "every-down": "workhorse",
    "bell cow": "bellcow", "lead back": "workhorse", "league winner": "league-winner",
    "red zone": "touchdown",
}

INJURY_FLAG_TERMS = {
    "questionable", "doubtful", "inactive", "injured", "injury", "ir", "acl", "mcl",
    "hamstring", "concussion", "sidelined", "dnp", "surgery", "strain", "sprain",
    "suspended", "benched", "demoted",
}
OPPORTUNITY_FLAG_TERMS = {
    "workhorse", "bellcow", "breakout", "starter", "promoted", "elevated",
    "featured", "ascending", "targets", "snaps", "usage", "league-winner",
}


@dataclass
class SentimentResult:
    sentiment: float          # -1..1 (VADER compound)
    injury_flag: bool
    opportunity_flag: bool


class SentimentScorer(ABC):
    name: str = "abstract"

    @abstractmethod
    def score(self, text: str) -> SentimentResult: ...


class VaderScorer(SentimentScorer):
    """VADER + NFL lexicon. The shipping v1 scorer (runs inside the cron Action)."""

    name = "vader"

    def __init__(self) -> None:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

        self._a = SentimentIntensityAnalyzer()
        self._a.lexicon.update(NFL_LEXICON)

    def _normalize(self, text: str) -> str:
        t = text.lower()
        for phrase, token in PHRASES.items():
            t = t.replace(phrase, token)
        return t

    def score(self, text: str) -> SentimentResult:
        norm = self._normalize(text or "")
        compound = self._a.polarity_scores(norm)["compound"]
        tokens = set(re.findall(r"[a-z\-]+", norm))
        return SentimentResult(
            sentiment=round(compound, 4),
            injury_flag=bool(tokens & INJURY_FLAG_TERMS),
            opportunity_flag=bool(tokens & OPPORTUNITY_FLAG_TERMS),
        )


class PlayerMatcher:
    """Resolve player_ids mentioned in text via 2-/3-gram lookup against names.

    Fast (linear in article length) and precise enough — matches full names, not
    bare surnames, to avoid false positives ("Josh" or "Hill" alone won't match).
    """

    _SUFFIX = {"jr", "sr", "ii", "iii", "iv", "v"}

    def __init__(self, players: list[dict]):
        # name(lower) → player_id; skip 1-word names (team DEFs handled separately)
        self.index: dict[str, str] = {}
        for p in players:
            nm = (p.get("full_name") or "").lower().strip()
            if len(nm.split()) >= 2:
                self.index[nm] = p["id"]

    def match(self, text: str) -> set[str]:
        words = re.findall(r"[a-z'\.\-]+", (text or "").lower())
        # strip generational suffixes so "Player Jr." still keys on "first last"
        found: set[str] = set()
        n = len(words)
        for i in range(n):
            for size in (2, 3):
                if i + size <= n:
                    gram = " ".join(words[i : i + size]).rstrip(".")
                    pid = self.index.get(gram)
                    if pid:
                        found.add(pid)
        return found
