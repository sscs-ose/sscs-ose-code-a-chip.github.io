from __future__ import annotations

def _b(v):
    if v not in (0, 1):
        raise ValueError(f"Binary logic only in Phase A0; got {v}")
    return int(v)

from functools import lru_cache


@lru_cache(maxsize=None)
def _lib_tokens(expr):
    from .liberty import _tokens
    return tuple(_tokens(expr))


def eval_primitive(kind: str, pins: dict[str, int]) -> int:
    if kind.startswith("LIB:"):
        # generic Liberty cell: kind = "LIB:<boolean function of the output pin>"
        from .liberty import _BoolParser
        return _BoolParser(list(_lib_tokens(kind[4:])), {n: _b(v) for n, v in pins.items()}).parse()
    k = kind.upper()
    p = {name: _b(v) for name, v in pins.items()}
    if k == "BUF": return p["A"]
    if k == "INV": return 1 - p["A"]
    if k == "AND2": return p["A"] & p["B"]
    if k == "OR2": return p["A"] | p["B"]
    if k == "NAND2": return 1 - (p["A"] & p["B"])
    if k == "NOR2": return 1 - (p["A"] | p["B"])
    if k == "XOR2": return p["A"] ^ p["B"]
    if k == "XNOR2": return 1 - (p["A"] ^ p["B"])
    if k == "MUX2": return p["A"] if p["S"] == 0 else p["B"]
    if k == "A21OI": return 1 - ((p["A1"] & p["A2"]) | p["B1"])
    if k == "O21AI": return 1 - ((p["A1"] | p["A2"]) & p["B1"])
    raise ValueError(f"Unsupported primitive: {kind}")

SUPPORTED_KINDS = frozenset({"BUF", "INV", "AND2", "OR2", "NAND2", "NOR2", "XOR2",
                             "XNOR2", "MUX2", "A21OI", "O21AI"})
