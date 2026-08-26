"""Context-event schemas with conservative credibility and modeling gates."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ContextFamily = Literal[
    "weather", "venue", "travel", "market", "trade_scenario", "personal_public"
]


@dataclass(frozen=True)
class CredibilityEvidence:
    authority: int
    directness: int
    corroboration: int
    recency: int
    correction_history: int
    specificity: int

    def score(self) -> float:
        values = (
            self.authority,
            self.directness,
            self.corroboration,
            self.recency,
            self.correction_history,
            self.specificity,
        )
        if any(value not in range(4) for value in values):
            raise ValueError("credibility dimensions must be integers from 0 through 3")
        weights = (0.25, 0.20, 0.20, 0.10, 0.10, 0.15)
        return sum(value / 3 * weight for value, weight in zip(values, weights, strict=True))


@dataclass(frozen=True)
class ContextEvent:
    event_id: str
    family: ContextFamily
    entity_id: str
    as_of_utc: datetime
    source_url: str
    source_tier: int
    credibility: CredibilityEvidence
    feature_name: str
    value: str | float | int | bool
    unit: str | None = None
    valid_at_utc: datetime | None = None
    uncertainty: float | None = None
    modeling_weight: float = 0.0
    public_relevance: str = ""

    def validate(self) -> None:
        if self.as_of_utc.tzinfo is None:
            raise ValueError("as_of_utc must be timezone-aware")
        if self.valid_at_utc is not None and self.valid_at_utc.tzinfo is None:
            raise ValueError("valid_at_utc must be timezone-aware")
        if self.source_tier not in {1, 2, 3}:
            raise ValueError("source_tier must be 1, 2, or 3")
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must use HTTPS")
        if self.uncertainty is not None and not 0 <= self.uncertainty <= 1:
            raise ValueError("uncertainty must be between 0 and 1")
        if self.family == "personal_public":
            if self.modeling_weight != 0:
                raise ValueError("personal context is zero-weight until empirical promotion")
            if not self.public_relevance:
                raise ValueError(
                    "personal context needs a documented football relevance hypothesis"
                )


WEATHER_FEATURES = frozenset({
    "temperature_c", "precipitation_probability", "wind_speed_mps", "wind_gust_mps",
    "humidity_pct", "roof_state", "surface", "altitude_m", "forecast_horizon_hours",
})
TRAVEL_FEATURES = frozenset({
    "distance_km", "time_zones_crossed", "travel_direction", "rest_days",
    "local_kickoff_hour", "international_game", "altitude_change_m",
})
PERSONAL_PUBLIC_CATEGORIES = frozenset({
    "bereavement_or_family_leave", "legal_proceeding", "contract_dispute_or_holdout",
    "team_discipline", "major_public_family_event", "public_relationship_event_research_only",
    "public_controversy_research_only",
})
EXCLUDED_PERSONAL_CATEGORIES = frozenset({
    "protected_trait", "private_family_detail", "undisclosed_diagnosis", "anonymous_gossip",
    "inferred_mental_state", "invasive_surveillance",
})


def validate_feature_catalog(events: list[ContextEvent]) -> None:
    ids: set[str] = set()
    for event in events:
        event.validate()
        if event.event_id in ids:
            raise ValueError(f"duplicate context event: {event.event_id}")
        ids.add(event.event_id)
        if event.family == "weather" and event.feature_name not in WEATHER_FEATURES:
            raise ValueError(f"unknown weather feature: {event.feature_name}")
        if event.family == "travel" and event.feature_name not in TRAVEL_FEATURES:
            raise ValueError(f"unknown travel feature: {event.feature_name}")
        if event.family == "personal_public":
            if event.feature_name in EXCLUDED_PERSONAL_CATEGORIES:
                raise ValueError(f"excluded personal feature: {event.feature_name}")
            if event.feature_name not in PERSONAL_PUBLIC_CATEGORIES:
                raise ValueError(f"unreviewed personal feature: {event.feature_name}")
