"""Give an OpenRAM Liberty view the clock-to-output delay measured in SPICE (plan item 2.2, step 2).

    spice_macro_lib.py <in.lib> <out.lib> <measured_ns> [--report]

OpenRAM's views of the chip's macros carry the typical-corner clock-to-output delay at every corner (about 0.43 ns), far
below what the transistor netlist shows (toolkit/openram_energy with SRAM_ENERGY_DELAY=1: for example 2.05 ns at tt and
3.76 ns at ss for the 12 x 256 macro, from the falling clock edge to the output's crossing of VDD/2 with a 10 fF load).
This adds one constant to every cell_rise/cell_fall table of the dout pins, so that the entry nearest a 10 fF load equals
the measured worst delay; output transitions, setup and hold constraints and every other arc are unchanged. The input
side (setup of addr/din/csb/web) is not measured and keeps the view's values; that is stated with every result.
SPDX-License-Identifier: Apache-2.0
"""
import re
import sys

LOAD_PF = 0.010                       # the 10 fF load of the SPICE measurement


def tables(text):
    """(start, end, kind) of every cell_rise/cell_fall group inside a timing() of a dout pin."""
    out = []
    for pm in re.finditer(r"\bpin\s*\(\s*\"?(dout\d*(?:\[[\d:]+\])?)\"?\s*\)\s*\{", text):
        depth, i = 1, pm.end()
        while depth:                                  # the pin group's extent
            depth += {"{": 1, "}": -1}.get(text[i], 0); i += 1
        for tm in re.finditer(r"\b(cell_rise|cell_fall)\s*\([^)]*\)\s*\{", text[pm.end():i]):
            a = pm.end() + tm.start(); b = text.index("}", pm.end() + tm.end()) + 1
            out.append((a, b, tm[1]))
    return out


def nums(s):
    return [float(x) for x in re.findall(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", s)]


def at_load(group, text):
    """The table value at the measurement's load, smallest input transition (first row), interpolated linearly in the
    load index (index_2 of the group, else of its lu_table_template, whose variable_2 must be the output load)."""
    vals = nums(re.search(r"values\s*\(((?:[^()]|\n)*?)\)\s*;", group, re.S)[1])
    idx2 = re.search(r"index_2\s*\(\s*\"([^\"]*)\"", group)
    if not idx2:
        tpl = re.match(r"\w+\s*\(\s*(\w+)\s*\)", group)[1]
        t = re.search(r"lu_table_template\s*\(\s*" + tpl + r"\s*\)\s*\{(.*?)\}", text, re.S)[1]
        assert "variable_2 : total_output_net_capacitance" in t, tpl
        idx2 = re.search(r"index_2\s*\(\s*\"([^\"]*)\"", t)
    loads = nums(idx2[1])
    row = vals[:len(loads)]
    for k in range(len(loads) - 1):
        if LOAD_PF <= loads[k + 1] or k == len(loads) - 2:
            f = (LOAD_PF - loads[k]) / (loads[k + 1] - loads[k])
            return row[k] + f * (row[k + 1] - row[k])
    return row[0]


def main(src, dst, measured, report=False):
    text = open(src, newline="").read()
    groups = tables(text)
    assert groups, f"{src}: no dout cell_rise/cell_fall tables"
    ref = max(at_load(text[a:b], text) for a, b, _ in groups)
    delta = measured - ref
    out, pos = [], 0
    for a, b, _ in groups:
        g = text[a:b]
        m = re.search(r"values\s*\(((?:[^()]|\n)*?)\)\s*;", g, re.S)
        body = re.sub(r"-?\d+\.?\d*(?:[eE][-+]?\d+)?", lambda n: f"{float(n[0]) + delta:.4f}", m[1])
        out += [text[pos:a], g[:m.start(1)], body, g[m.end(1):]]
        pos = b
    out.append(text[pos:])
    open(dst, "w", newline="").write("".join(out))
    if report:
        print(f"{src}: {len(groups)} dout tables, view {ref:.3f} ns at 10 fF -> measured {measured:.3f} ns (+{delta:.3f})")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]), "--report" in sys.argv)
