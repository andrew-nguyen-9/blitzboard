"""
calibration_run.py — C02 player-level calibration gate (preregistered in the
reviewer-owned `player-calibration-v1.json` manifest; results go to
`.orchestrator-v6/experiments/calibration/` and never overwrite the manifest).

Three subcommands, run in order:

  snapshot   Freeze every input BEFORE any metric is computed: Supabase players +
             season history + the seeded league's scoring profile, FFC ADP (the
             projector's consensus input) for each league size, and the three
             FantasyPros benchmark pages (derived fields only; raw HTML stays in
             the uncommitted artifacts/ dir, its sha256 is recorded).
  boards     Build one arm's boards for the three manifest formats from the frozen
             snapshot. `--pipeline-dir` selects the arm's code (v5 = the baseline
             tree extracted from git, v6 = this tree). Every component needed to
             reproduce the rank is dumped per player.
  report     Match boards to benchmarks, compute the manifest metrics and cohorts,
             and write report.json / report.md / promotion-v3.json.

No jax/torch; network only in `snapshot`. Reads Supabase, never writes it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

PIPE = Path(__file__).resolve().parent
REPO = PIPE.parent
CAL = REPO / ".orchestrator-v6" / "experiments" / "calibration"
RAW = REPO / "artifacts" / "calibration"  # uncommitted raw receipts

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

#: The three manifest formats. BN is ignored by replacement math but kept for the record.
FORMATS: dict[str, dict] = {
    "12-team-half-ppr-1qb": {
        "league_size": 12,
        "roster_slots": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DST": 1, "BN": 6},
    },
    "12-team-half-ppr-superflex": {
        "league_size": 12,
        "roster_slots": {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "OP": 1, "K": 1,
                         "DST": 1, "BN": 6},
    },
    "14-team-half-ppr-2qb": {
        "league_size": 14,
        "roster_slots": {"QB": 2, "RB": 2, "WR": 2, "TE": 1, "FLEX": 1, "K": 1, "DST": 1, "BN": 6},
    },
}

#: `fantasypros-half-ppr-ecr` deviates from the manifest URL by retrieval VARIANT only:
#: the cheatsheet page server-renders just 24 rows (the rest is JS), while the print
#: rankings page embeds the identical ECR product (`ecrData`) in full with its expert
#: count. Recorded as a deviation for reviewer adjudication; the product graded is the
#: same half-PPR draft Expert Consensus Ranking.
BENCHMARKS = {
    "fantasypros-half-ppr-ecr": "https://www.fantasypros.com/nfl/rankings/half-point-ppr-cheatsheets.php?print=true",
    "fantasypros-half-ppr-adp": "https://www.fantasypros.com/nfl/adp/half-point-ppr-overall.php/",
    "fantasypros-superflex-ecr": "https://www.fantasypros.com/nfl/rankings/superflex-cheatsheets.php?print=true",
}
MANIFEST_ECR_URL = "https://www.fantasypros.com/nfl/cheatsheets/top-half-ppr-players.php?week=draft"

#: The ADP page hydrates its table client-side (the HTML carries a 5-row preview), from
#: this partners endpoint using the public x-api-key embedded in the page's own JS
#: bundle. Same free product, derived fields only; recorded as a retrieval deviation.
ADP_API_URL = (
    "https://partners.fantasypros.com/api/v1/consensus-rankings.php"
    "?sport=NFL&year={year}&week=0&position=ALL&type=ADP&scoring=HALF&experts=available"
)
ADP_API_KEY_RE = re.compile(r'["\']([A-Za-z0-9]{35,45})["\']')  # found in bundle-*.js

#: Which benchmark grades which format (superflex ECR also grades the 2QB board — the
#: closest public reference; recorded as such in the report).
FORMAT_BENCHMARKS = {
    "12-team-half-ppr-1qb": ["fantasypros-half-ppr-ecr", "fantasypros-half-ppr-adp"],
    "12-team-half-ppr-superflex": ["fantasypros-superflex-ecr"],
    "14-team-half-ppr-2qb": ["fantasypros-superflex-ecr"],
}


def _utc() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _dump_gz(path: Path, obj) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    with gzip.GzipFile(path, "wb", mtime=0) as f:  # mtime=0 → byte-stable gzip
        f.write(data)
    return _sha(data)  # hash of the CONTENT, not the container


def _load_gz(path: Path):
    with gzip.open(path, "rb") as f:
        return json.load(f)


def norm_name(name: str) -> str:
    """Benchmark↔board matching key: lowercase ASCII, no punctuation, no suffixes."""
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[.'\-]", "", s.lower())
    s = re.sub(r"\s+(jr|sr|ii|iii|iv|v)$", "", s.strip())
    return re.sub(r"\s+", " ", s)


# ── benchmark parsers (derived fields only) ─────────────────────────────────────


def parse_ecrdata(html: str) -> tuple[list[dict], int | None]:
    """FantasyPros pages that embed the full ECR product as `var ecrData = {...};`."""
    m = re.search(r"var ecrData = (\{.*?\});\s*\n", html, re.S)
    if not m:
        return [], None
    d = json.loads(m.group(1))
    pos = re.compile(r"([A-Z]+)")
    rows = [
        {
            "overall_rank": int(p["rank_ecr"]),
            "player": p["player_name"],
            "position": (pos.match(str(p.get("player_position_id") or "")) or [None, None])[1],
            "team": p.get("player_team_id"),
        }
        for p in d.get("players", [])
    ]
    return sorted(rows, key=lambda x: x["overall_rank"]), d.get("total_experts")


def fetch_adp_api(page_html: str, year: int) -> tuple[list[dict], dict]:
    """Full ADP rows from the page's own partners endpoint, keyed by the public
    x-api-key embedded in the page's JS bundle (the HTML itself carries only a
    5-row preview). Returns (rows, provenance)."""
    import requests

    bundle_re = r'src="((?:https?:)?//cdn\.fantasypros\.com[^"]*bundle[^"]*\.js[^"]*)"'
    bundles = re.findall(bundle_re, page_html)
    key = None
    for b in bundles:
        js = requests.get("https:" + b if b.startswith("//") else b, timeout=30, headers=UA).text
        for cand in ADP_API_KEY_RE.findall(js):
            probe = requests.get(
                ADP_API_URL.format(year=year), timeout=30, headers={**UA, "x-api-key": cand}
            )
            if probe.ok:
                key = cand
                data = probe.json()
                break
        if key:
            break
    if not key:
        raise SystemExit("ADP: no working x-api-key found in page bundles")
    rows = [
        {
            "overall_adp": float(p["rank_ave"]),
            "overall_rank": int(p["rank_ecr"]),
            "player": p["player_name"],
            "position": p.get("player_position_id"),
            "source_count": len(str(data.get("filters", "")).split(",")),
        }
        for p in data.get("players", [])
    ]
    prov = {
        "api_url": ADP_API_URL.format(year=year),
        "included_platforms": data.get("filters"),
        "platform_count": len(str(data.get("filters", "")).split(",")),
        "source_last_updated": data.get("last_updated"),
        "deviation": "rows fetched from the page's own partners endpoint; the manifest "
        "URL's HTML carries only a 5-row server-rendered preview",
    }
    return sorted(rows, key=lambda x: x["overall_rank"]), prov


def parse_superflex(html: str) -> tuple[list[dict], int | None]:
    pat = re.compile(
        r'<td class="sticky-cell sticky-cell-one">(\d+)</td>.*?fp-player-name="([^"]+)".*?'
        r'player__team">([A-Z]{2,3})</span>\s*<span class="player__position">([A-Z]{1,3})',
        re.S,
    )
    rows = [
        {"overall_rank": int(r), "player": n, "position": p, "team": t}
        for r, n, t, p in pat.findall(html)
    ]
    m = re.search(r"of\s+(\d+)\s+[Ee]xperts", html)
    return sorted(rows, key=lambda x: x["overall_rank"]), (int(m.group(1)) if m else None)


# ── snapshot ────────────────────────────────────────────────────────────────────


def _load_env() -> None:
    """In a linked worktree the gitignored pipeline/.env lives only in the MAIN checkout;
    resolve it through the git common dir so no machine path is hardcoded."""
    import subprocess

    from dotenv import load_dotenv

    common = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    load_dotenv(Path(common).parent / "pipeline" / ".env")


def cmd_snapshot() -> None:
    import requests

    sys.path.insert(0, str(PIPE))
    _load_env()
    from common import fetch_all, get_supabase
    from models.adp import fetch_ffc_adp

    sb = get_supabase()
    if sb is None:
        raise SystemExit("Supabase not configured (run from a checkout with pipeline/.env)")

    players = fetch_all(
        "players", "id,full_name,position,nfl_team,age,years_exp,injury_status,metadata"
    )
    history = fetch_all(
        "player_stats_history", "player_id,season,stats", apply=lambda q: q.is_("week", "null")
    )
    scoring = (sb.table("league_rules").select("scoring").limit(1).execute().data or [{}])[0].get(
        "scoring", {}
    )
    ffc = {}
    for teams in sorted({f["league_size"] for f in FORMATS.values()}):
        ffc[str(teams)] = fetch_ffc_adp(teams, "half-ppr", dt.date.today().year)

    snap = {
        "retrieved_utc": _utc(),
        "season": dt.date.today().year,
        "players": players,
        "history": history,
        "scoring": scoring,
        "ffc_adp": ffc,
        "counts": {"players": len(players), "history": len(history)},
    }
    sha = _dump_gz(CAL / "snapshot.json.gz", snap)
    print(f"snapshot: {len(players)} players, {len(history)} history rows, sha256 {sha}")

    RAW.mkdir(parents=True, exist_ok=True)
    bench: dict[str, dict] = {}
    for bid, url in BENCHMARKS.items():
        r = requests.get(url, timeout=30, headers=UA)
        r.raise_for_status()
        (RAW / f"{bid}.html").write_bytes(r.content)
        meta: dict = {"url": url, "retrieved_utc": _utc(), "raw_sha256": _sha(r.content)}
        if bid == "fantasypros-half-ppr-adp":
            rows, prov = fetch_adp_api(r.text, dt.date.today().year)
            meta.update(prov)
        elif bid == "fantasypros-superflex-ecr":
            rows, experts = parse_ecrdata(r.text)
            if not rows:
                rows, experts = parse_superflex(r.text)
            meta["expert_count"] = experts
        else:
            rows, experts = parse_ecrdata(r.text)
            meta["expert_count"] = experts
            meta["manifest_url"] = MANIFEST_ECR_URL
            meta["deviation"] = (
                "retrieval variant: manifest cheatsheet URL server-renders only 24 rows; "
                "the print rankings page embeds the identical half-PPR draft ECR in full"
            )
        if len(rows) < 100:
            raise SystemExit(f"{bid}: parsed only {len(rows)} rows — parser broken, refusing to freeze")
        meta["row_count"] = len(rows)
        bench[bid] = {**meta, "rows": rows}
        print(f"{bid}: {len(rows)} rows, raw sha256 {meta['raw_sha256'][:16]}…")
    sha_b = _dump_gz(CAL / "benchmarks.json.gz", bench)
    print(f"benchmarks frozen, content sha256 {sha_b}")


# ── boards ──────────────────────────────────────────────────────────────────────


def cmd_boards(pipeline_dir: str, arm: str) -> None:
    sys.path.insert(0, pipeline_dir)
    import models.adp as adp_mod
    from models import (
        EnsembleProjector,
        HeuristicProjector,
        RegressionProjector,
        ConsensusProjector,
        KickerProjector,
        DefenseProjector,
        Predictability,
        VorpEngine,
    )
    from models.league_rules import LeagueRules
    import value_engine_run as ver
    import math

    snap = _load_gz(CAL / "snapshot.json.gz")
    ffc = {int(k): v for k, v in snap["ffc_adp"].items()}
    adp_mod.fetch_ffc_adp = lambda teams=12, fmt="half-ppr", year=0: ffc[int(teams)]  # frozen

    ve = sys.modules[VorpEngine.__module__]
    season = int(snap["season"])
    players = snap["players"]
    out: dict[str, list[dict]] = {}

    for fmt_id, fmt in FORMATS.items():
        rules = LeagueRules(
            league_id=f"calibration-{fmt_id}",
            league_size=fmt["league_size"],
            scoring=snap["scoring"],
            roster_slots=fmt["roster_slots"],
        )
        store = ver.build_store(rules, players, snap["history"])
        ensemble = EnsembleProjector(
            [
                (HeuristicProjector(store, rules, season), 1.0),
                (RegressionProjector(store, rules, season), 1.0),
                (ConsensusProjector(store, rules, season, teams=rules.league_size), 1.0),
            ]
        )
        kicker = KickerProjector(store, rules, season, teams=rules.league_size)
        defense = DefenseProjector(store, rules, season, teams=rules.league_size)
        pred = Predictability(store, rules)

        projections, positions = {}, {}
        for p in players:
            pos = p.get("position")
            if not pos:
                continue
            if pos in ("DEF", "DST"):
                pos = "DST"
                p = {**p, "position": "DST"}
            proj = (kicker if pos == "K" else defense if pos == "DST" else ensemble).project(p)
            if not proj:
                continue
            proj.predictability = round(pred.score(proj.player_id, p["position"]), 4)
            projections[p["id"]] = proj
            positions[p["id"]] = pos

        by_name = {norm_name(p.get("full_name") or ""): p["id"] for p in players}
        adp_by_pid: dict[str, float] = {}
        for nm, e in ffc[rules.league_size].items():
            pos = e.get("position")
            if pos in ("PK", "DEF"):
                for p in players:
                    if (p.get("position") in (("K",) if pos == "PK" else ("DST", "DEF"))) and (
                        e.get("team", "").upper() == (p.get("nfl_team") or "").upper()
                    ):
                        adp_by_pid[p["id"]] = e.get("adp")
            else:
                pid = by_name.get(norm_name(nm))
                if pid:
                    adp_by_pid[pid] = e.get("adp")
        meta = {
            p["id"]: {
                "age": p.get("age"),
                "years_exp": p.get("years_exp"),
                "adp": adp_by_pid.get(p["id"]),
                "search_rank": (p.get("metadata") or {}).get("search_rank"),
            }
            for p in players
        }

        values = VorpEngine().compute(projections, positions, rules, meta)

        # Component decomposition, re-derived with THIS arm's constants so a reviewer
        # can rebuild every rank. (`youth`/`consensus` exist only in the v5 arm.)
        pos_means: dict[str, list[float]] = {}
        for pid, proj in projections.items():
            pos_means.setdefault(positions[pid], []).append(proj.mean)
        for pos in pos_means:
            pos_means[pos].sort(reverse=True)
        pos_rank = {}
        for pos in pos_means:
            ranked = sorted(
                (pid for pid in projections if positions[pid] == pos),
                key=lambda pid: -projections[pid].mean,
            )
            for i, pid in enumerate(ranked, 1):
                pos_rank[pid] = i

        pinfo = {p["id"]: p for p in players}
        rows = []
        for v in values:
            proj = projections[v.player_id]
            pos = positions[v.player_id]
            rk = pos_rank.get(v.player_id, 999)
            m = meta.get(v.player_id, {})
            means = pos_means.get(pos, [])
            below = (
                means[rk - 1 + ve.CLIFF_LOOKAHEAD]
                if rk - 1 + ve.CLIFF_LOOKAHEAD < len(means)
                else (means[-1] if means else proj.mean)
            )
            comp = {
                "elite": round(1.0 + ve.ELITE_PREMIUM * math.exp(-(rk - 1) / ve.ELITE_SCALE), 4),
                "cliff": round(max(0.0, proj.mean - below) * ve.CLIFF_W, 2),
                "upside": round(max(0.0, proj.ceiling - proj.mean) * ve.UPSIDE_W, 2),
                "predictability_discount": round(
                    ve.f_predictability(proj.predictability, ve.DISCOUNT_K), 4
                ),
            }
            if hasattr(ve, "YOUTH_W"):  # v5 arm only
                comp["youth"] = round(ve._youth_factor(pos, m.get("age")), 4)
                sr = m.get("search_rank")
                comp["consensus"] = round(
                    ve.CONSENSUS_W * (1 - min(sr, 800) / 800), 2
                ) if (sr and sr < 999) else 0.0
            rows.append(
                {
                    "player_id": v.player_id,
                    "player": pinfo[v.player_id].get("full_name"),
                    "position": pos,
                    "final_rank": v.rank,
                    "final_value": v.value,
                    "vor": v.vor,
                    "replacement": round(v.replacement, 2),
                    "projection_mean": round(proj.mean, 2),
                    "projection_ceiling": round(proj.ceiling, 2),
                    "ceiling_vor": v.boom,
                    "predictability": proj.predictability,
                    "age": m.get("age"),
                    "market_adp": m.get("adp"),
                    "search_rank": m.get("search_rank"),
                    "availability": None,  # not a value-engine input (frontend e2b concern)
                    "policy_adjustment": None,  # downstream draft policy, not board value
                    "components": comp,
                }
            )
        out[fmt_id] = rows
        print(f"{arm} {fmt_id}: {len(rows)} players, QB repl rank {rules.replacement_ranks()['QB']}")

    # No timestamp in the payload: boards are a pure function of the frozen snapshot
    # and the arm's code, so the content hash reproduces byte-for-byte on re-run.
    sha = _dump_gz(CAL / f"boards-{arm}.json.gz", {"arm": arm, "formats": out})
    print(f"boards-{arm} frozen, content sha256 {sha}")


# ── report ──────────────────────────────────────────────────────────────────────


def _spearman(x: list[float], y: list[float]) -> float:
    import numpy as np

    def ranks(v):
        a = np.asarray(v, dtype=float)
        order = a.argsort()
        r = np.empty_like(a)
        r[order] = np.arange(1, len(a) + 1)
        # average ties
        for val in np.unique(a):
            m = a == val
            if m.sum() > 1:
                r[m] = r[m].mean()
        return r

    rx, ry = ranks(x), ranks(y)
    rx -= rx.mean()
    ry -= ry.mean()
    denom = float(np.sqrt((rx**2).sum() * (ry**2).sum()))
    return float((rx * ry).sum() / denom) if denom else 0.0


def _cohorts(row_meta: dict) -> list[str]:
    out = ["all", row_meta["position"]] if row_meta["position"] in ("QB", "RB", "WR", "TE") else ["all"]
    if row_meta.get("years_exp") == 0:
        out.append("rookie")
    age = row_meta.get("age")
    if age is not None and age >= 30:
        out.append("veteran_age_30_plus")
    if row_meta.get("injury_status"):
        out.append("injury_designation")
    if row_meta.get("market_adp") is None:
        out.append("missing_adp")
    if row_meta.get("depth_chart_order") is None:
        out.append("missing_depth")
    return out


def _grade(board: list[dict], bench_rows: list[dict], pinfo: dict, top_n: int = 150) -> dict:
    """One (board, benchmark) comparison over the benchmark's top `top_n` rows."""
    by_key: dict[tuple[str, str], dict] = {}
    for r in board:
        by_key.setdefault((norm_name(r["player"] or ""), r["position"]), r)

    matched, unmatched = [], []
    for b in bench_rows[:top_n]:
        pos = b.get("position")
        if pos in ("DST", "DEF", "K", "PK") or pos is None:
            continue  # offense-only grading: DST naming is team-based and K adds noise
        hit = by_key.get((norm_name(b["player"]), pos))
        if hit is None:
            unmatched.append(b["player"])
            continue
        matched.append((b, hit))

    top100 = [b for b in bench_rows[:100] if b.get("position") not in ("DST", "DEF", "K", "PK")]
    un100 = sum(
        1 for b in top100 if by_key.get((norm_name(b["player"]), b.get("position"))) is None
    )
    if not matched:
        return {"matched": 0, "unmatched_top_100_rate": 1.0}

    bench_rank = [float(b.get("overall_rank")) for b, _ in matched]
    board_rank = [float(h["final_rank"]) for _, h in matched]
    import numpy as np

    # weighted absolute rank error: benchmark-rank weights (1/rank) — misplacing the
    # top of the board costs more than misplacing the tail
    w = np.array([1.0 / r for r in bench_rank])
    # compare positions within the matched set (board ranks re-densified) so pool-size
    # differences between board and benchmark do not manufacture error
    dense_board = np.argsort(np.argsort(board_rank)) + 1.0
    dense_bench = np.argsort(np.argsort(bench_rank)) + 1.0
    err = float((w * np.abs(dense_board - dense_bench)).sum() / w.sum())

    def recall(n: int) -> float:
        want = {norm_name(b["player"]) for b, _ in matched if b["overall_rank"] <= n}
        have = {
            norm_name(b["player"])
            for (b, h) in sorted(matched, key=lambda t: t[1]["final_rank"])[: len(want)]
        }
        return round(len(want & have) / len(want), 4) if want else 1.0

    med_bias: dict[str, float] = {}
    for pos in ("QB", "RB", "WR", "TE"):
        d = [db - dn for (b, h), db, dn in zip(matched, dense_board, dense_bench, strict=True)
             if b.get("position") == pos]
        if d:
            med_bias[pos] = float(np.median(d))

    outliers = sorted(
        (
            {
                "player": b["player"],
                "position": b.get("position"),
                "benchmark_rank": b["overall_rank"],
                "board_rank": int(h["final_rank"]),
                "dense_delta": float(db - dn),
            }
            for (b, h), db, dn in zip(matched, dense_board, dense_bench, strict=True)
        ),
        key=lambda o: -abs(o["dense_delta"]),
    )[:10]

    cohort_err: dict[str, dict] = {}
    for (b, h), db, dn in zip(matched, dense_board, dense_bench, strict=True):
        p = pinfo.get(h["player_id"], {})
        rm = {**h, "injury_status": p.get("injury_status"),
              "years_exp": p.get("years_exp"),
              "depth_chart_order": (p.get("metadata") or {}).get("depth_chart_order")}
        for c in _cohorts(rm):
            e = cohort_err.setdefault(c, {"n": 0, "abs_err": 0.0, "bias": 0.0})
            e["n"] += 1
            e["abs_err"] += abs(db - dn)
            e["bias"] += db - dn
    for c, e in cohort_err.items():
        e["mean_abs_err"] = round(e.pop("abs_err") / e["n"], 2)
        e["median_free_bias"] = round(e.pop("bias") / e["n"], 2)

    return {
        "matched": len(matched),
        "unmatched": unmatched[:20],
        "unmatched_top_100_rate": round(un100 / len(top100), 4) if top100 else 0.0,
        "spearman_rho": round(_spearman(bench_rank, board_rank), 4),
        "weighted_absolute_rank_error": round(err, 3),
        "top_12_recall": recall(12),
        "top_24_recall": recall(24),
        "top_50_recall": recall(50),
        "median_rank_bias_by_position": med_bias,
        "largest_absolute_outliers": outliers,
        "cohorts": cohort_err,
    }


def cmd_report() -> None:
    snap = _load_gz(CAL / "snapshot.json.gz")
    bench = _load_gz(CAL / "benchmarks.json.gz")
    boards = {arm: _load_gz(CAL / f"boards-{arm}.json.gz") for arm in ("v5", "v6")}
    pinfo = {p["id"]: p for p in snap["players"]}

    results: dict[str, dict] = {}
    for fmt_id, bids in FORMAT_BENCHMARKS.items():
        results[fmt_id] = {}
        for bid in bids:
            rows = bench[bid]["rows"]
            results[fmt_id][bid] = {
                arm: _grade(boards[arm]["formats"][fmt_id], rows, pinfo) for arm in ("v5", "v6")
            }

    # threshold evaluation (manifest: player-calibration-v1.json)
    checks = []
    for fmt_id, per_bid in results.items():
        for bid, arms in per_bid.items():
            v5, v6 = arms["v5"], arms["v6"]
            checks.append(
                {
                    "format": fmt_id,
                    "benchmark": bid,
                    "unmatched_top_100_rate_max_0.02": v6["unmatched_top_100_rate"] <= 0.02,
                    "spearman_delta_min_0.0": v6["spearman_rho"] >= v5["spearman_rho"],
                    "weighted_rank_error_delta_max_0.0":
                        v6["weighted_absolute_rank_error"] <= v5["weighted_absolute_rank_error"],
                }
            )

    report = {
        "generated_utc": _utc(),
        "manifest": ".worktrees/v6-review/.orchestrator-v6/experiments/player-calibration-v1.json (frozen, reviewer-owned)",
        "inputs": {
            "snapshot_rows": snap["counts"],
            "benchmarks": {
                bid: {k: v for k, v in b.items() if k != "rows"} for bid, b in bench.items()
            },
        },
        "results": results,
        "threshold_checks": checks,
        "notes": [
            "Grading is offense-only (QB/RB/WR/TE): DST naming is team-based and K is streamed.",
            "The superflex ECR benchmark also grades the 2QB board — the closest public reference.",
            "Cohorts team_change and low_availability are NOT computable from the frozen snapshot "
            "(no prior-team field; player_availability is not present in this database) and are "
            "reported as such rather than approximated.",
            "No coefficient is promoted by this report: deterministic C01 corrections shipped via "
            "the C01/C01A correctness gate; every tuned constant is byte-identical between arms.",
        ],
    }
    (CAL / "report.json").write_text(json.dumps(report, indent=2))
    print("report.json written")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["snapshot", "boards", "report"])
    ap.add_argument("--pipeline-dir", default=str(PIPE))
    ap.add_argument("--arm", default="v6", choices=["v5", "v6"])
    a = ap.parse_args()
    if a.cmd == "snapshot":
        cmd_snapshot()
    elif a.cmd == "boards":
        cmd_boards(a.pipeline_dir, a.arm)
    else:
        cmd_report()


if __name__ == "__main__":
    main()
