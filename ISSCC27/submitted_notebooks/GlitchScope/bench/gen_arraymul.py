"""Generate a c6288-style N x N array multiplier as a SKY130 gate-level netlist.

ISCAS-85 c6288 is a 16x16 carry-save array multiplier built from 2-input NOR
full/half adders plus AND partial products; it is the classic glitch-heavy
benchmark.  This generator builds the same architecture from scratch (no third-party
netlist), so the file is fully open and reproducible:

  * partial products  pp(i,j) = a_i & b_j               -> sky130 and2_1
  * full adder        9 x nor2_1 (two NOR-XNOR stages + NOR carry)
  * half adder        4 x nor2_1 (XNOR) + inv_1 (sum) + and2_1 (carry)
  * carry-save rows j = 1..N-1, final ripple-carry row
  * instance names carry the hierarchy: pp_aII_bJJ_g0 (partial product),
    rJJcII_gK (adder in row J, column I), rf_cII_gK (final ripple row)

    python bench/gen_arraymul.py 16 bench/netlists/arraymul16.v
"""
import sys
from collections import defaultdict
from pathlib import Path


def generate(n=16, name=None, regs=False, pipe=(), cells=None):
    """``regs``: register the inputs and outputs (sky130 dfxtp_1, clock ``clk``).
    ``pipe``: rows after which a pipeline register stage is inserted (all live sums,
    carries, operand bits still needed and finished product bits are registered).
    ``cells``: {"nor2","and2","inv"[,"dff"]: glitchscope.pdk.CellRef} to build the same
    circuit from another library's cells (default: SKY130 HD names)."""
    name = name or f"arraymul{n}"
    if pipe and not regs:
        raise ValueError("pipeline stages need regs=True")
    lib_cells = cells
    gl, k = [], [0]
    scope = ["top"]          # hierarchical instance prefix, e.g. r03c07 (row 3, column 7)

    def net():
        k[0] += 1
        return f"n{k[0]}"

    def gate(kind, pins):
        if lib_cells is None:
            gl.append(("sky130_fd_sc_hd__" + kind, pins, scope[0]))
            return
        fn = {"nor2_1": "nor2", "and2_1": "and2", "inv_1": "inv", "dfxtp_1": "dff"}[kind]
        ref = lib_cells[fn]
        if fn == "dff":
            ex = ref.extra
            mp = {"CLK": ex["clk"], "D": ex["d"], "Q": ex["q"]}
        else:
            src = {"nor2": ("A", "B"), "and2": ("A", "B"), "inv": ("A",)}[fn]
            mp = dict(zip(src, ref.inputs)); mp.update({"Y": ref.output, "X": ref.output})
        gl.append((ref.name, {mp[k]: v for k, v in pins.items()}, scope[0]))

    def nor(a, b):
        y = net(); gate("nor2_1", dict(A=a, B=b, Y=y)); return y

    def and2(a, b, y=None):
        y = y or net(); gate("and2_1", dict(A=a, B=b, X=y)); return y

    def reg(x, sc):
        if x is None:
            return None
        old, scope[0] = scope[0], sc
        y = net(); gate("dfxtp_1", dict(CLK="clk", D=x, Q=y))
        scope[0] = old
        return y

    def inv(a, y=None):
        y = y or net(); gate("inv_1", dict(A=a, Y=y)); return y

    def xnor_nor(a, b):
        n1 = nor(a, b)
        return nor(nor(a, n1), nor(b, n1)), n1

    def fa(a, b, c):
        x1, n1 = xnor_nor(a, b)          # XNOR(a, b); n1 = NOR(a, b)
        s, m1 = xnor_nor(x1, c)          # XNOR(XNOR(a,b), c) = a ^ b ^ c; m1 = NOR(x1, c)
        return s, nor(n1, m1)            # carry = NOR(NOR(a,b), NOR(XNOR(a,b), c))

    def ha(a, b):
        x1, _ = xnor_nor(a, b)
        return inv(x1), and2(a, b)

    def add(bits):
        bits = [b for b in bits if b is not None]
        if len(bits) == 3:
            return fa(*bits)
        if len(bits) == 2:
            return ha(*bits)
        return (bits[0] if bits else None), None

    a = [f"a{i}" for i in range(n)]
    b = [f"b{i}" for i in range(n)]
    prod = [None] * (2 * n)
    A = [reg(x, "in_reg") for x in a] if regs else list(a)
    B = [reg(x, "in_reg") for x in b] if regs else list(b)

    def pp(i, j):
        scope[0] = f"pp_a{i:02d}_b{j:02d}"
        return and2(A[i], B[j])

    S = [pp(i, 0) for i in range(n)]
    C = [None] * n
    prod[0] = S[0]
    for j in range(1, n):
        nS, nC = [], []
        for i in range(n):
            x = pp(i, j)
            scope[0] = f"r{j:02d}c{i:02d}"
            s, c = add([x, S[i + 1] if i + 1 < n else None, C[i]])
            nS.append(s); nC.append(c)
        S, C = nS, nC
        prod[j] = S[0]
        if j in pipe:
            sc = f"pipe_r{j:02d}"
            S = [reg(x, sc) for x in S]; C = [reg(x, sc) for x in C]
            A = [reg(x, sc) for x in A]
            B = B[:j + 1] + [reg(x, sc) for x in B[j + 1:]]
            prod[:j + 1] = [reg(x, sc) for x in prod[:j + 1]]
    rc = None
    for i in range(n):
        scope[0] = f"rf_c{i:02d}"
        s, rc = add([S[i + 1] if i + 1 < n else None, C[i], rc])
        prod[n + i] = s
    prod[2 * n - 1] = prod[2 * n - 1] if rc is None else rc
    if prod[2 * n - 1] is None:
        raise RuntimeError("top product bit missing")

    if regs:
        prod = [reg(x, "out_reg") for x in prod]
    # rename product nets to p<k> (driver output renamed in place)
    ren = {prod[k]: f"p{k}" for k in range(2 * n)}
    ports = (["clk"] if regs else []) + a + b
    desc = f"c6288-style {n}x{n} NOR array multiplier" + (", registered" if regs else "") + \
           (f", pipeline after row(s) {','.join(map(str, pipe))}" if pipe else "")
    lines = [f"// {desc}, generated by bench/gen_arraymul.py (GlitchScope, Apache-2.0)",
             f"module {name}(" + ", ".join(ports + [f"p{k}" for k in range(2 * n)]) + ");"]
    lines += [f"  input {x};" for x in ports]
    lines += [f"  output p{k};" for k in range(2 * n)]
    internal = sorted({v for _, p, _ in gl for v in p.values()} - set(ports) - set(ren),
                      key=lambda s: int(s[1:]))
    lines += [f"  wire {w};" for w in internal]
    used = defaultdict(int)
    for kind, pins, sc in gl:
        conn = ", ".join(f".{p}({ren.get(v, v)})" for p, v in pins.items())
        lines.append(f"  {kind} {sc}_g{used[sc]} ({conn});")
        used[sc] += 1
    lines.append("endmodule")
    return "\n".join(lines) + "\n", len(gl)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, nargs="?", default=16)
    ap.add_argument("out", nargs="?")
    ap.add_argument("--regs", action="store_true", help="register inputs and outputs")
    ap.add_argument("--pipe", default="", help="comma-separated rows followed by a pipeline stage")
    ap.add_argument("--name")
    a_ = ap.parse_args()
    n = a_.n
    pipe = tuple(int(x) for x in a_.pipe.split(",") if x)
    out = Path(a_.out) if a_.out else Path(__file__).parent / "netlists" / f"arraymul{n}.v"
    text, nc = generate(n, name=a_.name, regs=a_.regs or bool(pipe), pipe=pipe)
    out.write_text(text)
    print(f"wrote {out} ({nc} cells)")
