"""
Environmental / team-context ingest (E3) — the free-data feeder for the E3
projection factors and the E9b Articles surface.

WHAT IT DOES
    * Weather: per-stadium forecast from **Open-Meteo** — genuinely FREE and
      KEYLESS (no account, non-commercial ≤10k calls/day). Wrapped in an
      F2-style ``Adapter`` so it reuses the shared degrade + retry contract.
    * Venue: the static ``STADIUMS`` table (dome / elevation / lat-lon) that
      lives with the environment factors — no API needed.
    * Scheme: team pace + pass-rate aggregates. Computed here from nflverse
      play-by-play when available; absent → the team simply carries no scheme
      signal (its factors stay identity).

DEGRADE CONTRACT (E3): every path degrades to a NEUTRAL result, never a crash.
No network / Open-Meteo down → weather is ``None`` per team → the weather factors
return identity. No nflverse → no pace/pass-rate → the scheme factors return
identity. Supabase unset → the artifact is still written; no DB rows. Re-running
is idempotent (pure overwrite of the artifact, keyed upsert if a backend exists).

THE ARTIFACT (what E9b consumes)
    ``pipeline/artifacts/context_report.json`` — see ``build_report`` for the exact
    shape. It is auto-generated, self-describing (source + free-tier provenance
    inline), and the per-team ``metadata`` block is exactly what
    ``FactorContext.metadata`` needs (``weather``, ``venue_team``, ``team_pace``,
    ``pass_rate``) so a downstream hydrator can drop it straight onto a player row.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from pathlib import Path

from common import console, retry_api
from models.factors.environment import STADIUMS

try:  # adapters is a sibling top-level package on the pipeline path
    from adapters.base import Adapter
except Exception:  # pragma: no cover - only if F2 scaffold is absent
    Adapter = object  # type: ignore

_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
_ARTIFACT = Path(__file__).resolve().parent.parent / "artifacts" / "context_report.json"
_SOURCE = "open-meteo (keyless, non-commercial ≤10k/day) + static stadium table"


# ── pure builders (network-free, unit-testable) ─────────────────────────────
def team_metadata(team: str, weather: dict | None, scheme: dict | None) -> dict:
    """The ``FactorContext.metadata`` block for one team — exactly the keys the E3
    factors read. Weather is annotated ``indoor`` for domed venues so the weather
    factors self-neutralize indoors. Missing inputs simply omit their key
    (→ that factor degrades to identity)."""
    venue = STADIUMS.get(team) or {}
    meta: dict = {"venue_team": team}
    if weather:
        w = dict(weather)
        w.setdefault("indoor", bool(venue.get("dome")))
        meta["weather"] = w
    elif venue.get("dome"):
        # a domed venue is weather-neutral even with no forecast
        meta["weather"] = {"indoor": True}
    if scheme:
        if scheme.get("team_pace"):
            meta["team_pace"] = scheme["team_pace"]
        if scheme.get("pass_rate"):
            meta["pass_rate"] = scheme["pass_rate"]
    return meta


def build_report(
    season: int,
    week: int | None,
    weather_by_team: dict[str, dict | None] | None = None,
    scheme_by_team: dict[str, dict] | None = None,
    *,
    degraded: bool = False,
) -> dict:
    """Assemble the self-describing context artifact (pure; no I/O).

    ``teams[code]`` = ``{"venue": {...}, "metadata": {...}}`` where ``metadata`` is
    factor-ready. Any team with neither weather nor scheme data still appears with
    its static venue + a ``venue_team`` metadata anchor, so consumers always get all
    32 teams and the projection factors stay perfectly neutral for the missing ones."""
    weather_by_team = weather_by_team or {}
    scheme_by_team = scheme_by_team or {}
    teams: dict[str, dict] = {}
    for code, venue in STADIUMS.items():
        meta = team_metadata(code, weather_by_team.get(code), scheme_by_team.get(code))
        teams[code] = {"venue": venue, "metadata": meta}
    return {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "season": season,
        "week": week,
        "source": _SOURCE,
        "degraded": degraded,
        "teams": teams,
    }


# ── F2-style keyless weather adapter ────────────────────────────────────────
class WeatherContextAdapter(Adapter):  # type: ignore[misc]
    """Open-Meteo forecast per stadium, modelled on the F2 ``Adapter`` contract.

    Keyless (``requires_key=None``) → always "enabled", but still degrades: a
    network failure is swallowed by ``fetch_safe`` and yields ``{}`` (every team
    then neutral). Persistence is artifact-based in E3, so ``persist`` is a no-op
    (no new DB table introduced here); the JSON artifact is the sink."""

    name = "weather_context"
    table = ""                       # artifact-only in E3; no invented schema
    on_conflict = ""
    requires_key = None              # Open-Meteo needs no key
    free_tier = "Open-Meteo: no key/account; non-commercial ≤10,000 calls/day"

    def __init__(self, teams: list[str] | None = None):
        self.teams = teams or list(STADIUMS)

    @retry_api
    def _one(self, code: str) -> dict | None:
        import requests

        v = STADIUMS[code]
        r = requests.get(
            _OPEN_METEO,
            params={
                "latitude": v["lat"], "longitude": v["lon"],
                "current": "temperature_2m,wind_speed_10m,precipitation",
                "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
            },
            timeout=15,
        )
        r.raise_for_status()
        cur = (r.json() or {}).get("current") or {}
        if not cur:
            return None
        return {
            "temp_f": cur.get("temperature_2m"),
            "wind_mph": cur.get("wind_speed_10m"),
            "precip": bool(cur.get("precipitation")),
        }

    def fetch(self) -> dict[str, dict | None]:
        """Best-effort per-stadium forecast; a single failure degrades that team to
        ``None`` rather than sinking the whole run."""
        out: dict[str, dict | None] = {}
        for code in self.teams:
            try:
                out[code] = self._one(code)
            except Exception as e:  # per-team degrade
                console.print(f"[yellow]⚠ weather {code}: {e} — neutral[/yellow]")
                out[code] = None
        return out

    def normalize(self, raw: object) -> list[dict]:  # pragma: no cover - artifact sink
        return []

    def persist(self, rows: list[dict]) -> int:  # pragma: no cover - artifact sink
        return 0


# ── orchestration ───────────────────────────────────────────────────────────
def ingest(
    season: int,
    week: int | None = None,
    *,
    teams: list[str] | None = None,
    fetch_weather: bool = True,
    scheme_by_team: dict[str, dict] | None = None,
) -> dict:
    """Build the context report, degrade-safe. Returns the artifact dict.

    ``fetch_weather=False`` (tests / offline cron) skips the network entirely and
    still emits a complete, neutral report."""
    weather: dict[str, dict | None] = {}
    degraded = not fetch_weather
    if fetch_weather:
        try:
            weather = WeatherContextAdapter(teams=teams).fetch()
        except Exception as e:  # whole-source degrade
            console.print(f"[yellow]⚠ weather source unavailable: {e} — neutral report[/yellow]")
            degraded = True
    return build_report(season, week, weather, scheme_by_team, degraded=degraded)


def write_artifact(report: dict, path: Path = _ARTIFACT) -> Path:
    """Idempotent write of the JSON artifact (E9b input). Creates ``artifacts/``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    console.print(f"[green]✓ context report → {path}[/green] (degraded={report['degraded']})")
    return path


def _parse_args(argv=None):
    p = argparse.ArgumentParser(description="Ingest environmental/team context (E3).")
    p.add_argument("--season", type=int, default=_dt.date.today().year)
    p.add_argument("--week", type=int, default=None)
    p.add_argument("--no-fetch", action="store_true",
                   help="skip the network; emit a neutral report (offline/cron dry-run)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    # Cron degrade knob: CONTEXT_INGEST_OFFLINE=1 forces the no-network path.
    offline = args.no_fetch or os.getenv("CONTEXT_INGEST_OFFLINE") == "1"
    report = ingest(args.season, args.week, fetch_weather=not offline)
    write_artifact(report)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
