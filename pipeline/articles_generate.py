"""Article generator (Epic 9b).

Turns E3's environmental / team-scheme context artifact
(``pipeline/artifacts/context_report.json``) into a small, stable set of
human-readable "modeling findings" articles and upserts them into
``public.articles``. E9a search then indexes those rows (``id,title,slug,summary``
→ ``/articles/<slug>``) with no code change on its side.

Design (mirrors E3): pure, network-free builders (unit-testable) + a thin main.
Idempotent — every article carries a deterministic ``slug`` derived from its
category + season/week, so re-running upserts in place (on_conflict=slug) and the
row *set* is fixed regardless of how sparse the context is. When a signal has no
ingested data (neutral/degraded artifact), its article degrades to an honest
"context not yet ingested" body rather than vanishing, keeping the PK set stable.

Sources are all E3's: weather (Open-Meteo, keyless), team_pace / pass_rate
(team-scheme factors), venue (static stadium table). See docs/modeling/FACTOR_CATALOG.md.
"""
from __future__ import annotations

import json
from pathlib import Path

from common import console, upsert

_ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "context_report.json"
# E6: the projection-why artifact the engine's `blitz_engine.explain.why_report` writes.
# Its `brief` (summary/body) is already-rendered, deterministic prose — this generator only
# stamps it with a slug/category, so the war-room wording lives entirely in the engine.
_PROJECTION_ARTIFACT = Path(__file__).resolve().parent / "artifacts" / "projection_why.json"

# Wind (mph) at/above which passing/kicking gets a real haircut in the weather
# factors — the threshold that makes a game "notable" for the weather article.
_WIND_NOTABLE = 15.0


# ── pure helpers ────────────────────────────────────────────────────────────
def _teams(report: dict) -> list[tuple[str, dict]]:
    """(code, metadata) pairs, sorted by code for deterministic output."""
    teams = (report or {}).get("teams") or {}
    return sorted(
        ((code, (t or {}).get("metadata") or {}) for code, t in teams.items()),
        key=lambda kv: kv[0],
    )


def _period(report: dict) -> str:
    """Human label for the report's season/week, e.g. '2025 · Week 5' or '2025'."""
    season = (report or {}).get("season")
    week = (report or {}).get("week")
    return f"{season} · Week {week}" if week else f"{season}"


def _slug(report: dict, kind: str) -> str:
    season = (report or {}).get("season") or "na"
    week = (report or {}).get("week")
    tail = f"{season}-w{week}" if week else f"{season}"
    return f"{kind}-{tail}"


def _lines(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items)


# ── article builders (one per signal) ───────────────────────────────────────
def weather_article(report: dict) -> dict:
    """Teams whose forecast wind clears the notable threshold (passing downgrade)."""
    windy: list[tuple[str, float]] = []
    for code, meta in _teams(report):
        w = meta.get("weather") or {}
        if w.get("indoor"):
            continue
        mph = w.get("wind_mph")
        if isinstance(mph, (int, float)) and mph >= _WIND_NOTABLE:
            windy.append((code, float(mph)))
    windy.sort(key=lambda kv: -kv[1])

    period = _period(report)
    if windy:
        summary = f"{len(windy)} venue(s) forecast to blow — passing and kicking take a modeled haircut."
        body = (
            f"Wind is the single biggest weather lever on the model. For {period}, "
            f"these home venues are forecast at or above {_WIND_NOTABLE:.0f} mph, "
            "where the passing and kicking factors start clipping expected efficiency:\n\n"
            f"{_lines(f'{c}: {mph:.0f} mph' for c, mph in windy)}\n\n"
            "Fade nothing blindly — the factors clamp within bounded bands — but "
            "lean toward the run and downgrade long-field-goal equity in these spots."
        )
    else:
        summary = "No notable wind in the current forecast — passing stays neutral."
        body = (
            f"For {period}, no open-air venue clears the {_WIND_NOTABLE:.0f} mph wind "
            "threshold where the weather factors bite. Passing and kicking projections "
            "carry no wind penalty this slate. (Absent an ingested forecast, every open "
            "venue is treated as neutral by design.)"
        )
    return {
        "slug": _slug(report, "weather-watch"),
        "title": f"Weather watch — {period}",
        "summary": summary,
        "body": body,
        "category": "weather",
    }


def pace_article(report: dict) -> dict:
    """Fastest / slowest team pace — more plays, more fantasy opportunity."""
    paces = [
        (code, float(meta["team_pace"]))
        for code, meta in _teams(report)
        if isinstance(meta.get("team_pace"), (int, float))
    ]
    period = _period(report)
    if paces:
        paces.sort(key=lambda kv: kv[1])  # low seconds/play = fast
        fast = paces[:5]
        slow = paces[-5:][::-1]
        summary = "Pace sets the ceiling — the fastest offenses run the most plays."
        body = (
            "Team pace (seconds per play) scales raw opportunity: faster offenses "
            f"snap more plays, lifting every skill position's volume. For {period}:\n\n"
            "Fastest (most plays):\n"
            f"{_lines(f'{c}: {p:.1f}s/play' for c, p in fast)}\n\n"
            "Slowest (fewest plays):\n"
            f"{_lines(f'{c}: {p:.1f}s/play' for c, p in slow)}"
        )
    else:
        summary = "Team pace not yet ingested — opportunity treated as neutral."
        body = (
            f"For {period}, the team-scheme pace signal has not been ingested, so the "
            "pace factor is running at identity (no volume adjustment). This article "
            "refreshes automatically once pace data lands in the context artifact."
        )
    return {
        "slug": _slug(report, "pace-report"),
        "title": f"Pace report — {period}",
        "summary": summary,
        "body": body,
        "category": "pace",
    }


def passing_article(report: dict) -> dict:
    """Most pass-heavy / run-heavy offenses by neutral pass rate."""
    rates = [
        (code, float(meta["pass_rate"]))
        for code, meta in _teams(report)
        if isinstance(meta.get("pass_rate"), (int, float))
    ]
    period = _period(report)
    if rates:
        rates.sort(key=lambda kv: -kv[1])
        pass_heavy = rates[:5]
        run_heavy = rates[-5:][::-1]
        summary = "Pass rate splits the field — where the targets actually go."
        body = (
            "Pass rate is the cleanest read on where volume concentrates: pass-heavy "
            "offenses funnel to WR/TE, run-heavy ones to the backfield. For "
            f"{period}:\n\n"
            "Most pass-heavy:\n"
            f"{_lines(f'{c}: {r:.0%}' for c, r in pass_heavy)}\n\n"
            "Most run-heavy:\n"
            f"{_lines(f'{c}: {r:.0%}' for c, r in run_heavy)}"
        )
    else:
        summary = "Pass-rate tendencies not yet ingested — splits treated as neutral."
        body = (
            f"For {period}, pass-rate tendencies have not been ingested, so the "
            "pass-rate factor is at identity. This article refreshes once the "
            "team-scheme signal lands in the context artifact."
        )
    return {
        "slug": _slug(report, "passing-tendencies"),
        "title": f"Passing tendencies — {period}",
        "summary": summary,
        "body": body,
        "category": "passing",
    }


def venue_article(report: dict) -> dict:
    """Indoor (domed/retractable-closed) venues — weather-proof slate."""
    domes = [code for code, meta in _teams(report) if (meta.get("weather") or {}).get("indoor")]
    period = _period(report)
    if domes:
        summary = f"{len(domes)} indoor venue(s) — weather never touches these games."
        body = (
            "Indoor venues neutralize every weather factor by construction: no wind, "
            f"no precipitation, no cold. For {period}, these home venues play in a "
            "climate-controlled dome, so their passing and kicking projections carry "
            "zero environmental penalty:\n\n"
            f"{_lines(domes)}\n\n"
            "When you're chasing ceiling in bad-weather weeks, indoor games are the "
            "safe harbor for high-volume passing stacks."
        )
    else:
        summary = "No indoor venues resolved for this slate."
        body = (
            f"For {period}, no domed/indoor venue is present in the context artifact. "
            "Every game is weather-exposed to some degree — see the weather watch."
        )
    return {
        "slug": _slug(report, "indoor-venues"),
        "title": f"Indoor venues — {period}",
        "summary": summary,
        "body": body,
        "category": "venue",
    }


def war_room_article(projection: dict) -> dict:
    """The auto war-room brief — top projections decomposed into their drivers.

    E6 (no AI-in-loop): the engine's `why_report` already rendered the deterministic
    `brief` (summary + body) from the projection numbers; this builder lifts that prose
    verbatim and stamps a stable slug/category/provenance, so re-running is a pure in-place
    overwrite and the wording never diverges from the engine. Missing/empty artifact →
    honest degraded row (the PK set stays stable), mirroring the E3 article builders.
    """
    period = _period(projection)
    brief = (projection or {}).get("brief") or {}
    summary = brief.get("summary")
    body = brief.get("body")
    if not (isinstance(summary, str) and summary.strip() and isinstance(body, str) and body.strip()):
        summary = "Projection briefs not yet generated — the war room is dark."
        body = (
            f"For {period}, the engine has not published a projection-why artifact, so "
            "there is no war-room breakdown to show. This brief refreshes automatically "
            "once projections land (numbers in, prose out — no AI in the loop)."
        )
    return {
        "slug": _slug(projection, "war-room-brief"),
        "title": f"War room brief — {period}",
        "summary": summary,
        "body": body,
        "category": "war_room",
    }


# ── assembly ────────────────────────────────────────────────────────────────
def build_articles(report: dict, projection: dict | None = None) -> list[dict]:
    """The full, deterministic set of article rows for the context (+ optional projection).

    Every row is stamped with its source artifact's provenance so the feed is dated and
    self-describing. The slug set is fixed per season/week, so a re-run is a pure in-place
    overwrite (idempotent). The war-room brief (E6) is appended only when a projection-why
    artifact is supplied — it carries its OWN provenance, keeping the E3 context rows
    byte-identical whether or not projections exist."""
    if not report and not projection:
        return []

    def _stamp(rows: list[dict], src: dict) -> list[dict]:
        published_at = (src or {}).get("generated_at")
        source = (src or {}).get("source")
        for r in rows:
            if published_at:
                r["published_at"] = published_at
            r["source"] = source
        return rows

    rows: list[dict] = []
    if report:
        rows += _stamp(
            [weather_article(report), pace_article(report),
             passing_article(report), venue_article(report)],
            report,
        )
    if projection:
        rows += _stamp([war_room_article(projection)], projection)
    return rows


def load_report(path: Path = _ARTIFACT) -> dict:
    """Read E3's context artifact; empty dict if it hasn't been generated yet."""
    try:
        return json.loads(path.read_text())
    except Exception as e:  # missing/unwritten artifact → no articles this run
        console.print(f"[yellow]⚠ context artifact unavailable ({type(e).__name__}) — no articles[/yellow]")
        return {}


def load_projection(path: Path = _PROJECTION_ARTIFACT) -> dict:
    """Read the engine's projection-why artifact; empty dict if not yet generated (E6)."""
    try:
        return json.loads(path.read_text())
    except Exception as e:  # missing/unwritten → no war-room brief this run (degrade-safe)
        console.print(f"[yellow]⚠ projection-why artifact unavailable ({type(e).__name__}) — no war-room brief[/yellow]")
        return {}


def main() -> None:
    report = load_report()
    projection = load_projection()
    rows = build_articles(report, projection)
    if not rows:
        console.print("[dim]articles: nothing to publish (no context/projection artifact)[/dim]")
        return
    upsert("articles", rows, on_conflict="slug")
    console.print(f"[green]✓ generated {len(rows)} article(s) from context/projection reports[/green]")


if __name__ == "__main__":
    main()
