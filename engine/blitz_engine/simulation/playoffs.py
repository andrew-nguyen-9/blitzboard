"""Fixed single-elimination playoff bracket for the league season sim (E3).

Standard seeding bracket — seed 1 down one half, seed 2 down the other, adjacent seeds
paired (`1v8, 4v5, 2v7, 3v6` …) — with **byes for the top seeds** when the field is not a
power of two (exactly the ESPN/Yahoo fantasy layout). Because the bracket *shape* is fixed
by seed, a whole batch of Monte-Carlo seasons resolves vectorised: each round compares the
two participants' realised scores in that round's playoff week and advances the higher; a
tie breaks toward the better seed.

`ponytail:` the bracket is a tiny precomputed list of matchups (built once, independent of
the season count) evaluated by numpy fancy indexing — a loop over ~3 rounds, not a
framework.
"""
from __future__ import annotations

import numpy as np
import numpy.typing as npt

__all__ = ["Bracket", "build_bracket"]

# A round is a list of matches; a match is (ref_a, ref_b). A ref is either an int seed
# (0-based), ``None`` (an empty bye slot), or a ("W", round, match) back-reference to the
# winner of an earlier match.
_Ref = "int | None | tuple[str, int, int]"


def _seed_slots(size: int) -> list[int]:
    """Bracket-slot order of 0-based seeds for a field of ``size`` (a power of two)."""
    order = [0]
    while len(order) < size:
        m = len(order) * 2
        order = [x for s in order for x in (s, m - 1 - s)]
    return order


class Bracket:
    """A fixed seeding bracket, resolvable over a batch of seasons.

    ``rounds`` is the precomputed matchup tree; ``n_rounds`` playoff weeks are consumed
    (round ``r`` uses playoff week ``r``). ``n_byes`` top seeds skip the first round.
    """

    def __init__(self, playoff_teams: int) -> None:
        if playoff_teams < 2:
            raise ValueError("playoff_teams must be >= 2")
        size = 1
        while size < playoff_teams:
            size *= 2
        self.playoff_teams = playoff_teams
        self.n_byes = size - playoff_teams
        slots: list[object] = [s if s < playoff_teams else None for s in _seed_slots(size)]
        rounds: list[list[tuple[object, object]]] = []
        cur = slots
        r = 0
        while len(cur) > 1:
            matches = [(cur[i], cur[i + 1]) for i in range(0, len(cur), 2)]
            rounds.append(matches)
            cur = [("W", r, i) for i in range(len(matches))]
            r += 1
        self.rounds = rounds
        self.n_rounds = len(rounds)

    def resolve(
        self, seed_scores: npt.NDArray[np.floating]
    ) -> tuple[npt.NDArray[np.int64], tuple[npt.NDArray[np.int64], npt.NDArray[np.int64]]]:
        """Play out the bracket for every season in the batch.

        ``seed_scores`` has shape ``(B, n_rounds, playoff_teams)`` — the realised score of
        each seed (0-based) in each playoff round's week. Returns ``(champion_seed,
        (finalist_a_seed, finalist_b_seed))``, each a ``(B,)`` array of 0-based seed indices.
        """
        b = seed_scores.shape[0]
        rows = np.arange(b)
        results: dict[tuple[int, int], npt.NDArray[np.int64]] = {}

        def seed_of(ref: object) -> npt.NDArray[np.int64] | None:
            if ref is None:
                return None
            if isinstance(ref, tuple):  # ("W", round, match)
                return results[(ref[1], ref[2])]
            assert isinstance(ref, int)
            return np.full(b, ref, dtype=np.int64)  # a fixed seed

        for r, matches in enumerate(self.rounds):
            score_r = seed_scores[:, r, :]
            for i, (a, b_ref) in enumerate(matches):
                sa, sb = seed_of(a), seed_of(b_ref)
                if sa is None and sb is None:
                    raise ValueError("empty bracket match")
                if sa is None:
                    results[(r, i)] = sb  # type: ignore[assignment]
                    continue
                if sb is None:
                    results[(r, i)] = sa
                    continue
                pa, pb = score_r[rows, sa], score_r[rows, sb]
                a_wins = (pa > pb) | ((pa == pb) & (sa < sb))  # tie -> better (lower) seed
                results[(r, i)] = np.where(a_wins, sa, sb)

        champ = results[(self.n_rounds - 1, 0)]
        fa, fb = self.rounds[-1][0]
        final_a = seed_of(fa)
        final_b = seed_of(fb)
        assert final_a is not None and final_b is not None
        return champ, (final_a, final_b)


def build_bracket(playoff_teams: int) -> Bracket:
    """Construct the standard seeding bracket for ``playoff_teams`` (byes when non-2^k)."""
    return Bracket(playoff_teams)
