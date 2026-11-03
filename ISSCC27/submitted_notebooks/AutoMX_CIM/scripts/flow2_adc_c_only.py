"""Explicit C-only approximation of the flat ADC, never a replacement PEX.

Contract extracted numeric wire resistors. Keep every MOS/MIM, every
modeled resistor and distinct formal ports. Residual numeric resistors
between protected ports are retained, avoiding ideal voltage-source loops.
Device parameters and functional delay resistors are unchanged.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

from scripts.reduce_flow2_adc_resistors import number

ALGORITHM = "C_ONLY_WIRE_CONTRACTION_PORT_PROTECTED_V1"


def cards(text):
    result = []
    for line in text.splitlines():
        if line.lstrip().startswith("+"):
            if not result:
                raise ValueError("orphan continuation")
            result[-1] += " " + line.lstrip()[1:].strip()
        else:
            result.append(line)
    return result


def reduce_text(text):
    rows = cards(text)
    ports, elements, directives = [], [], []
    for row in rows:
        f = row.split()
        if not f or f[0].startswith("*"):
            continue
        head = f[0].lower()
        if head == ".subckt":
            if ports:
                raise ValueError("one flat ADC subcircuit required")
            ports = f[2:]
            directives.append(f)
        elif head in (".ends", ".end"):
            continue
        elif head.startswith("."):
            raise ValueError("unsupported directive: " + head)
        elif head[0] in "rc" and len(f) >= 4:
            elements.append((f, 2))
        elif head[0] in "xm":
            index = next((i for i, v in enumerate(f) if v.startswith("sky130_fd_pr__")), None)
            if index not in (3, 5):
                raise ValueError("explicit MIM/MOS model required: " + f[0])
            elements.append((f, index - 1))
        else:
            raise ValueError("unsupported element: " + f[0])
    if not ports or len(ports) != len(set(ports)):
        raise ValueError("unique formal ports required")
    parent, protected = {}, {}

    def find(n):
        parent.setdefault(n, n)
        root = n
        while parent[root] != root:
            root = parent[root]
        while parent[n] != n:
            following = parent[n]
            parent[n] = root
            n = following
        return root

    for n in ["0", *ports]:
        protected[find(n)] = n
    # A functional resistor must never be removed through a wire shortcut.
    for f, _ in elements:
        if f[0][0].lower() == "r" and not (len(f) == 4 and number(f[3]) is not None):
            for n in f[1:3]:
                protected.setdefault(find(n), n)
    candidates = []
    for f, _ in elements:
        if f[0][0].lower() != "r" or len(f) != 4:
            continue
        value = number(f[3])
        if value is None:
            continue
        if value < 0:
            raise ValueError("negative wire resistance")
        candidates.append(f)
        a, b = find(f[1]), find(f[2])
        if a == b or (a in protected and b in protected):
            continue
        if b in protected:
            a, b = b, a
        parent[b] = a
        if b in protected:
            protected[a] = protected.pop(b)
    # Prefer formal/protected names, so parent-level probe aliases stay valid.
    aliases = {n: protected.get(find(n), find(n)) for n in list(parent)}
    counts, before, after = Counter(), Counter(), Counter()
    output = ["* Derived C-only approximation; NOT full distributed RC evidence.",
              " ".join(directives[0])]
    parameter_proofs = []
    for f, nn in elements:
        kind = f[0][0].lower()
        before[kind] += 1
        mapped = [aliases.get(n, n) for n in f[1:nn+1]]
        numeric_r = kind == "r" and len(f) == 4 and number(f[3]) is not None
        if numeric_r and mapped[0] == mapped[1]:
            counts["contracted_wire_resistors"] += 1
            continue
        if kind == "c" and mapped[0] == mapped[1]:
            counts["zero_differential_parasitic_capacitors_removed"] += 1
            continue
        changed = [f[0], *mapped, *f[nn+1:]]
        output.append(" ".join(changed))
        after[kind] += 1
        if not numeric_r and kind != "c":
            parameter_proofs.append([f[0], f[nn+1:]])
    output += [".ends " + directives[0][1], ""]
    if after["x"] != before["x"] or after["m"] != before["m"]:
        raise AssertionError("a physical device was lost")
    result = "\n".join(output)
    return result, {"algorithm": ALGORITHM, "scope": "functional transistor C-only prototype, not RC signoff",
        "source_sha256": sha256(text.encode()).hexdigest(), "derived_sha256": sha256(result.encode()).hexdigest(),
        "formal_ports": ports, "before": dict(before), "after": dict(after), **dict(counts),
        "functional_device_parameters_sha256": sha256(json.dumps(parameter_proofs).encode()).hexdigest(),
        "preserved_modeled_resistors": sum(f[0][0].lower() == "r" and not
            (len(f) == 4 and number(f[3]) is not None) for f, _ in elements),
        "node_aliases": aliases}


def prepare(source, target):
    source, target = Path(source), Path(target)
    text, proof = reduce_text(source.read_text(encoding="utf-8"))
    if target.exists() and target.read_text(encoding="utf-8") != text:
        raise FileExistsError("C-only inputs changed; use a new tag")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(text, encoding="utf-8")
    proof["source_file_sha256"] = sha256(source.read_bytes()).hexdigest()
    proof["derived_file_sha256"] = sha256(target.read_bytes()).hexdigest()
    return proof
