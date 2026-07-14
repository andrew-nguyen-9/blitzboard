"""`blitz_engine.explain` — projection explainability (E6).

Turns E1-core's read-apart generative layers into a per-projection **"why"** and a
deterministic **war-room brief** — numbers to plain language with no AI in the loop.

    explain / why_frame        exact-Shapley driver attribution per player-week
    render_why / war_room_brief templated prose (same input ⇒ same text)
    why_report                 the JSON artifact `pipeline/articles_generate.py` consumes

Attributions are exact Shapley values over three drivers (volume / efficiency / TD rate);
prose is a pure phrase-table render. See each module for the `ponytail:` rationale.
"""
from __future__ import annotations

from blitz_engine.explain.narrative import render_why, war_room_brief, why_report
from blitz_engine.explain.why import (
    FEATURES,
    ProjectionWhy,
    WhyFeature,
    explain,
    shapley_contributions,
    why_frame,
)

__all__ = [
    "FEATURES",
    "ProjectionWhy",
    "WhyFeature",
    "explain",
    "render_why",
    "shapley_contributions",
    "war_room_brief",
    "why_frame",
    "why_report",
]
