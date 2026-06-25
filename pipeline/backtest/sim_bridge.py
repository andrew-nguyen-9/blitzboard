"""Spawn the Node draft-sim (frontend/scripts/draftSim.ts) for one mock draft.

Keeps the TS policy as the single source of truth (acceptance D7): the harness never
re-implements pick logic, it shells out to the same code the live board uses. Runs via
the repo-local tsx binary so it works offline (no per-call npx network fetch)."""
from __future__ import annotations

import json
import os
import subprocess

_FRONTEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
_TSX = os.path.join("node_modules", ".bin", "tsx")


def run_draft(players: list[dict], seed: int, num_teams: int = 12, policy: str = "v2") -> list[list[str]]:
    """Run one deterministic snake draft; return rosters as per-team lists of player ids."""
    payload = json.dumps({"players": players, "numTeams": num_teams, "seed": seed, "policy": policy})
    proc = subprocess.run(
        [_TSX, "scripts/draftSim.ts"],
        input=payload, capture_output=True, text=True, cwd=_FRONTEND,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"draftSim failed ({proc.returncode}): {proc.stderr.strip()}")
    return json.loads(proc.stdout)["rosters"]
