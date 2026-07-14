"""Deterministic numbers → prose: the plain-language "why" line + the war-room brief.

Every string here is a pure function of the projection numbers — **no LLM, no NLG
framework, no randomness**. The same `ProjectionWhy` list always renders byte-identical
text, which is the whole contract (E6: "same input ⇒ same text, no AI call"). The pipeline
narrative generator (`pipeline/articles_generate.py::war_room_article`) does not re-template
anything: `why_report` embeds the finished `brief` prose and the pipeline only stamps it
with a slug/category, so the engine is the single source of the war-room wording.

`ponytail:` templated f-strings over a sign/magnitude ladder — the "senior dev who replaces
a paragraph-generator with a phrase table". No sentence planner, no grammar library.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from blitz_engine.explain.why import ProjectionWhy, WhyFeature, explain

if TYPE_CHECKING:
    from collections.abc import Sequence

    from blitz_engine.projection.families import ScoringWeights
    from blitz_engine.projection.inference import Projection

__all__ = ["render_why", "war_room_brief", "why_report"]


def _mag(points: float) -> str:
    """A plain-language magnitude band for a contribution (absolute points)."""
    a = abs(points)
    if a >= 4.0:
        return "huge"
    if a >= 2.0:
        return "big"
    if a >= 0.75:
        return "solid"
    return "slight"


def _clause(f: WhyFeature) -> str:
    """`elite yards per touch (+2.1)` / `a slight touchdown-rate drag (-0.4)`."""
    sign = "+" if f.contribution >= 0 else ""
    if f.contribution >= 0:
        return f"{_mag(f.contribution)} {f.label} ({sign}{f.contribution:.1f})"
    return f"a {_mag(f.contribution)} {f.label} drag ({f.contribution:.1f})"


def render_why(why: ProjectionWhy) -> str:
    """One deterministic plain-language sentence explaining a single projection.

    Leads with the headline projected points and the baseline it beats, then names the top
    two drivers by magnitude. Pure function of the numbers.
    """
    drivers = " and ".join(_clause(f) for f in why.top(2))
    delta = why.projected - why.baseline
    verb = "above" if delta >= 0 else "below"
    return (
        f"Projects {why.projected:.1f} pts "
        f"({abs(delta):.1f} {verb} a replacement touch): driven by {drivers}."
    )


def war_room_brief(
    whys: Sequence[ProjectionWhy], *, top: int = 8
) -> dict[str, str]:
    """Render a deterministic war-room brief (summary + body) over the top projections.

    Players are ranked by projected points (ties broken by `player_id`) so the output is
    stable for a fixed input. Returns `{"summary", "body"}`; the pipeline article wraps
    these verbatim. Empty input → an honest "no projections" degraded brief.
    """
    ranked = sorted(whys, key=lambda w: (-w.projected, w.player_id))[: max(top, 0)]
    if not ranked:
        return {
            "summary": "No projections available yet — the war room is dark.",
            "body": (
                "The projection engine has not published a snapshot for this slate, so "
                "there is nothing to break down. This brief refreshes automatically once "
                "projections land."
            ),
        }
    lead = ranked[0]
    summary = (
        f"{lead.player_id} tops the board at {lead.projected:.1f} pts — "
        f"{len(ranked)} projections broken down to their drivers."
    )
    lines = [f"- {w.player_id}: {render_why(w)}" for w in ranked]
    body = (
        "The war room, decomposed. Every projection below is split into the three levers "
        "that make it — usage, efficiency, and touchdown rate — measured against a "
        "replacement-level touch. No opinions, just the numbers the engine published:\n\n"
        + "\n".join(lines)
        + "\n\nRead a big positive usage number as volume you can trust; an efficiency or "
        "touchdown-rate drag is where regression is most likely to bite."
    )
    return {"summary": summary, "body": body}


def why_report(
    projection: Projection,
    *,
    weights: ScoringWeights | None = None,
    season: object = None,
    week: object = None,
    source: str = "blitz-engine projection",
    generated_at: str | None = None,
    top: int = 8,
) -> dict[str, object]:
    """Build the JSON-serialisable projection-why artifact the pipeline consumes.

    Shape: provenance + per-player driver records (`text` = `render_why`) + the finished
    `brief` (summary/body from `war_room_brief`). The pipeline's `war_room_article` lifts
    `brief` verbatim, so all war-room wording is owned here. Deterministic for a fixed
    projection.
    """
    whys = explain(projection, weights=weights)
    players = [
        {
            "player_id": w.player_id,
            "week": w.week,
            "projected": round(w.projected, 4),
            "baseline": round(w.baseline, 4),
            "contributions": {f.name: round(f.contribution, 4) for f in w.features},
            "text": render_why(w),
        }
        for w in sorted(whys, key=lambda w: (-w.projected, w.player_id))
    ]
    return {
        "generated_at": generated_at,
        "season": season,
        "week": week,
        "source": source,
        "players": players,
        "brief": war_room_brief(whys, top=top),
    }
