"""Machine-checkable signal cards and completeness audits."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

SignalState = Literal["implemented", "candidate", "blocked", "excluded"]
ModelEligibility = Literal["eligible", "shadow", "zero_weight", "excluded"]


@dataclass(frozen=True)
class SignalCard:
    id: str
    family: str
    description: str
    state: SignalState
    primary_source: str | None
    fallback_sources: tuple[str, ...]
    source_tier: int | None
    license: str
    timestamp_semantics: str
    identity_semantics: str
    cadence: str
    missingness: str
    leakage_risk: str
    storage_estimate_mb: float
    model_eligibility: ModelEligibility
    tests: tuple[str, ...]
    value_hypothesis: str
    privacy: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SignalCard:
        values = dict(data)
        values["fallback_sources"] = tuple(values.get("fallback_sources", ()))
        values["tests"] = tuple(values.get("tests", ()))
        card = cls(**values)
        card.validate()
        return card

    def validate(self) -> None:
        if not self.id or not self.family or not self.description:
            raise ValueError("signal id, family, and description are required")
        if self.source_tier not in {None, 1, 2, 3}:
            raise ValueError(f"{self.id}: source_tier must be 1, 2, 3, or null")
        if self.storage_estimate_mb < 0:
            raise ValueError(f"{self.id}: storage estimate cannot be negative")
        if self.state == "implemented" and (not self.primary_source or not self.tests):
            raise ValueError(f"{self.id}: implemented signals need a source and tests")
        safe_sensitive_states = {"zero_weight", "excluded"}
        if self.privacy == "sensitive" and self.model_eligibility not in safe_sensitive_states:
            raise ValueError(f"{self.id}: sensitive signals cannot be model-eligible")
        if self.state == "excluded" and self.model_eligibility != "excluded":
            raise ValueError(f"{self.id}: excluded signals must be excluded from modeling")


@dataclass(frozen=True)
class CoverageAudit:
    total: int
    implemented: int
    gaps: tuple[str, ...]
    blocked: tuple[str, ...]
    excluded: tuple[str, ...]
    estimated_storage_mb: float
    families: tuple[str, ...]

    @property
    def coverage_rate(self) -> float:
        eligible = self.total - len(self.excluded)
        return self.implemented / eligible if eligible else 1.0


def load_registry(path: str | Path) -> tuple[SignalCard, ...]:
    payload = json.loads(Path(path).read_text())
    if payload.get("schema_version") != 1 or not isinstance(payload.get("signals"), list):
        raise ValueError("signal registry schema drift")
    cards = tuple(SignalCard.from_dict(item) for item in payload["signals"])
    ids = [card.id for card in cards]
    if len(ids) != len(set(ids)):
        raise ValueError("signal registry contains duplicate ids")
    return cards


def audit_registry(cards: tuple[SignalCard, ...]) -> CoverageAudit:
    return CoverageAudit(
        total=len(cards),
        implemented=sum(card.state == "implemented" for card in cards),
        gaps=tuple(card.id for card in cards if card.state == "candidate"),
        blocked=tuple(card.id for card in cards if card.state == "blocked"),
        excluded=tuple(card.id for card in cards if card.state == "excluded"),
        estimated_storage_mb=sum(card.storage_estimate_mb for card in cards),
        families=tuple(sorted({card.family for card in cards})),
    )
