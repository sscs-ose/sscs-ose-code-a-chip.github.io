#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re
import argparse

def parse_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("INPUT"):
        return ("input", line.split()[1])
    if "=" in line:
        left, right = line.split("=", 1)
        left = left.strip()
        expr = right.strip().rstrip(";")
        m = re.match(r"(\w+)\(([^)]+)\)", expr)
        if m:
            gate = m.group(1).upper()
            args = [x.strip() for x in m.group(2).split(",")]
            return ("gate", left, gate, args)
    if line.startswith("OUT"):
        left, right = line.split("=", 1)
        return ("output", left.strip(), right.strip())
    return None

def convert_gate(gate, left, args, uid):
    """Emit GF180 cells with correct pin names."""
    inst = f"_{uid:04d}_"
    if gate == "INV":
        # inv has .I input and .ZN output
        return (
            f"  gf180mcu_fd_sc_mcu9t5v0__inv_1 {inst} (\n"
            f"    .I({args[0]}),\n"
            f"    .ZN({left})\n"
            f"  );"
        )
    elif gate == "NAND":
        # nand has .A1/.A2 and inverted output .ZN
        return (
            f"  gf180mcu_fd_sc_mcu9t5v0__nand2_1 {inst} (\n"
            f"    .A1({args[0]}),\n"
            f"    .A2({args[1]}),\n"
            f"    .ZN({left})\n"
            f"  );"
        )
    elif gate == "AND":
        return (
            f"  gf180mcu_fd_sc_mcu9t5v0__and2_1 {inst} (\n"
            f"    .A1({args[0]}),\n"
            f"    .A2({args[1]}),\n"
            f"    .Z({left})\n"
            f"  );"
        )
    elif gate == "OR":
        return (
            f"  gf180mcu_fd_sc_mcu9t5v0__or2_1 {inst} (\n"
            f"    .A1({args[0]}),\n"
            f"    .A2({args[1]}),\n"
            f"    .Z({left})\n"
            f"  );"
        )
    elif gate == "XOR":
        return (
            f"  gf180mcu_fd_sc_mcu9t5v0__xor2_1 {inst} (\n"
            f"    .A1({args[0]}),\n"
            f"    .A2({args[1]}),\n"
            f"    .Z({left})\n"
            f"  );"
        )
    elif gate == "XNOR":
        return (
            f"  gf180mcu_fd_sc_mcu9t5v0__xnor2_1 {inst} (\n"
            f"    .A1({args[0]}),\n"
            f"    .A2({args[1]}),\n"
            f"    .ZN({left})\n"
            f"  );"
        )
    else:
        raise ValueError(f"Unrecognized gate: {gate}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", required=True)
    parser.add_argument("--out", dest="outfile", required=True)
    parser.add_argument("--module-name", default="mult_8bits")
    args = parser.parse_args()

    with open(args.infile) as f:
        lines = f.readlines()

    inputs, gates, outputs, wires = [], [], [], set()
    uid = 1
    for line in lines:
        res = parse_line(line)
        if not res:
            continue
        if res[0] == "input":
            inputs.append(res[1])
        elif res[0] == "gate":
            _, left, gate, inps = res
            gates.append(convert_gate(gate, left, inps, uid))
            uid += 1
            wires.add(left)
            for n in inps:
                if n.startswith("n") or n.startswith("v") or n.startswith("_"):
                    wires.add(n)
        elif res[0] == "output":
            _, name, src = res
            outputs.append((name, src))
            if src.startswith("n") or src.startswith("v") or src.startswith("_"):
                wires.add(src)

    # Build header (GF180-style top)
    header = []
    header.append(f"module {args.module_name} (A, B, OUT);")
    header.append("  input  [7:0] A;")
    header.append("  input  [7:0] B;")
    header.append("  output [15:0] OUT;")
    # internal wires: exclude OUT/ports
    if wires:
        header.append("  wire " + ", ".join(sorted(wires)) + ";")

    header.append("")
    header.append("  // Map n0..n7 to A[0..7], n8..n15 to B[0..7]")
    for i in range(0, 8):
        header.append(f"  assign n{i} = A[{i}];")
    for i in range(8, 16):
        header.append(f"  assign n{i} = B[{i-8}];")

    with open(args.outfile, "w") as f:
        f.write("\n".join(header) + "\n\n")
        for g in gates:
            f.write(g + "\n")
        f.write("\n")
        outputs_sorted = sorted(outputs, key=lambda x: int(x[0][3:]))  # x[0] like "OUT0"
        for i, (oname, src) in enumerate(outputs_sorted):
            f.write(f"  assign OUT[{i}] = {src};\n")
        f.write("endmodule\n")

if __name__ == "__main__":
    main()
