from __future__ import annotations

from datetime import UTC, datetime

import pytest

from blitz_engine.intelligence.context import (
    ContextEvent,
    CredibilityEvidence,
    validate_feature_catalog,
)

NOW = datetime(2026, 8, 25, tzinfo=UTC)
CREDIBLE = CredibilityEvidence(3, 3, 2, 3, 2, 3)


def _event(**changes) -> ContextEvent:
    values = {
        "event_id": "weather-game-1-wind",
        "family": "weather",
        "entity_id": "2026_01_CHI_GB",
        "as_of_utc": NOW,
        "source_url": "https://api.weather.gov/gridpoints/example",
        "source_tier": 1,
        "credibility": CREDIBLE,
        "feature_name": "wind_speed_mps",
        "value": 8.0,
        "unit": "m/s",
        "valid_at_utc": datetime(2026, 9, 10, tzinfo=UTC),
        "uncertainty": 0.2,
    }
    values.update(changes)
    return ContextEvent(**values)


def test_weather_and_travel_catalog_accepts_defined_features() -> None:
    validate_feature_catalog([
        _event(),
        _event(event_id="travel", family="travel", feature_name="time_zones_crossed", value=2),
    ])


def test_personal_context_is_public_relevant_and_zero_weight() -> None:
    event = _event(
        event_id="public-context",
        family="personal_public",
        entity_id="00-001",
        feature_name="contract_dispute_or_holdout",
        value=True,
        public_relevance="May change reporting date and workload; research-only until validated.",
    )
    validate_feature_catalog([event])
    with pytest.raises(ValueError, match="zero-weight"):
        validate_feature_catalog([ContextEvent(**{**event.__dict__, "modeling_weight": 0.01})])


@pytest.mark.parametrize(
    "feature", ["protected_trait", "private_family_detail", "undisclosed_diagnosis",
                "anonymous_gossip", "inferred_mental_state", "invasive_surveillance"]
)
def test_excluded_personal_features_are_rejected(feature: str) -> None:
    with pytest.raises(ValueError, match="excluded personal"):
        validate_feature_catalog([_event(
            event_id=feature, family="personal_public", feature_name=feature, value=True,
            public_relevance="should never be collected",
        )])


def test_credibility_rubric_is_deterministic_and_bounded() -> None:
    assert CREDIBLE.score() == pytest.approx(0.9)
    with pytest.raises(ValueError, match="0 through 3"):
        CredibilityEvidence(4, 1, 1, 1, 1, 1).score()


def test_context_rejects_naive_timestamp_and_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _event(as_of_utc=datetime(2026, 8, 25)).validate()
    with pytest.raises(ValueError, match="duplicate"):
        validate_feature_catalog([_event(), _event()])
