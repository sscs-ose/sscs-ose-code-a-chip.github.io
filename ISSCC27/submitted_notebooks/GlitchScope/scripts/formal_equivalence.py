"""Formal sequential equivalence of a rewritten netlist and its original (open tools: Yosys + ABC).

Both netlists are read with their SKY130 cells' Liberty functions (Yosys ``read_liberty``), flattened and placed in
one miter: same inputs every cycle, and an output check that starts after ``skip`` cycles (a retimed design reaches
the original's state only once its pipeline has been filled from the common all-zero power-up state; ``skip`` >= the
pipeline depth plus the added latency).  The miter is bit-blasted to AIGER and handed to ABC:

  * ``dprove``  unbounded proof (sequential sweeping, retiming-aware induction, interpolation / PDR)
  * ``bmc3``    bounded check of every input sequence up to ``--frames`` cycles if no proof is found

    python scripts/formal_equivalence.py <liberty> <original.v> <candidate.v> [--latency 0] [--skip 3] [--frames 20]
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def tools():
    env = dict(l.split("=", 1) for l in (ROOT / "tools.env").read_text().split() if "=" in l) if (ROOT / "tools.env").exists() else {}
    yosys = env.get("GS_YOSYS", "yosys")
    return yosys, str(Path(yosys).with_name("yosys-abc"))


def ports(path):
    t = Path(path).read_text()
    m = re.search(r"module\s+(\w+)\s*\((.*?)\);", t, re.S)
    ins = re.findall(r"^\s*input\s+(?:\[[^\]]+\]\s*)?([\w\\\[\]\.$]+)\s*;", t, re.M)
    outs = re.findall(r"^\s*output\s+(?:\[[^\]]+\]\s*)?([\w\\\[\]\.$]+)\s*;", t, re.M)
    return m.group(1), ins, outs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lib"); ap.add_argument("gold"); ap.add_argument("gate")
    ap.add_argument("--latency", type=int, default=0)
    ap.add_argument("--skip", type=int, default=3)
    ap.add_argument("--frames", type=int, default=20)
    ap.add_argument("--timeout", type=int, default=1800)
    a = ap.parse_args()
    yosys, abc = tools()
    top, ins, outs = ports(a.gold)
    clk = next(i for i in ins if i in ("clk", "CLK", "clock"))
    data_in = [i for i in ins if i != clk]
    with tempfile.TemporaryDirectory(prefix="gs_feq_") as td:
        td = Path(td)
        g = Path(a.gold).read_text().replace(f"module {top}", "module gold", 1)
        c = Path(a.gate).read_text().replace(f"module {top}", "module gate", 1)
        (td / "gold.v").write_text(g); (td / "gate.v").write_text(c)
        L = a.latency
        n = max(a.skip + L, 1)
        conn = ", ".join(f".{p}({p})" for p in ins)
        w = [f"module miter({', '.join(ins)}, bad);", "  input " + ", ".join(ins) + ";", "  output bad;"]
        w += [f"  wire {o}_g, {o}_c;" for o in outs]
        w.append(f"  gold G({conn}, " + ", ".join(f".{o}({o}_g)" for o in outs) + ");")
        w.append(f"  gate C({conn}, " + ", ".join(f".{o}({o}_c)" for o in outs) + ");")
        # gold outputs delayed by the added latency, so they line up with the candidate's
        prev = {o: f"{o}_g" for o in outs}
        for k in range(L):
            for o in outs:
                w.append(f"  reg {o}_d{k} = 1'b0; always @(posedge {clk}) {o}_d{k} <= {prev[o]};")
                prev[o] = f"{o}_d{k}"
        w.append(f"  reg [7:0] cnt = 8'd0; always @(posedge {clk}) if (cnt != 8'd{n}) cnt <= cnt + 8'd1;")
        diff = " | ".join(f"({prev[o]} ^ {o}_c)" for o in outs)
        w.append(f"  assign bad = (cnt == 8'd{n}) & ({diff});")
        w.append("endmodule")
        (td / "miter.v").write_text("\n".join(w) + "\n")
        ys = (f"read_liberty -ignore_miss_func {a.lib}\nread_verilog gold.v gate.v\nread_verilog miter.v\n"
              "hierarchy -top miter\nproc\nflatten\nopt_clean\ndffunmap\nsetundef -zero\nmemory_map\nopt -fast -nodffe -nosdff\n"
              "techmap\nopt -fast -nodffe -nosdff\nabc -g AND\ndffunmap\nzinit\naigmap\nopt_clean\nwrite_aiger -zinit miter.aig\nstat\n")
        (td / "m.ys").write_text(ys)
        r = subprocess.run([yosys, "-q", "-s", "m.ys"], cwd=td, capture_output=True, text=True)
        if r.returncode:
            sys.exit("yosys failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])
        for cmd in (f"read miter.aig; print_stats; dprove -v", f"read miter.aig; bmc3 -F {a.frames} -v"):
            try:
                r = subprocess.run([abc, "-c", cmd], cwd=td, capture_output=True, text=True, timeout=a.timeout)
                out = r.stdout
            except subprocess.TimeoutExpired:
                out = "TIMEOUT"
            if re.search(r"asserted in frame|[Nn]ot equivalent|NOT EQUIVALENT", out):
                verdict = "FAILED (counterexample)"
            elif re.search(r"Networks are equivalent|Property proved", out):
                verdict = "PROVED"
            elif "bmc3" in cmd and re.search(r"No output asserted|Reached limit on the number of timeframes", out):
                verdict = f"NO MISMATCH in {a.frames} cycles"
            else:
                verdict = "UNDECIDED"
            stats = re.search(r"(i/o\s*=.*?lat\s*=\s*\d+)", out)
            print(f"{cmd.split(';')[-1].strip():12s} {verdict:24s} {stats.group(1) if stats else ''}")
            print("   " + " | ".join(l.strip() for l in out.splitlines()[-4:]))
            if verdict.startswith("PROVED") and "dprove" in cmd:
                break


if __name__ == "__main__":
    main()
