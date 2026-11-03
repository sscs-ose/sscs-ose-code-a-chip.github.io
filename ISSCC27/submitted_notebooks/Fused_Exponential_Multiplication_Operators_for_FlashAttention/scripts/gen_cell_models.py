#!/usr/bin/env python3
"""gen_cell_models.py -- generate behavioural Verilog models from the
nangate45 Liberty file (function / ff / latch attributes) for gate-level sim."""
from __future__ import annotations

import re
import sys


def strip_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"//[^\n]*", "", s)
    return s


def block_after(s: str, i: int) -> str:
    """s[i] == '{' -> return contents up to the matching '}'."""
    depth = 0
    for j in range(i, len(s)):
        if s[j] == "{":
            depth += 1
        elif s[j] == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j]
    return ""


def verilog_expr(e: str) -> str:
    e = e.replace("!", "~")
    return e


def main() -> int:
    lib = sys.argv[1]
    out = sys.argv[2]
    txt = strip_comments(open(lib, errors="ignore").read())
    mods = []
    for m in re.finditer(r"cell\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\{", txt):
        name = m.group(1)
        body = block_after(txt, m.end() - 1)
        pins = []
        for pm in re.finditer(r"(?<![A-Za-z0-9_])pin\s*\(\s*([A-Za-z0-9_]+)\s*\)\s*\{", body):
            pname = pm.group(1)
            pbody = block_after(body, pm.end() - 1)
            d = re.search(r"direction\s*:\s*(\w+)", pbody)
            f = re.search(r'function\s*:\s*"([^"]+)"', pbody)
            pins.append((pname, d.group(1) if d else "input",
                         f.group(1) if f else None))
        if not pins:
            continue
        ins = [p for p in pins if p[1] == "input"]
        outs = [p for p in pins if p[1] == "output"]
        if not outs:
            continue
        if re.search(r"latch\s*\(", body):
            continue
        ffm = re.search(r"ff\s*\([^)]*\)\s*\{", body)
        if ffm:
            ffb = block_after(body, ffm.end() - 1)
            ns = re.search(r'next_state\s*:\s*"([^"]+)"', ffb)
            ck = re.search(r'clocked_on\s*:\s*"([^"]+)"', ffb)
            clr = re.search(r'clear\s*:\s*"([^"]+)"', ffb)
            pre = re.search(r'preset\s*:\s*"([^"]+)"', ffb)
            q_names = [p[0] for p in outs if p[0] in ("Q", "QN")]
            qout = "Q" if "Q" in q_names else outs[0][0]
            qn = "QN" if "QN" in q_names else None
            ports = [p[0] for p in ins] + [p[0] for p in outs]
            decl = ",\n    ".join(ports)
            lines = [f"module {name} ({decl});"]
            for p in ins:
                lines.append(f"  input {p[0]};")
            for p in outs:
                lines.append(f"  output {p[0]};")
            lines.append("  reg q_r;")
            sens = []
            rst = []
            if clr and clr.group(1).startswith("!"):
                pin = clr.group(1)[1:]
                sens.append(f"negedge {pin}")
                rst.append(f"if (!{pin}) q_r <= 1'b0; else ")
            if pre and pre.group(1).startswith("!"):
                pin = pre.group(1)[1:]
                sens.append(f"negedge {pin}")
                rst.append(f"if (!{pin}) q_r <= 1'b1; else ")
            clk = ck.group(1) if ck else "CK"
            edge = ", ".join([f"posedge {clk}"] + sens)
            body_stmt = "".join(rst) + f"q_r <= {ns.group(1)};"
            lines.append(f"  always @({edge}) {body_stmt}")
            lines.append(f"  assign {qout} = q_r;")
            if qn:
                lines.append(f"  assign {qn} = ~q_r;")
            lines.append("endmodule")
            mods.append("\n".join(lines))
            continue
        # combinational
        if "IQ" in body:          # clock-gating cells reference internal nodes
            continue
        ports = [p[0] for p in ins] + [p[0] for p in outs]
        decl = ", ".join(ports)
        lines = [f"module {name} ({decl});"]
        for p in ins:
            lines.append(f"  input {p[0]};")
        for p in outs:
            lines.append(f"  output {p[0]};")
        for p in outs:
            expr = p[2]
            if expr is None:
                lines.append(f"  assign {p[0]} = 1'b0;")
            else:
                lines.append(f"  assign {p[0]} = {verilog_expr(expr)};")
        lines.append("endmodule")
        mods.append("\n".join(lines))
    with open(out, "w") as f:
        f.write("// generated from %s\n" % lib)
        f.write("\n\n".join(mods))
        f.write("\n")
    print(f"wrote {out}: {len(mods)} cell models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
