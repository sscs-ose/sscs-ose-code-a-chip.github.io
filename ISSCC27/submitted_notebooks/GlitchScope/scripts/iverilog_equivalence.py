"""Independent check of a transformed netlist with Icarus Verilog (no GlitchScope code in
the loop): behavioural models of every cell are generated from the Liberty ``function``
/ ``ff`` statements, the original and the candidate are simulated side by side with the
same random inputs, and the candidate's outputs are compared with the original's
delayed by ``latency`` cycles.

    python scripts/iverilog_equivalence.py <liberty> <original.v> <candidate.v> [latency] [cycles] [seed]

Flip-flops start at 0 in both netlists.  Registers that sit in different places start
in different states, so outputs are compared after a short warm-up; designs with
register loops (an accumulator) agree only after their own clear has been applied,
which the random inputs exercise.  Needs iverilog / vvp (tools.env: GS_YOSYS's bin
directory, or PATH).
"""
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tool(name):
    env = ROOT / "tools.env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GS_YOSYS="):
                p = Path(line.split("=", 1)[1].strip()).parent / name
                if p.exists():
                    return str(p)
    return shutil.which(name) or name


def liberty_expr(f):
    """Liberty Boolean expression -> Verilog."""
    toks = [t for t in re.findall(r"[A-Za-z_]\w*|[!&|^*+()']|[01]", f.strip().strip('"'))]
    out = []
    for t in toks:                       # implicit AND between operands
        if out and out[-1] not in ("!", "&", "|", "^", "*", "+", "(") and t not in ("&", "|", "^", "*", "+", ")", "'"):
            out.append("&")
        out.append(t)
    s = []
    for t in out:
        if t == "'":                     # postfix NOT
            if s[-1] == ")":
                depth = 0
                for j in range(len(s) - 1, -1, -1):
                    depth += s[j] == ")"
                    depth -= s[j] == "("
                    if depth == 0:
                        break
                s = s[:j] + ["~("] + s[j:] + [")"]
            else:
                s[-1] = f"(~{s[-1]})"
        else:
            s.append({"!": "~", "*": "&", "+": "|"}.get(t, t))
    return " ".join(s)


def cell_models(lib_text, cells):
    out = ["`timescale 1ns/1ps"]
    for c in sorted(cells):
        m = re.search(r'\bcell\s*\(\s*"?%s"?\s*\)\s*\{' % re.escape(c), lib_text)
        i, d = m.end(), 1
        while d:
            d += lib_text[i] == "{"
            d -= lib_text[i] == "}"
            i += 1
        blk = lib_text[m.end():i]
        pins = []
        for pm in re.finditer(r'\bpin\s*\(\s*"?(\w+)"?\s*\)\s*\{', blk):
            j, d = pm.end(), 1
            while d:
                d += blk[j] == "{"
                d -= blk[j] == "}"
                j += 1
            pb = blk[pm.end():j]
            dirn = re.search(r'direction\s*:\s*"?(\w+)"?', pb).group(1)
            fn = re.search(r'\bfunction\s*:\s*"([^"]*)"', pb)
            pins.append((pm.group(1), dirn, fn.group(1) if fn else None))
        v = [f"module {c}({', '.join(p for p, _, _ in pins)});"]
        v += [f"  {'input' if d_ == 'input' else 'output'} {p};" for p, d_, _ in pins]
        ff = re.search(r'\bff\s*\(\s*"?(\w+)"?\s*,\s*"?(\w+)"?\s*\)\s*\{([^}]*)\}', blk)
        if ff:
            iq, iqn, body = ff.groups()
            nxt = re.search(r'next_state\s*:\s*"([^"]*)"', body).group(1)
            clk = re.search(r'clocked_on\s*:\s*"([^"]*)"', body).group(1)
            v += [f"  reg {iq} = 1'b0;", f"  always @(posedge {liberty_expr(clk)}) {iq} <= {liberty_expr(nxt)};",
                  f"  wire {iqn} = ~{iq};"]
        v += [f"  assign {p} = {liberty_expr(f)};" for p, d_, f in pins if d_ == "output" and f]
        v.append("endmodule")
        out.append("\n".join(v))
    return "\n\n".join(out)


def ports(text):
    m = re.search(r"\bmodule\s+(\S+)\s*\((.*?)\)\s*;", text, re.S)
    ins = [x.strip() for x in re.findall(r"\binput\s+([^;]+);", text)]
    outs = [x.strip() for x in re.findall(r"\boutput\s+([^;]+);", text)]
    if any("[" in x and not x.startswith("\\") for x in ins + outs):
        raise ValueError("vector port declarations are not supported; use scalar (split) ports")
    return m.group(1), ins, outs


def main():
    lib, orig, cand = sys.argv[1:4]
    L = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    N = int(sys.argv[5]) if len(sys.argv) > 5 else 2000
    seed = int(sys.argv[6]) if len(sys.argv) > 6 else 1
    lib_text = Path(lib).read_text()
    texts = [Path(orig).read_text(), Path(cand).read_text()]
    cells = set()
    for t in texts:
        cells |= {m for m in re.findall(r"^\s*(\w+)\s+\S+\s*\(", t, re.M)
                  if m not in ("module", "input", "output", "wire", "assign")}
    names, ins, outs = ports(texts[0])
    _, ins2, outs2 = ports(texts[1])
    if sorted(ins) != sorted(ins2) or sorted(outs) != sorted(outs2):
        raise SystemExit("FAIL: port lists differ")
    clk = next((p for p in ins if p in ("clk", "CLK", "clock")), None)
    data = [p for p in ins if p != clk]
    W = 8
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "cells.v").write_text(cell_models(lib_text, cells))
        for k, t in enumerate(texts):
            (d / f"n{k}.v").write_text(re.sub(r"\bmodule\s+[\w$]+", f"module dut{k}", t, count=1))
        sig = lambda s: "s_" + re.sub(r"\W", "_", s.lstrip("\\").strip())       # noqa: E731
        conn = lambda k: ", ".join(f".{p if not p.startswith(chr(92)) else p + ' '}({sig(p)}{'_' + str(k) if p in outs else ''})"  # noqa: E731
                                   for p in ins + outs)
        tb = ["`timescale 1ns/1ps", "module tb;", f"  reg {', '.join(sig(p) for p in ins)};"]
        tb += [f"  wire {sig(p)}_0, {sig(p)}_1;" for p in outs]
        tb += [f"  dut0 u0({conn(0)});", f"  dut1 u1({conn(1)});"]
        tb += [f"  reg [{L}:0] h_{sig(p)};" for p in outs]
        tb += ["  integer cyc, bad, first, seed;", "  initial begin",
               f"    seed = {seed}; bad = 0; first = -1;"]
        tb += [f"    {sig(p)} = 0;" for p in ins]
        tb += [f"    for (cyc = 0; cyc < {N}; cyc = cyc + 1) begin"]
        tb += [f"      {sig(p)} = $random(seed);" for p in data]
        if clk:
            tb += [f"      #5 {sig(clk)} = 1; #5 {sig(clk)} = 0;"]
        else:
            tb += ["      #10;"]
        cmp = []
        for p in outs:
            tb += [f"      h_{sig(p)} = {{h_{sig(p)}, {sig(p)}_0}};"]
            cmp.append(f"(h_{sig(p)}[{L}] !== {sig(p)}_1)")
        tb += [f"      if (cyc >= {W + L} && ({' || '.join(cmp)})) begin bad = bad + 1; first = -1; end",
               f"      else if (cyc >= {L} && first < 0 && !({' || '.join(cmp)})) first = cyc;",
               "    end",
               f'    $display("RESULT cycles=%0d compared=%0d mismatching=%0d agree_from=%0d", {N}, {N - W - L}, bad, first);',
               "    $finish;", "  end", "endmodule"]
        (d / "tb.v").write_text("\n".join(tb))
        r = subprocess.run([tool("iverilog"), "-g2005", "-o", str(d / "sim"), str(d / "tb.v"), str(d / "cells.v"),
                            str(d / "n0.v"), str(d / "n1.v")], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("iverilog failed:\n" + r.stderr[-3000:])
        r = subprocess.run([tool("vvp"), "-n", str(d / "sim")], capture_output=True, text=True)
        line = next((l for l in r.stdout.splitlines() if l.startswith("RESULT")), r.stdout[-500:])
        print(f"{Path(cand).name} vs {Path(orig).name} (latency +{L}): {line}")
        ok = "mismatching=0" in line
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
