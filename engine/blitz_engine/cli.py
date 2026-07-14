"""`blitz-engine` CLI — the four verbs of the local quant engine.

    blitz-engine fit      # fit the Bayesian projection model (E1) -> posterior draws
    blitz-engine sim      # Monte-Carlo season/league simulation (E3)
    blitz-engine draft     # value / equity / MCTS draft strategy (E4)
    blitz-engine publish   # write a versioned snapshot + compact export

E0-scaffold ships these as STUBS that wire together the foundation (config + store +
registry) and run end-to-end on a smoke path. Each unit fills in the real logic for its
verb without touching this dispatch layer. `ponytail:` argparse only — no CLI framework.
"""
from __future__ import annotations

import argparse
from collections.abc import Sequence

from blitz_engine.config import EngineConfig, load_config
from blitz_engine.registry import ModelRegistry
from blitz_engine.store import ParquetStore

_VERBS = ("fit", "sim", "draft", "publish")


def _wire(args: argparse.Namespace) -> tuple[EngineConfig, ParquetStore, ModelRegistry]:
    """Resolve config + open the store + registry the same way for every verb."""
    cfg = load_config(
        **{k: v for k, v in {
            "data_root": args.data_root,
            "seed": args.seed,
            "cloud_burst": args.cloud_burst,
        }.items() if v is not None}
    )
    store = ParquetStore.open(cfg.data_root, cfg)
    registry = ModelRegistry(cfg.data_root)
    return cfg, store, registry


def _cmd_fit(args: argparse.Namespace) -> int:
    cfg, store, registry = _wire(args)
    print(f"[fit] stub — would fit projection model: n_draws={cfg.n_draws} "
          f"dtype={cfg.dtype} device={cfg.device} store={store.root}")
    print("[fit] real Bayesian core lands in E1-core.")
    return 0


def _cmd_sim(args: argparse.Namespace) -> int:
    cfg, store, _ = _wire(args)
    print(f"[sim] stub — would run MC sim: mc_batch={cfg.mc_batch} "
          f"chunked (chunk_size={cfg.chunk_size}) store={store.root}")
    print("[sim] real Monte-Carlo simulation lands in E3.")
    return 0


def _cmd_draft(args: argparse.Namespace) -> int:
    cfg, _, _ = _wire(args)
    print(f"[draft] stub — would compute value/equity/MCTS (seed={cfg.seed}, "
          f"cloud_burst={cfg.cloud_burst}).")
    print("[draft] real value engine lands in E4.")
    return 0


def _cmd_publish(args: argparse.Namespace) -> int:
    cfg, _, _ = _wire(args)
    print(f"[publish] stub — would write versioned snapshot + compact export "
          f"under {cfg.data_root}.")
    print("[publish] real snapshot publish wires into pipeline/publish_snapshot.py.")
    return 0


_HANDLERS = {
    "fit": _cmd_fit,
    "sim": _cmd_sim,
    "draft": _cmd_draft,
    "publish": _cmd_publish,
}


def build_parser() -> argparse.ArgumentParser:
    """The full argparse tree — one subparser per verb, shared global options."""
    parser = argparse.ArgumentParser(
        prog="blitz-engine",
        description="BlitzBoard local quant engine — fit | sim | draft | publish.",
    )
    sub = parser.add_subparsers(dest="verb", required=True)
    for verb in _VERBS:
        p = sub.add_parser(verb, help=_HANDLERS[verb].__doc__ or f"{verb} (stub)")
        p.add_argument("--data-root", default=None,
                       help="Override the local store/snapshot/registry root.")
        p.add_argument("--seed", type=int, default=None, help="Override the RNG seed.")
        p.add_argument("--cloud-burst", action="store_true", default=None,
                       help="Opt in to external heavy compute (never the default).")
        p.set_defaults(func=_HANDLERS[verb])
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint for the `blitz-engine` console script. Returns a process exit code."""
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
