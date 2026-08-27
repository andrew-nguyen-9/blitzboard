"""Independent C04 live-consumer integration probe."""

from __future__ import annotations

import os
from pathlib import Path


def test_live_recommendations_consume_and_render_structured_explanations() -> None:
    root_value = os.environ.get("C04_PROD_ROOT")
    assert root_value, "C04_PROD_ROOT must name the C04 checkpoint worktree"
    root = Path(root_value)
    war_room = (root / "frontend/components/draft/DraftWarRoom.tsx").read_text()
    recommendations = (
        root / "frontend/components/draft/LiveRecommendations.tsx"
    ).read_text()

    # C04 is a live-scoring/explanation checkpoint, not a detached-library checkpoint.
    # The production recommendation path must call the explained scorer and pass its
    # structured payload to the rendered recommendation surface.
    assert "v6DraftLiveScoring" in war_room
    assert "scoreBoardWithExplanations(" in war_room
    assert "explanation" in war_room
    assert "explanation" in recommendations
    assert "formatDraftExplanation" in recommendations

