"""Transistor-level energy per clock cycle of an OpenRAM SKY130 macro (typical corner, 1.8 V).

OpenRAM's Liberty power views are analytical and, for SKY130 macros, not physical (they report megawatts for
a single macro). This tool measures what a read, a write and an idle cycle actually cost by simulating the
macro's own transistor netlist in ngspice: it drives port 0 through idle cycles, writes of random data to
random addresses and reads of the same addresses, integrates the supply current over every clock cycle, and
checks that every read returns the data written. A flat layout extraction of the same macro can be
simulated the same way to measure what the wiring changes (see run_openram_energy.sh).

deck:   openram_energy.py <netlist> <macro> <deck.sp> <pdk sky130.lib.spice>
parse:  openram_energy.py --parse <ngspice log> <macro> <out.json>

Environment: SRAM_ENERGY_CORNER, SRAM_ENERGY_VDD, SRAM_ENERGY_TEMP process corner (a section of sky130.lib.spice),
supply and temperature (default tt, 1.8 V, 25 C; ss is 1.60 V 100 C and ff 1.95 V -40 C in the sign-off);
SRAM_ENERGY_DELAY=1 also measures, for every read, the time from the falling clock edge to the output's crossing of
VDD/2 (OpenRAM macros present read data after the falling edge); SRAM_ENERGY_T_NS clock period in ns (default 40, i.e. 25 MHz); SRAM_ENERGY_SETTLE idle cycles
before the first write (default 3; a large macro needs more to power up); SRAM_ENERGY_ACCESSES writes and
reads (default 3; fewer shorten a slow flat-layout run); SRAM_ENERGY_READS=repeat reads one address every
time; SRAM_ENERGY_RELTOL the transient's relative tolerance (default 1e-3).
Ports: port 0 (din0, addr0, dout0, csb0, web0, clk0, wmask0, spare_wen0) is exercised. A second port of a
1rw1r macro (csb1, clk1, addr1, dout1) is held idle: chip select deasserted, clock and address low. A spare
column (spare_wen0 present) is written with 0 and not checked.
Netlist requirements: the SKY130 models set scale=1u, so device sizes must be unitless microns, and ngspice
must run with "set ngbehavior=hsa" in .spiceinit (run_openram_energy.sh does both).
SPDX-License-Identifier: Apache-2.0
"""
import json
import os
import random
import re
import sys

VDD = float(os.environ.get("SRAM_ENERGY_VDD", 1.8))   # V
CORNER = os.environ.get("SRAM_ENERGY_CORNER", "tt")    # section of sky130.lib.spice: tt, ss, ff, ...
TEMP = float(os.environ.get("SRAM_ENERGY_TEMP", 25))   # degrees C
T = float(os.environ.get("SRAM_ENERGY_T_NS", 40.0))   # clock period [ns]
SETTLE = int(os.environ.get("SRAM_ENERGY_SETTLE", 3))
N_W = int(os.environ.get("SRAM_ENERGY_ACCESSES", 3))
REPEAT = os.environ.get("SRAM_ENERGY_READS") == "repeat"
DELAY = os.environ.get("SRAM_ENERGY_DELAY") == "1"     # also measure the clock-to-output delay of every read
RELTOL = os.environ.get("SRAM_ENERGY_RELTOL", "1e-3")
# (tier-3 clone, D2) SRAM_ENERGY_IN_AT=<s ns>: every input (din, addr, csb, web) changes at s relative to the rising
# clock edge of its cycle instead of at the cycle start (s = -T/2). s in (-T, 0): setup -s for the new value and hold
# T + s for the previous one; a grid of s finds the smallest setup (s near 0) and hold (s near -T) that still write and
# read correctly
IN_AT = os.environ.get("SRAM_ENERGY_IN_AT")
SUPPLY = {"vdd": "vdd", "vccd1": "vdd", "gnd": "0", "vssd1": "0"}


def pins(netlist, name):
    text = open(netlist).read()
    m = re.search(rf"^\.subckt\s+{re.escape(name)}\s+(.*?)(?=^[^+\s])", text, re.M | re.S | re.I)
    if not m:
        raise SystemExit(f"subcircuit {name} not found in {netlist}")
    return [t for t in m[1].replace("\n+", " ").split() if t != "+"]


def bus(p, prefix):
    sel = [x for x in p if re.fullmatch(rf"{prefix}\[(\d+)\]", x)]
    return sorted(sel, key=lambda x: int(re.search(r"\[(\d+)\]", x)[1]))


def pwl(vals, tr=0.1):
    pts, prev = [(0.0, vals[0])], vals[0]
    for k, v in enumerate(vals[1:], 1):
        if v != prev:
            tk = k * T + (T / 2 + float(IN_AT) if IN_AT is not None else 0.0)
            pts += [(tk - tr / 2, prev), (tk + tr / 2, v)]
        prev = v
    return "PWL(" + " ".join(f"{t:.3f}n {VDD * v:.2f}" for t, v in pts) + ")"


def nd(x):
    return re.sub(r"[\[\]]", "_", x)


def data_bits(p):
    """Bits of a word that carry data: a spare column (spare_wen0) is not checked."""
    spare = any(x.lower().startswith("spare_wen0") for x in p)
    return len(bus(p, "din0")) - (1 if spare else 0)


def deck(netlist, name, out, pdk_lib):
    p = pins(netlist, name)
    din, addr, dout, wm = bus(p, "din0"), bus(p, "addr0"), bus(p, "dout0"), bus(p, "wmask0")
    nbits = data_bits(p)
    rnd = random.Random(2027)
    n = SETTLE + 1 + 2 * N_W + 1
    addrs = rnd.sample(range(2 ** (len(addr) - 1)), N_W)
    data = [rnd.getrandbits(nbits) for _ in range(N_W)]
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
    # newer OpenRAM bitcells instantiate PDK "special" devices (sky130_fd_pr__special_*), whose models live in the PDK's
    # libs.ref/sky130_fd_pr/spice/<device>.pm3.spice. Some tech libraries already include them (all.spice of open_pdks);
    # a second include makes ngspice ignore the redefined subcircuit and then fail on its parameters, so a model is
    # included only when no file of the tech library mentions it
    here = os.path.dirname(os.path.abspath(pdk_lib))
    spice_dir = os.path.normpath(os.path.join(here, "..", "..", "libs.ref", "sky130_fd_pr", "spice"))
    special = sorted(set(re.findall(r"(sky130_fd_pr__special_\w+)", open(netlist).read())))
    lib_text = "".join(open(os.path.join(here, f), errors="ignore").read() for f in sorted(os.listdir(here))
                       if f.endswith(".spice") and os.path.isfile(os.path.join(here, f))) if special else ""
    extra = [f".include {os.path.join(spice_dir, d + '.pm3.spice')}" for d in special
             if d + ".pm3.spice" not in lib_text and os.path.exists(os.path.join(spice_dir, d + ".pm3.spice"))]
    L = [f"* energy of {name}", f'.lib "{pdk_lib}" {CORNER}', f".include {netlist}", *extra, f"Vvdd vdd 0 PWL(0 0 2n {VDD})",
         "X0 " + " ".join(SUPPLY.get(x.lower(), nd(x)) for x in p) + f" {name}"]
    L += [f"V{nd(x)} {nd(x)} 0 {pwl(d[b])}" for b, x in enumerate(din)]
    L += [f"V{nd(x)} {nd(x)} 0 {pwl(a[b])}" for b, x in enumerate(addr)]
    L += [f"V{nd(x)} {nd(x)} 0 {VDD}" for x in wm]
    L += [f"V{nd(x)} {nd(x)} 0 0" for x in p if x.lower().startswith("spare_wen0")]
    L += [f"Vcsb0 csb0 0 {pwl(csb)}", f"Vweb0 web0 0 {pwl(web)}",
          f"Vclk0 clk0 0 PULSE(0 {VDD} {T / 2}n 0.1n 0.1n {T / 2 - 0.1}n {T}n)"]
    # a second (read) port, if any, is idle: chip select high, clock and address low
    second = [x for x in p if x.lower() in ("csb1", "clk1") or re.fullmatch(r"addr1\[\d+\]", x)]
    L += [f"V{nd(x)} {nd(x)} 0 {VDD if x.lower() == 'csb1' else 0}" for x in second]
    L += [f"C{nd(x)} {nd(x)} 0 10f" for x in dout + bus(p, "dout1")]
    for k in range(SETTLE, n):              # one clock cycle, rising edge to rising edge
        L.append(f".meas tran q{k} INTEG i(vvdd) FROM={k * T + T / 2:.3f}n TO={min((k + 1) * T + T / 2, n * T + T / 2 - 0.01):.3f}n")
    for i in range(N_W):
        ts = (w0 + N_W + i + 1) * T + T / 2 - 1.0
        for b, x in enumerate(dout[:nbits]):
            L.append(f".meas tran r{i}b{b} FIND v({nd(x)}) AT={ts:.3f}n")
    for i in range(N_W if DELAY else 0):    # data appears after the falling edge that follows the read's rising edge
        tf = (w0 + N_W + i + 1) * T + 0.05
        for b, x in enumerate(dout[:nbits]):
            L.append(f".meas tran t{i}b{b} WHEN v({nd(x)})={VDD / 2:.3f} CROSS=1 TD={tf + 0.01:.3f}n")
    L += [f".options klu method=gear reltol={RELTOL}", f".temp {TEMP:g}", f".tran 0.2n {n * T + T / 2}n UIC", ".save i(vvdd)", ".end"]
    open(out, "w").write("\n".join(L) + "\n")
    json.dump({"settle": SETTLE, "writes": N_W, "data": [data[j] for j in rd], "data_bits": nbits,
               "reads": "repeat" if REPEAT else "distinct", "clock_ns": T,
               "corner": CORNER, "vdd": VDD, "temp_c": TEMP, "delay": DELAY, "in_at_ns": IN_AT}, open(out + ".json", "w"))


def parse(log, name, out):
    meta = json.load(open(log.replace(".log", ".sp.json")))
    txt = open(log).read()
    e = {int(k): -VDD * float(v) * 1e12 for k, v in re.findall(r"^q(\d+)\s*=\s*([-0-9.eE+]+)", txt, re.M)}
    if not e:
        raise SystemExit(f"{log}: no energy measurements; the transient did not finish (see the log)")
    w0, nw = meta["settle"] + 1, meta["writes"]
    ok = []
    for i in range(nw):
        bits = {int(b): float(v) for b, v in re.findall(rf"^r{i}b(\d+)\s*=\s*([-0-9.eE+]+)", txt, re.M)}
        ok.append(sum(1 << b for b, v in bits.items() if v > VDD / 2) == meta["data"][i] and len(bits) == meta["data_bits"])
    delays = []                 # clock fall to output crossing; a crossing later than half a cycle belongs to another cycle
    for i in range(nw):
        tf = (meta["settle"] + 1 + nw + i + 1) * T + 0.05
        for b, v in re.findall(rf"^t{i}b(\d+)\s*=\s*([-0-9.eE+]+)", txt, re.M):
            d = float(v) * 1e9 - tf
            if 0 < d < T / 2:
                delays.append(d)
    t = re.search(r"Total elapsed time \(seconds\) =\s*([0-9.]+)", txt)
    res = {"macro": name, "per_cycle_pj": [round(e[k], 3) for k in sorted(e)],
           "idle_pj": [round(e[meta["settle"]], 3), round(e[max(e)], 3)],
           "write_pj": [round(e[w0 + i], 3) for i in range(nw)], "read_pj": [round(e[w0 + nw + i], 3) for i in range(nw)],
           "reads_correct": ok, "elapsed_s": float(t[1]) if t else None}
    if meta.get("delay"):
        res.update({"clk_to_dout_ns": {"n": len(delays), "max": round(max(delays), 3) if delays else None,
                                       "median": round(sorted(delays)[len(delays) // 2], 3) if delays else None},
                    "corner": meta["corner"], "vdd": meta["vdd"], "temp_c": meta["temp_c"]})
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps(res))


if __name__ == "__main__":
    if sys.argv[1] == "--parse":
        parse(*sys.argv[2:5])
    else:
        deck(*sys.argv[1:5])
