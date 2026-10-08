"""Transistor-level energy of one OpenRAM SKY130 macro per clock cycle (typical corner, 1.8 V, 25 MHz).

deck:  writes an ngspice deck that drives the macro for three idle cycles, three writes of random data to
       random addresses, three reads of the same addresses and one idle cycle, and integrates the supply
       current over every clock cycle; the read data is sampled at the end of each read cycle.
       SRAM_ENERGY_ACCESSES=n changes the number of writes and reads (fewer shorten a slow flat-layout run);
       SRAM_ENERGY_READS=repeat reads the first address every time, as the chip's macros mostly do;
       SRAM_ENERGY_SETTLE=n sets the number of idle cycles (a large macro needs more to finish powering up);
       SRAM_ENERGY_RELTOL sets the transient's relative tolerance (default 1e-3).
parse: turns the ngspice log into per-cycle energies (pJ) and checks that every read returned the data
       written.
Netlist requirements (see scripts/sram_energy_spice.sh): the SKY130 models set scale=1u, so device sizes
must be unitless microns, and ngspice must run with "set ngbehavior=hsa" in .spiceinit.
usage: sram_energy_deck.py <netlist> <macro> <deck.sp> <pdk sky130.lib.spice>
       sram_energy_deck.py --parse <log> <macro> <out.json>
SPDX-License-Identifier: Apache-2.0
"""
import json
import os
import random
import re
import sys

VDD = 1.8                                    # V
T = float(os.environ.get("SRAM_ENERGY_T_NS", 40.0))   # clock period [ns]; the committed results use 40 (25 MHz)
SETTLE = int(os.environ.get("SRAM_ENERGY_SETTLE", 3))   # idle cycles before the first write
N_W = int(os.environ.get("SRAM_ENERGY_ACCESSES", 3))   # writes (= reads)
REPEAT = os.environ.get("SRAM_ENERGY_READS") == "repeat"
RELTOL = os.environ.get("SRAM_ENERGY_RELTOL", "1e-3")   # integration tolerance of the transient


def pins(netlist, name):
    text = open(netlist).read()
    m = re.search(rf"^\.subckt\s+{re.escape(name)}\s+(.*?)(?=^[^+\s])", text, re.M | re.S | re.I)
    return [t for t in m[1].replace("\n+", " ").split() if t != "+"]


def bus(p, prefix):
    sel = [x for x in p if re.fullmatch(rf"{prefix}\[(\d+)\]", x)]
    return sorted(sel, key=lambda x: int(re.search(r"\[(\d+)\]", x)[1]))


def pwl(vals, tr=0.1):
    pts, prev = [(0.0, vals[0])], vals[0]
    for k, v in enumerate(vals[1:], 1):
        if v != prev:
            pts += [(k * T - tr / 2, prev), (k * T + tr / 2, v)]
        prev = v
    return "PWL(" + " ".join(f"{t:.3f}n {VDD * v:.2f}" for t, v in pts) + ")"


def nd(x):
    return re.sub(r"[\[\]]", "_", x)


def deck(netlist, name, out, pdk_lib):
    p = pins(netlist, name)
    din, addr, dout, wm = bus(p, "din0"), bus(p, "addr0"), bus(p, "dout0"), bus(p, "wmask0")
    rnd = random.Random(2027)
    n = SETTLE + 1 + 2 * N_W + 1
    addrs = rnd.sample(range(2 ** (len(addr) - 1)), N_W)
    data = [rnd.getrandbits(len(din) - 1) for _ in range(N_W)]
    csb, web = [1] * n, [1] * n
    a, d = [[0] * n for _ in addr], [[0] * n for _ in din]
    w0 = SETTLE + 1
    rd = [0] * N_W if REPEAT else list(range(N_W))      # which written word each read fetches
    for i in range(N_W):
        for k, rw, j in ((w0 + i, 0, i), (w0 + N_W + i, 1, rd[i])):
            csb[k], web[k] = 0, rw
            for b in range(len(addr)):
                a[b][k] = (addrs[j] >> b) & 1
            for b in range(len(din)):
                d[b][k] = (data[i] >> b) & 1 if rw == 0 else 0
    sup = {"vdd": "vdd", "vccd1": "vdd", "gnd": "0", "vssd1": "0"}
    L = [f"* energy of {name}", f'.lib "{pdk_lib}" tt', f".include {netlist}", f"Vvdd vdd 0 PWL(0 0 2n {VDD})",
         "X0 " + " ".join(sup.get(x.lower(), nd(x)) for x in p) + f" {name}"]
    L += [f"V{nd(x)} {nd(x)} 0 {pwl(d[b])}" for b, x in enumerate(din)]
    L += [f"V{nd(x)} {nd(x)} 0 {pwl(a[b])}" for b, x in enumerate(addr)]
    L += [f"V{nd(x)} {nd(x)} 0 {VDD}" for x in wm]
    L += [f"V{nd(x)} {nd(x)} 0 0" for x in p if x.lower().startswith("spare_wen0")]
    L += [f"Vcsb0 csb0 0 {pwl(csb)}", f"Vweb0 web0 0 {pwl(web)}",
          f"Vclk0 clk0 0 PULSE(0 {VDD} {T / 2}n 0.1n 0.1n {T / 2 - 0.1}n {T}n)"]
    L += [f"C{nd(x)} {nd(x)} 0 10f" for x in dout]
    for k in range(SETTLE, n):              # one clock cycle, rising edge to rising edge
        L.append(f".meas tran q{k} INTEG i(vvdd) FROM={k * T + T / 2:.3f}n TO={min((k + 1) * T + T / 2, n * T + T / 2 - 0.01):.3f}n")
    for i in range(N_W):
        ts = (w0 + N_W + i + 1) * T + T / 2 - 1.0
        for b, x in enumerate(dout[:len(din) - 1]):
            L.append(f".meas tran r{i}b{b} FIND v({nd(x)}) AT={ts:.3f}n")
    L += [f".options klu method=gear reltol={RELTOL}", ".temp 25", f".tran 0.2n {n * T + T / 2}n UIC", ".save i(vvdd)", ".end"]
    open(out, "w").write("\n".join(L) + "\n")
    json.dump({"settle": SETTLE, "writes": N_W, "data": [data[j] for j in rd], "data_bits": len(din) - 1,
               "reads": "repeat" if REPEAT else "distinct"}, open(out + ".json", "w"))


def parse(log, name, out):
    meta = json.load(open(log.replace(".log", ".sp.json")))
    txt = open(log).read()
    e = {int(k): -VDD * float(v) * 1e12 for k, v in re.findall(r"^q(\d+)\s*=\s*([-0-9.eE+]+)", txt, re.M)}
    w0, nw = meta["settle"] + 1, meta["writes"]
    ok = []
    for i in range(nw):
        bits = {int(b): float(v) for b, v in re.findall(rf"^r{i}b(\d+)\s*=\s*([-0-9.eE+]+)", txt, re.M)}
        ok.append(sum(1 << b for b, v in bits.items() if v > VDD / 2) == meta["data"][i] and len(bits) == meta["data_bits"])
    t = re.search(r"Total elapsed time \(seconds\) =\s*([0-9.]+)", txt)
    res = {"macro": name, "per_cycle_pj": [round(e[k], 3) for k in sorted(e)],
           "idle_pj": [round(e[meta["settle"]], 3), round(e[max(e)], 3)],
           "write_pj": [round(e[w0 + i], 3) for i in range(nw)], "read_pj": [round(e[w0 + nw + i], 3) for i in range(nw)],
           "reads_correct": ok, "elapsed_s": float(t[1]) if t else None}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    if sys.argv[1] == "--parse":
        parse(*sys.argv[2:5])
    else:
        deck(*sys.argv[1:5])
