"""Retiming certificate: a structural proof that a rewritten netlist is a legal Leiserson-Saxe retiming of the original.

Checks, without simulation:
  1. the combinational logic is identical: same cells (name and library cell) and the same driver of every input pin,
     once flip-flops are looked through;
  2. the number of flip-flops on every connection, w'(e), is explained by one integer lag per gate:
     w'(u->v) = w(u->v) + r(v) - r(u), with r = 0 at the inputs and r = latency at the outputs.

By Leiserson & Saxe (1991) such a circuit has the original's input/output behaviour (shifted by the latency) once
both start from corresponding states; it scales to any size, unlike SAT-based sequential equivalence
(scripts/formal_equivalence.py), which is tried as well.

    python scripts/retiming_certificate.py <liberty> <original.v> <candidate.v> [latency]
"""
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from glitchscope.liberty import parse_liberty_file  # noqa: E402
from glitchscope.retime import build_rgraph  # noqa: E402
from glitchscope.verilog import read_design  # noqa: E402


def keyed(g):
    """{(u, v, pin): w} with nodes named: cells by instance, sources by net, sinks by (kind, name)."""
    C, S = len(g.cells), len(g.sources)

    def name(i):
        if i < C:
            return ("cell", g.cells[i].name, g.cells[i].library_cell)
        if i < C + S:
            return ("in", g.sources[i - C])
        k, n = g.sinks[i - C - S]
        if k == "ffd":                                   # data input of a fixed flop: identify by its D net's sink
            return ("ffd", n)
        return (k, n)
    return {(name(u), name(v), pin): w for u, v, pin, w in g.edges}


def certify(lib, orig, cand, latency=0):
    L = parse_liberty_file(lib)
    go, gc = build_rgraph(read_design(orig, L)), build_rgraph(read_design(cand, L))
    eo, ec = keyed(go), keyed(gc)
    if set(eo) != set(ec):
        miss, extra = set(eo) - set(ec), set(ec) - set(eo)
        return False, f"logic differs: {len(miss)} connections missing, {len(extra)} new (e.g. {sorted(miss | extra)[:2]})"
    adj = defaultdict(list)
    for (u, v, pin), w in eo.items():
        d = ec[(u, v, pin)] - w                          # = r(v) - r(u)
        adj[u].append((v, d)); adj[v].append((u, -d))
    r = {}
    for n in adj:                                        # anchors: inputs 0, outputs = latency
        if n[0] == "in":
            r[n] = 0
        elif n[0] in ("po", "ffd", "ffc"):
            r[n] = latency
    q = deque(r)
    while q:
        u = q.popleft()
        for v, d in adj[u]:
            if v not in r:
                r[v] = r[u] + d; q.append(v)
            elif r[v] != r[u] + d:
                return False, f"no consistent lag at {v[1]} (register counts are not a retiming)"
    unreached = [n for n in adj if n not in r]
    if unreached:                                        # logic not connected to any I/O: free lag, check internally
        r0 = unreached[0]; r[r0] = 0; q = deque([r0])
        while q:
            u = q.popleft()
            for v, d in adj[u]:
                if v not in r:
                    r[v] = r[u] + d; q.append(v)
                elif r[v] != r[u] + d:
                    return False, f"no consistent lag at {v[1]}"
    if any(w < 0 for w in ec.values()):
        return False, "negative register count"
    lags = [x for n, x in r.items() if n[0] == "cell"]
    n_ff_o = sum(len(g.movable) + len(g.fixed) for g in (go,))
    n_ff_c = sum(len(g.movable) + len(g.fixed) for g in (gc,))
    return True, (f"legal retiming: {len(eo)} connections, {len(lags)} gates, lags {min(lags)}..{max(lags)}, "
                  f"flip-flops {n_ff_o} -> {n_ff_c}")


if __name__ == "__main__":
    ok, msg = certify(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 0)
    print(("CERTIFIED  " if ok else "REJECTED   ") + msg)
    sys.exit(0 if ok else 1)
