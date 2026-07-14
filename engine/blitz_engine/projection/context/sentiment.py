"""Sentiment context → a Bayesian PRIOR NUDGE + VARIANCE WIDENER on the talent prior.

This is the *context seam over E1-core*: it does not touch the generative model, it
implements the core's `TalentPriorHook` (priors.py) so a narrative signal shifts a
player's talent-prior **mean** (a hot-usage story nudges opportunity up; an injury story
nudges it down) and widens its **scale** (conflicting reports / an availability flag = more
epistemic room). Every unknown player degrades to neutral (loc 0, default scale) — a
missing sentiment feed can never hurt the base fit.

Signal source (UPGRADE-with-fallback, brief §build):
  * the shipping NFL-tuned VADER scorer (`pipeline/models/sentiment.py`) is the FALLBACK;
  * `resolve_scorer()` first tries a local NFL-tuned HF transformer (`TransformerScorer`)
    and DEGRADES to VADER when `transformers`/the model is unavailable — so the unit works
    keyless and dependency-light, and only *improves* when the transformer is present.

Bounds (safety, mirrors the factor seam's clamp): the mean nudge is confidence-shrunk and
hard-clipped to `max_nudge`; the variance widener is clipped to `[1, max_widen]`. A single
noisy article can nudge the mean only a little, but a genuine injury/availability flag still
widens the outcome variance regardless of volume.
"""
from __future__ import annotations

import importlib.util
import statistics
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

import numpy as np

from blitz_engine.projection.priors import TalentPrior

if TYPE_CHECKING:
    from blitz_engine.projection.priors import TalentPriorHook

__all__ = [
    "Scored",
    "SentimentPrior",
    "SentimentSignal",
    "Scorer",
    "TransformerScorer",
    "aggregate_signals",
    "resolve_scorer",
    "score_and_aggregate",
]


# ── scorer surface (VADER fallback ← → transformer upgrade) ────────────────────
@dataclass(frozen=True)
class Scored:
    """One text's sentiment read — the minimal shape `aggregate_signals` consumes.

    Matches the pipeline `SentimentResult` structurally (sentiment in [-1, 1] + the two
    NFL flags) so the VADER fallback and the transformer upgrade are interchangeable.
    """

    sentiment: float
    injury_flag: bool = False
    opportunity_flag: bool = False


@runtime_checkable
class Scorer(Protocol):
    """Anything with an NFL-tuned `.score(text)` returning sentiment + the two flags."""

    name: str

    def score(self, text: str) -> Scored: ...


def _load_pipeline_sentiment():  # noqa: ANN202
    """Import `pipeline/models/sentiment.py` by PATH (no pipeline package init).

    `ponytail:` a direct file-load sidesteps `pipeline/models/__init__` (which pulls the
    whole modeling package) — the scorer module is stdlib-only until VADER is constructed.
    """
    from blitz_engine.pipeline_bridge import pipeline_root

    path = pipeline_root() / "models" / "sentiment.py"
    spec = importlib.util.spec_from_file_location("_blitz_pipeline_sentiment", path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot load pipeline sentiment from {path}")
    mod = sys.modules.get(spec.name)
    if mod is None:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
    return mod


class TransformerScorer:
    """OPTIONAL upgrade: a local NFL-tuned HF transformer for the compound sentiment.

    Constructing it REQUIRES `transformers` and the model to load; either absent raises so
    `resolve_scorer` falls back to VADER. The two NFL flags reuse the pipeline lexicon term
    sets (the flags are lexical, not learned), so the upgrade only replaces the *polarity*.
    """

    name = "transformer"

    def __init__(self, model: str | None = None) -> None:
        import os

        from transformers import pipeline as hf_pipeline  # raises if unavailable

        model_name = model or os.getenv(
            "BLITZ_SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english"
        )
        self._pipe = hf_pipeline("sentiment-analysis", model=model_name)
        sent = _load_pipeline_sentiment()
        self._injury = frozenset(sent.INJURY_FLAG_TERMS)
        self._opp = frozenset(sent.OPPORTUNITY_FLAG_TERMS)
        self._phrases = dict(sent.PHRASES)

    def _flags(self, text: str) -> tuple[bool, bool]:
        import re

        t = (text or "").lower()
        for phrase, token in self._phrases.items():
            t = t.replace(phrase, token)
        tokens = set(re.findall(r"[a-z\-]+", t))
        return bool(tokens & self._injury), bool(tokens & self._opp)

    def score(self, text: str) -> Scored:
        out = self._pipe((text or "")[:512])[0]
        signed = float(out["score"]) * (1.0 if out["label"].upper().startswith("POS") else -1.0)
        injury, opp = self._flags(text)
        return Scored(sentiment=round(signed, 4), injury_flag=injury, opportunity_flag=opp)


def resolve_scorer(*, prefer_transformer: bool = True) -> Scorer:
    """Best available scorer: transformer upgrade if importable, else the VADER fallback."""
    if prefer_transformer:
        try:
            return TransformerScorer()
        except Exception:  # noqa: BLE001 - any load failure ⇒ degrade to VADER
            pass
    return _load_pipeline_sentiment().VaderScorer()


# ── per-player aggregation ─────────────────────────────────────────────────────
@dataclass(frozen=True)
class SentimentSignal:
    """A player's aggregated narrative: mean polarity, volume, flags, disagreement.

    `n` (article count) drives the confidence-shrink on the mean nudge; `disagreement`
    (stdev of the article polarities) and `injury_flag` drive the variance widener.
    """

    sentiment: float = 0.0
    n: int = 0
    injury_flag: bool = False
    opportunity_flag: bool = False
    disagreement: float = 0.0


def aggregate_signals(articles: Iterable[Mapping[str, object]]) -> dict[str, SentimentSignal]:
    """Scored article rows → per-player `SentimentSignal` (mirrors news_sentiment aggregation).

    Each row needs `player_ids` (iterable) + `sentiment` (+ optional `injury_flag` /
    `opportunity_flag`). Players not mentioned simply never appear ⇒ neutral downstream.
    """
    polarities: dict[str, list[float]] = {}
    injury: dict[str, bool] = {}
    opp: dict[str, bool] = {}
    for a in articles:
        s = float(a.get("sentiment") or 0.0)  # type: ignore[arg-type]
        pids = a.get("player_ids")
        if not isinstance(pids, (list, tuple, set)):
            continue
        for pid in pids:
            polarities.setdefault(pid, []).append(s)
            injury[pid] = injury.get(pid, False) or bool(a.get("injury_flag"))
            opp[pid] = opp.get(pid, False) or bool(a.get("opportunity_flag"))
    out: dict[str, SentimentSignal] = {}
    for pid, xs in polarities.items():
        out[pid] = SentimentSignal(
            sentiment=float(statistics.fmean(xs)),
            n=len(xs),
            injury_flag=injury[pid],
            opportunity_flag=opp[pid],
            disagreement=float(statistics.pstdev(xs)) if len(xs) > 1 else 0.0,
        )
    return out


def score_and_aggregate(
    items: Iterable[tuple[str, Iterable[str]]], scorer: Scorer | None = None
) -> dict[str, SentimentSignal]:
    """`(text, player_ids)` pairs → signals, scoring with `scorer` (default: best available).

    Exercises the scorer end-to-end (transformer→VADER fallback) so callers need not wire
    the scorer themselves; equivalent to `aggregate_signals` over freshly-scored rows.
    """
    sc = scorer or resolve_scorer()
    rows = []
    for text, pids in items:
        r = sc.score(text)
        rows.append({
            "player_ids": list(pids),
            "sentiment": r.sentiment,
            "injury_flag": r.injury_flag,
            "opportunity_flag": r.opportunity_flag,
        })
    return aggregate_signals(rows)


# ── the talent-prior hook (context seam over E1-core) ──────────────────────────
class SentimentPrior:
    """`TalentPriorHook`: sentiment → bounded prior-mean nudge + variance widener.

    Composes over an optional `base` hook (e.g. E1-talent's) — the nudge/widener stack on
    top of the base loc/scale so sentiment and a talent model coexist. Neutral for any
    player without a signal.

    Tunables (all bounded):
      * `nudge_gain` × sentiment × confidence, clipped to ±`max_nudge` → the mean shift.
        confidence = n / (n + `confidence_at`) shrinks a thin (few-article) signal.
      * widener = 1 + `widen_gain` × (disagreement + `injury_penalty`·injury_flag),
        clipped to [1, `max_widen`] → scale multiplier (variance, not mean).
    """

    def __init__(
        self,
        signals: Mapping[str, SentimentSignal],
        *,
        base: TalentPriorHook | None = None,
        nudge_gain: float = 0.4,
        max_nudge: float = 0.5,
        widen_gain: float = 0.5,
        max_widen: float = 2.0,
        injury_penalty: float = 0.75,
        confidence_at: int = 3,
    ) -> None:
        self.signals = signals
        self.base = base
        self.nudge_gain = nudge_gain
        self.max_nudge = max_nudge
        self.widen_gain = widen_gain
        self.max_widen = max_widen
        self.injury_penalty = injury_penalty
        self.confidence_at = confidence_at

    def __call__(self, player_ids: list[str], stage: str, default_scale: float) -> TalentPrior:
        n = len(player_ids)
        if self.base is not None:
            bt = self.base(player_ids, stage, default_scale)
            loc = np.asarray(bt.loc, dtype=float).copy()
            scale = np.asarray(bt.scale, dtype=float).copy()
        else:
            loc = np.zeros(n)
            scale = np.full(n, default_scale)

        for i, pid in enumerate(player_ids):
            sig = self.signals.get(pid)
            if sig is None:
                continue
            conf = sig.n / (sig.n + self.confidence_at)
            raw_nudge = self.nudge_gain * sig.sentiment * conf
            loc[i] += float(np.clip(raw_nudge, -self.max_nudge, self.max_nudge))
            uncertainty = sig.disagreement + (self.injury_penalty if sig.injury_flag else 0.0)
            widen = float(np.clip(1.0 + self.widen_gain * uncertainty, 1.0, self.max_widen))
            scale[i] *= widen

        return TalentPrior(loc=loc, scale=scale)  # type: ignore[arg-type]
