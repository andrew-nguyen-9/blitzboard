"""Unit tests for the article generator (Epic 9b).

Covers the claims that matter: the E3 context artifact → article-row mapping is
correct for both a populated and a neutral report, the slug set is FIXED per
season/week (idempotent overwrite), and every row exposes exactly the columns
E9a search reads (slug/title/summary) plus the render body.

Runs under pytest OR as a plain script (no pytest in a bare venv):
    python tests/test_articles_generate.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import articles_generate as ag  # noqa: E402

# Minimal E3-shaped artifact: one windy open venue, one dome, pace + pass_rate.
_POPULATED = {
    "generated_at": "2025-09-10T12:00:00+00:00",
    "season": 2025,
    "week": 2,
    "source": "open-meteo (keyless) + static stadium table",
    "degraded": False,
    "teams": {
        "BUF": {"metadata": {"venue_team": "BUF", "weather": {"wind_mph": 22.0, "indoor": False},
                              "team_pace": 26.0, "pass_rate": 0.62}},
        "DET": {"metadata": {"venue_team": "DET", "weather": {"indoor": True},
                             "team_pace": 24.5, "pass_rate": 0.58}},
        "TEN": {"metadata": {"venue_team": "TEN", "weather": {"wind_mph": 4.0, "indoor": False},
                             "team_pace": 30.0, "pass_rate": 0.45}},
    },
}

_NEUTRAL = {  # degraded / no-fetch: domes only, no pace/pass_rate/wind
    "generated_at": "2025-09-10T12:00:00+00:00",
    "season": 2025,
    "week": None,
    "source": "static stadium table",
    "degraded": True,
    "teams": {
        "ARI": {"metadata": {"venue_team": "ARI", "weather": {"indoor": True}}},
        "CHI": {"metadata": {"venue_team": "CHI"}},
    },
}

_REQUIRED_COLS = {"slug", "title", "summary", "body", "category"}


def test_populated_mapping():
    rows = ag.build_articles(_POPULATED)
    assert len(rows) == 4
    by_cat = {r["category"]: r for r in rows}
    assert set(by_cat) == {"weather", "pace", "passing", "venue"}

    # every row carries the search-contract + render columns + provenance
    for r in rows:
        assert _REQUIRED_COLS <= set(r), r
        assert r["published_at"] == "2025-09-10T12:00:00+00:00"
        assert r["source"] == _POPULATED["source"]
        for col in ("title", "summary", "body"):
            assert isinstance(r[col], str) and r[col].strip()

    # BUF (22 mph) is flagged windy; TEN (4 mph) is not; DET is indoor → dome
    assert "BUF" in by_cat["weather"]["body"]
    assert "TEN" not in by_cat["weather"]["body"]
    assert "DET" in by_cat["venue"]["body"]
    # pace/passing surface the teams that have the signal
    assert "BUF" in by_cat["pace"]["body"] and "TEN" in by_cat["pace"]["body"]
    assert "62%" in by_cat["passing"]["body"]  # BUF pass_rate formatted
    print("✓ populated artifact → 4 correct, provenance-stamped articles")


def test_neutral_degrades_gracefully():
    rows = ag.build_articles(_NEUTRAL)
    assert len(rows) == 4  # same fixed set even with no signals
    by_cat = {r["category"]: r for r in rows}
    # no wind data → weather article says neutral, doesn't invent teams
    assert "neutral" in by_cat["weather"]["summary"].lower()
    # no pace/pass_rate → honest "not yet ingested"
    assert "not yet ingested" in by_cat["pace"]["summary"].lower()
    assert "not yet ingested" in by_cat["passing"]["summary"].lower()
    # ARI dome still surfaces
    assert "ARI" in by_cat["venue"]["body"]
    print("✓ neutral/degraded artifact degrades to stable, honest rows")


def test_slugs_fixed_and_idempotent():
    a = [r["slug"] for r in ag.build_articles(_POPULATED)]
    b = [r["slug"] for r in ag.build_articles(_POPULATED)]
    assert a == b, "slug set must be deterministic across runs"
    assert len(set(a)) == 4, "slugs must be unique (PK for upsert)"
    # week folds into the slug so different weeks don't collide
    assert all("2025-w2" in s for s in a), a
    weekless = [r["slug"] for r in ag.build_articles(_NEUTRAL)]
    assert all("2025-w2" not in s and "2025" in s for s in weekless), weekless
    print("✓ slug set fixed per season/week (idempotent upsert key)")


def test_empty_report_no_rows():
    assert ag.build_articles({}) == []
    print("✓ empty/absent artifact → zero rows (degrade-safe)")


if __name__ == "__main__":
    test_populated_mapping()
    test_neutral_degrades_gracefully()
    test_slugs_fixed_and_idempotent()
    test_empty_report_no_rows()
    print("\nall articles_generate tests passed")
