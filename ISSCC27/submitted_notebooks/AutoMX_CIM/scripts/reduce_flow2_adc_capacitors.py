"""Eliminate unobserved, capacitor-only metal nodes at zero free charge.

For a floating conductor with no DC/active connection, Q=0 gives
Vf=sum(Cfi*Vi)/sum(Cfi). Substitution adds Cij=Cfi*Cfj/sum(Cfi).
This preserves boundary charge/current and electrostatic energy. No leakage
resistor, MOS, MIM, modeled resistor or terminal is removed/idealized.
Nonzero trapped free charge and observed floating nodes are outside scope.
"""
from __future__ import annotations

from collections import Counter, deque
from hashlib import sha256
import math
import random
import re

from scripts.reduce_flow2_adc_resistors import number


def capacitance(token):
    return number(re.sub(r"(?i)(meg|[fpnumkgt])f$", r"\1", token))


def reduce_text(text, *, protected=(), maximum_degree=128):
    if not 2 <= maximum_degree <= 128:
        raise ValueError("bounded capacitor elimination requires degree 2..128")
    cards, card = [], []
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith("+"):
            if not card:
                raise ValueError("orphan continuation")
            card.append(line)
        else:
            if card:
                cards.append("".join(card))
            card = [line]
    if card:
        cards.append("".join(card))
    graph, anchors = {}, {"0", *protected}
    caps, indices, preserved = [], set(), []
    counts = Counter()

    def add(a, b, c):
        if a == b:
            return
        graph.setdefault(a, {})[b] = graph.get(a, {}).get(b, 0.)+c
        graph.setdefault(b, {})[a] = graph.get(b, {}).get(a, 0.)+c

    for index, raw in enumerate(cards):
        f = re.sub(r"\r?\n\s*\+", " ", raw).split()
        if not f or f[0].startswith("*"):
            preserved.append(raw)
            continue
        kind = f[0].lower()
        if kind == ".subckt":
            counts["subcircuits"] += 1
            anchors.update(f[2:])
        elif kind in (".ends", ".end"):
            pass
        elif kind.startswith("."):
            raise ValueError(f"unsupported ADC directive/initial charge: {kind}")
        elif len(raw.splitlines()) != 1:
            raise ValueError("continued device card needs explicit parsing")
        elif kind.startswith("r"):
            if len(f) < 4:
                raise ValueError("malformed resistor")
            anchors.update(f[1:3])
            counts["resistors"] += 1
        elif kind.startswith("x"):
            primitive = next((i for i, value in enumerate(f) if value.startswith("sky130_fd_pr__")), None)
            if (primitive not in (3, 5) or (primitive == 3 and f[primitive] != "sky130_fd_pr__cap_mim_m3_1")
                    or (primitive == 5 and not f[primitive].startswith(("sky130_fd_pr__nfet_", "sky130_fd_pr__pfet_")))):
                raise ValueError("unsupported ADC primitive")
            anchors.update(f[1:primitive])
            counts["mim" if primitive == 3 else "mos"] += 1
        elif kind.startswith("c"):
            value = capacitance(f[3]) if len(f) == 4 else None
            if value is None or value <= 0:
                raise ValueError("only positive constant capacitors without IC are supported")
            if kind.startswith("cautomx_float_"):
                raise ValueError("capacitor reduction was already applied")
            caps.append((f[1], f[2], value))
            indices.add(index)
            counts["capacitors"] += 1
            add(f[1], f[2], value)
            continue
        else:
            raise ValueError(f"unsupported ADC card: {f[0]}")
        preserved.append(raw)
    if counts["subcircuits"] != 1 or not caps:
        raise ValueError("one flat ADC subcircuit and a capacitor network are required")
    floating = set(graph)-anchors
    pending = deque(sorted(n for n in floating if len(graph[n]) <= maximum_degree))
    trace = []
    while pending:
        node = pending.popleft()
        if node in anchors or node not in graph or len(graph[node]) > maximum_degree:
            continue
        adjacent = sorted(graph.pop(node).items())
        total = math.fsum(c for _, c in adjacent)
        if not adjacent:
            # An entirely isolated C component has no boundary current.
            # Its common potential is arbitrary; choose zero to reconstruct
            # the zero-free-charge validation, without adding a DC shunt.
            trace.append((node, adjacent, 0.))
            continue
        if not math.isfinite(total) or total <= 0:
            raise ValueError("invalid floating capacitor star")
        trace.append((node, adjacent, total))
        for other, _ in adjacent:
            del graph[other][node]
        for i, (a, ca) in enumerate(adjacent):
            for b, cb in adjacent[i+1:]:
                value = ca/total*cb
                if not math.isfinite(value) or value <= 0:
                    raise ValueError("capacitor elimination underflow/overflow")
                add(a, b, value)
        for other, _ in adjacent:
            if other not in anchors and len(graph[other]) <= maximum_degree:
                pending.append(other)
    remaining = sorted(set(graph)-anchors)
    if remaining:
        raise ValueError(f"floating capacitor nodes exceed bounded elimination: {remaining[:8]}")
    edges = [(a, b, c) for a in sorted(graph) for b, c in sorted(graph[a].items()) if a < b]
    if not trace:
        return text, {"algorithm": "CAPACITOR_ONLY_ZERO_FREE_CHARGE_KRON", "eliminated_nodes": 0,
                      "source_sha256": sha256(text.encode()).hexdigest(),
                      "equivalent_sha256": sha256(text.encode()).hexdigest(), "original_counts": dict(counts)}
    # Independent boundary-charge/energy check: reconstruct internal voltages
    # backwards, then evaluate the ORIGINAL edges rather than another reduction.
    trials = []
    rng = random.Random(20261018)
    boundary = sorted(set(graph))
    for _ in range(3):
        voltage = {n: (0. if n == "0" else rng.uniform(-.2, 1.8)) for n in boundary}
        for node, adjacent, total in reversed(trace):
            voltage[node] = math.fsum(c*voltage[n] for n, c in adjacent)/total if total else 0.
        original_q = Counter()
        reduced_q = Counter()
        for a, b, c in caps:
            voltage.setdefault(a, 0.)  # includes electrically null self-C
            voltage.setdefault(b, 0.)
            q = c*(voltage[a]-voltage[b])
            original_q[a] += q
            original_q[b] -= q
        for a, b, c in edges:
            q = c*(voltage[a]-voltage[b])
            reduced_q[a] += q
            reduced_q[b] -= q
        scale = max(1e-30, max(map(abs, original_q.values())))
        charge_error = max((abs(original_q[n]-reduced_q[n]) for n in boundary), default=0.)/scale
        floating_error = max(abs(original_q[n]) for n in floating)/scale
        e0 = math.fsum(.5*c*(voltage[a]-voltage[b])**2 for a, b, c in caps)
        e1 = math.fsum(.5*c*(voltage[a]-voltage[b])**2 for a, b, c in edges)
        energy_error = abs(e0-e1)/max(1e-30, abs(e0))
        if max(charge_error, floating_error, energy_error) > 1e-10:
            raise ValueError("independent charge/energy equivalence check failed")
        trials.append({"boundary_charge_relative_error": charge_error,
                       "floating_charge_relative_error": floating_error, "energy_relative_error": energy_error})
    replacement = "* Capacitor-only floating metal elimination; zero initial free charge.\n"
    replacement += "".join(f"CAUTOMX_FLOAT_{i} {a} {b} {c:.17g}\n" for i, (a, b, c) in enumerate(edges))
    output, inserted = [], False
    for i, raw in enumerate(cards):
        if i in indices:
            if not inserted:
                output.append(replacement)
                inserted = True
        else:
            output.append(raw)
    if [raw for raw in output if raw != replacement] != preserved:
        raise ValueError("active/R/MIM/header card preservation failed")
    result = "".join(output)
    return result, {"algorithm": "CAPACITOR_ONLY_ZERO_FREE_CHARGE_KRON", "maximum_degree": maximum_degree,
        "source_sha256": sha256(text.encode()).hexdigest(), "equivalent_sha256": sha256(result.encode()).hexdigest(),
        "original_counts": dict(counts), "equivalent_capacitors": len(edges), "eliminated_nodes": len(trace),
        "eliminated_node_names": [n for n, _, _ in trace], "remaining_capacitor_only_nodes": [],
        "preserved_non_C_cards_sha256": sha256("".join(preserved).encode()).hexdigest(),
        "independent_charge_energy_checks": trials,
        "assumption": "unobserved linear capacitor-only conductors have zero initial free charge; no IC cards",
        "not_signoff": "derived simulation network, not new PEX; no nonlinear device, modeled R, MIM, port or observed node is replaced"}
