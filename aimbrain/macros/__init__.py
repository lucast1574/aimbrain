"""
Macro registry — collects all macros from submodules into a single dict.

Each macro is a callable: fn(params: dict) -> None
"""

from aimbrain.macros import combat, building, movement, looting, utility

# ─── Registry ─────────────────────────────────────────────────────────
# Each submodule defines a MACROS dict. We merge them here.

MACROS: dict[str, callable] = {}
MACROS.update(combat.MACROS)
MACROS.update(building.MACROS)
MACROS.update(movement.MACROS)
MACROS.update(looting.MACROS)
MACROS.update(utility.MACROS)


def list_macros() -> list[str]:
    """Return sorted list of all macro names."""
    return sorted(MACROS.keys())


def run(name: str, params: dict | None = None):
    """Execute a macro by name. Raises KeyError if unknown."""
    if name not in MACROS:
        raise KeyError(f"Unknown macro: {name}. Available: {list_macros()}")
    MACROS[name](params or {})


def exists(name: str) -> bool:
    return name in MACROS
