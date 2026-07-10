"""
Auto-discovery of Factor subclasses under ``pipeline/models/factors/``.

``discover_factors()`` globs every module in this package (skipping ``base``,
``loader`` and private ``_*`` modules), imports it, and instantiates each concrete
``Factor`` subclass exactly once. A downstream unit (E1/E2/E3/E5) adds a factor by
dropping ONE new file here — no registry to edit, no ``projector.py`` change.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from functools import lru_cache

from .base import Factor

_SKIP = {"base", "loader"}


def _iter_factor_classes():
    pkg = importlib.import_module(__package__)
    seen: set[str] = set()
    for info in pkgutil.iter_modules(pkg.__path__):
        name = info.name
        if name in _SKIP or name.startswith("_"):
            continue
        mod = importlib.import_module(f"{__package__}.{name}")
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            # only classes DEFINED in this module (skip re-imported base/others)
            if (issubclass(obj, Factor) and obj is not Factor
                    and obj.__module__ == mod.__name__):
                key = f"{obj.__module__}.{obj.__qualname__}"
                if key not in seen:
                    seen.add(key)
                    yield obj


def discover_factors(*, include_disabled: bool = False) -> list[Factor]:
    """One instance per concrete Factor subclass, sorted by name (deterministic,
    idempotent). Disabled factors are omitted unless ``include_disabled``."""
    out = [cls() for cls in _iter_factor_classes()]
    if not include_disabled:
        out = [f for f in out if f.enabled]
    out.sort(key=lambda f: f.name)
    return out


@lru_cache(maxsize=1)
def default_factors() -> tuple[Factor, ...]:
    """Cached discovery for a pipeline run (call ``default_factors.cache_clear()``
    after adding a factor at runtime; tests use ``discover_factors()`` directly)."""
    return tuple(discover_factors())
