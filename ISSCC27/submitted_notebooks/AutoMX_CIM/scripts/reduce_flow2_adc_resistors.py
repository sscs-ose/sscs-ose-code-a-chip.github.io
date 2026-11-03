"""Exact elimination of unobserved passive resistor nodes in the pinned ADC.

Only positive, constant numeric resistors participate. Every node touched by
a capacitor, MOS, modeled resistor or top port is retained. Degree <= 3
star/mesh (Kron) elimination changes neither currents nor voltages at those
retained nodes in exact arithmetic. All nonnumeric-R cards remain bytewise
identical. Internal resistor names and eliminated-node probes are not kept.
"""
from __future__ import annotations

from collections import Counter, deque
from hashlib import sha256
import math
from pathlib import Path
import re

NUMBER = re.compile(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([A-Za-z]*)\Z")
SCALE = {"": 1., "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6,
         "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, "t": 1e12}


def number(value):
    match = NUMBER.fullmatch(value)
    if not match or match[2].lower() not in SCALE:
        return None
    value = float(match[1]) * SCALE[match[2].lower()]
    return value if math.isfinite(value) else None


def reduce_text(text: str, *, max_degree=3) -> tuple[str, dict]:
    if max_degree not in (1, 2, 3):
        raise ValueError("bounded exact elimination supports degree 1..3")
    # The pinned postlayout view has a continued header, but no continued
    # element cards. Fail explicitly if that changes; never guess its nodes.
    cards, card = [], []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("+"):
            if not card:
                raise ValueError("orphan SPICE continuation")
            card.append(line)
        else:
            if card:
                cards.append("".join(card))
            card = [line]
    if card:
        cards.append("".join(card))
    graph, anchors, candidates, preserved = {}, {"0"}, {}, []
    counts = Counter()

    def add(a, b, conductance):
        if a == b:
            return
        graph.setdefault(a, {})[b] = graph.get(a, {}).get(b, 0.) + conductance
        graph.setdefault(b, {})[a] = graph.get(b, {}).get(a, 0.) + conductance

    for index, raw in enumerate(cards):
        logical = re.sub(r"\r?\n\s*\+", " ", raw)
        fields = logical.split()
        if not fields or fields[0].startswith("*"):
            preserved.append(raw)
            continue
        head = fields[0].lower()
        if head == ".subckt":
            counts["subcircuits"] += 1
            anchors.update(fields[2:])
        elif head.startswith("."):
            if head not in (".ends", ".end"):
                raise ValueError(f"unexpected ADC directive: {head}")
        elif "\n+" in raw.replace("\r\n", "\n"):
            raise ValueError("continued element cards need explicit node parsing")
        elif head.startswith("r"):
            if len(fields) < 4:
                raise ValueError("malformed resistor")
            value = number(fields[3]) if len(fields) == 4 else None
            if value is not None and value > 0:
                if not math.isfinite(1/value):
                    raise ValueError("resistor conductance outside numeric range")
                candidates[index] = (fields[1], fields[2], value)
                add(fields[1], fields[2], 1/value)
                counts["numeric_resistors"] += 1
                continue
            anchors.update(fields[1:3])
            counts["preserved_resistors"] += 1
        elif head.startswith("c"):
            if len(fields) != 4:
                raise ValueError("unexpected capacitor card")
            anchors.update(fields[1:3])
            counts["capacitors"] += 1
        elif head.startswith("x"):
            primitive = next((i for i, part in enumerate(fields) if part.startswith("sky130_fd_pr__")), None)
            if primitive not in (3, 5):
                raise ValueError("only the pinned 2-terminal MIM/4-terminal MOS cards are supported")
            if ((primitive == 3 and fields[primitive] != "sky130_fd_pr__cap_mim_m3_1") or
                    (primitive == 5 and not fields[primitive].startswith(("sky130_fd_pr__nfet_", "sky130_fd_pr__pfet_")))):
                raise ValueError("unsupported ADC primitive")
            anchors.update(fields[1:primitive])
            counts["mim" if primitive == 3 else "mos"] += 1
        else:
            raise ValueError(f"unexpected ADC element: {fields[0]}")
        preserved.append(raw)
    if counts["subcircuits"] != 1:
        raise ValueError("one flat ADC subcircuit required")
    # No nonlinear/dynamic terminal, external port or test gate can enter
    # this queue. Degree-three elimination never increases the edge count.
    pending = deque(n for n, adj in graph.items() if n not in anchors and len(adj) <= max_degree)
    removed = Counter()
    original_nodes = len(graph)
    original_protected = set(graph).intersection(anchors)
    maximum_local_roundoff = 0.
    while pending:
        node = pending.popleft()
        if node in anchors or node not in graph or len(graph[node]) > max_degree:
            continue
        adjacent = list(graph.pop(node).items())
        removed[len(adjacent)] += 1
        total = math.fsum(g for _, g in adjacent)
        if adjacent and (total <= 0 or not math.isfinite(total)):
            raise ValueError("invalid passive star conductance")
        for other, _ in adjacent:
            del graph[other][node]
        for index, (a, ga) in enumerate(adjacent):
            for b, gb in adjacent[index+1:]:
                # This order avoids overflow in the product ga*gb.
                new = (ga / total) * gb
                if not math.isfinite(new) or new <= 0:
                    raise ValueError("passive reduction underflow/overflow")
                maximum_local_roundoff = max(maximum_local_roundoff, abs(new / gb * total / ga - 1.))
                add(a, b, new)
        for other, _ in adjacent:
            if other not in anchors and len(graph[other]) <= max_degree:
                pending.append(other)
    edges = [(a, b, 1/g) for a in sorted(graph) for b, g in sorted(graph[a].items()) if a < b]
    if original_protected - set(graph):
        raise ValueError("a protected active/dynamic/port node was removed")
    if any(not math.isfinite(r) or r <= 0 for _, _, r in edges):
        raise ValueError("invalid equivalent resistor")
    if any(re.search(r"(?im)^RAUTOMX_KRON_", raw) for raw in preserved):
        raise ValueError("resistor name prefix already exists")
    replacement = "* Exact passive resistor-node elimination; all active/dynamic terminals retained.\n"
    replacement += "".join(f"RAUTOMX_KRON_{i} {a} {b} {r:.17g}\n" for i, (a, b, r) in enumerate(edges))
    output, inserted = [], False
    for index, raw in enumerate(cards):
        if index in candidates:
            if not inserted:
                output.append(replacement)
                inserted = True
        else:
            output.append(raw)
    if not inserted:
        raise ValueError("no numeric resistors to reduce")
    result = "".join(output)
    # This independent output-card scan checks preservation of every original
    # noncandidate card, including the eight modeled poly resistors.
    preserved_output = [raw for raw in output if raw != replacement]
    if preserved_output != preserved:
        raise ValueError("nonresistor card preservation failed")
    fingerprint = sha256("".join(preserved).encode()).hexdigest()
    report = {"algorithm": f"EXACT_PASSIVE_KRON_MAX_DEGREE_{max_degree}", "max_degree": max_degree,
              "original_counts": dict(counts), "equivalent_numeric_resistors": len(edges),
              "original_resistor_nodes": original_nodes, "retained_resistor_nodes": len(graph),
              "eliminated_nodes_by_degree": {str(k): v for k, v in sorted(removed.items())},
              "protected_nodes": len(anchors), "protected_node_removed": False,
              "all_non_numeric_R_cards_preserved": True, "preserved_cards_sha256": fingerprint,
              "maximum_local_relative_roundoff": maximum_local_roundoff,
              "source_sha256": sha256(text.encode()).hexdigest(),
              "equivalent_sha256": sha256(result.encode()).hexdigest(),
              "scope": "passive-node Schur complement only; all MOS/MIM/C, modeled R and top ports unchanged; no ADC conversion/PDK signoff claim"}
    return result, report
