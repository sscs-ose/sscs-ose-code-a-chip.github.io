"""Reader for flat, technology-mapped structural Verilog written by Yosys
(``write_verilog -noattr -noexpr`` after ``splitnets -ports``).

Every instance must be a known SKY130 HD cell; the cell's logic kind is derived
from its library name (``sky130_fd_sc_hd__a21oi_1`` -> ``A21OI``).  ``assign``
statements are treated as pure net aliases.  The returned Network uses
placeholder unit delays; real timing comes from the Liberty delay provider.
"""
from __future__ import annotations

import re
from pathlib import Path

from dataclasses import dataclass, field
from typing import List, Optional

from .model import Cell, Network
from .logic import SUPPORTED_KINDS

PREFIX = "sky130_fd_sc_hd__"
_ID = r"(?:\\\S+|[A-Za-z_][A-Za-z0-9_$]*)"


def _norm(name: str) -> str:
    name = name.strip()
    return name[1:] if name.startswith("\\") else name


def kind_of(libcell: str) -> str:
    base = libcell[len(PREFIX):] if libcell.startswith(PREFIX) else libcell
    kind = re.sub(r"_\d+$", "", base).upper()
    if kind == "CLKINV":
        kind = "INV"
    return kind


FLOP_RE = re.compile(r"^dfxtp_\d+$")
# physical-only cells inserted by place-and-route (no logic function)
PHYSICAL_RE = re.compile(r"^(tapvpwrvgnd|tap|decap|fill|diode|lpflow_decapkapwr|fakediode)(_\d+)?$")


@dataclass
class Flop:
    """Rising-edge D flip-flop.  ``q``/``qn`` may be None when the cell has no such
    output.  ``clear``/``preset``: Liberty expressions over ``ctrl`` pins (async
    set/reset, applied at the clock edge)."""
    name: str
    libcell: str
    d: str
    q: Optional[str]
    clk: str
    qn: Optional[str] = None
    d_pin: str = "D"
    clk_pin: str = "CLK"
    q_pin: Optional[str] = "Q"
    qn_pin: Optional[str] = None
    clear: Optional[str] = None
    preset: Optional[str] = None
    ctrl: dict = field(default_factory=dict)

    @property
    def outputs(self):
        """[(net, pin, inverted)] of the connected state outputs."""
        out = []
        if self.q:
            out.append((self.q, self.q_pin, 0))
        if self.qn:
            out.append((self.qn, self.qn_pin, 1))
        return out


@dataclass
class Design:
    """Sequential design split at flip-flops.

    ``network`` is the combinational logic: its primary inputs are the real
    inputs (minus clocks) plus all flop Q nets; its primary outputs are the real
    outputs plus all flop D nets."""
    network: Network
    flops: List[Flop]
    real_inputs: List[str]
    real_outputs: List[str]
    clocks: List[str]
    # source-level information (for writing a transformed netlist back)
    module: str = ""
    input_ports: List[str] = field(default_factory=list)      # declared order, buses expanded
    output_ports: List[str] = field(default_factory=list)
    port_net: dict = field(default_factory=dict)              # output port -> canonical driven net
    tie_cells: dict = field(default_factory=dict)             # const net -> (libcell, pin)
    clock_tree: list = field(default_factory=list)            # CTS buffers/inverters removed from the logic


def read_design(path, lib, clocks=("clk", "CLK", "clock"), initial_value: int = 0) -> Design:
    """Read a mapped netlist (combinational or with dfxtp flops) using Liberty
    functions for any combinational cell."""
    return _read(path, lib, clocks, initial_value)


def read_verilog(path, initial_value: int = 0, lib=None) -> Network:
    d = _read(path, lib, (), initial_value)
    if d.flops:
        raise ValueError("netlist contains flip-flops: use read_design()")
    return d.network


def _read(path, lib, clocks, initial_value):
    text = Path(path).read_text()
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    m = re.search(r"\bmodule\s+(" + _ID + r")\s*\((.*?)\)\s*;(.*?)\bendmodule", text, re.S)
    if not m:
        raise ValueError("no module found")
    body = m.group(3)
    inputs, outputs = [], []
    for kw, dst in (("input", inputs), ("output", outputs)):
        # "input a;", "input a, b, c;", "input [3:0] a, b;", "input wire [3:0] a;"
        for d in re.finditer(r"\b" + kw + r"\s+(?:wire\s+|reg\s+)?(\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([^;]+);", body):
            names = [_norm(x) for x in re.findall(_ID, d.group(4))]
            if d.group(1):
                hi, lo = int(d.group(2)), int(d.group(3))
                for nm in names:
                    dst.extend(f"{nm}[{i}]" for i in range(min(hi, lo), max(hi, lo) + 1))
            else:
                dst.extend(names)
    # aliases from assign statements (single or concatenated)
    alias, const_assign = {}, {}
    for a in re.finditer(r"\bassign\s+(.*?)=(.*?);", body, re.S):
        cm = re.fullmatch(r"\s*\d*'[bhd]([0-9a-fA-F]+)\s*", a.group(2))
        if cm:                                   # constant: assign n = 1'b0 / 1'h1
            lhs = [_norm(x) for x in re.findall(_ID, a.group(1))]
            if len(lhs) == 1:
                const_assign[lhs[0]] = int(cm.group(1), 16) & 1
                continue
        lhs = [_norm(x) for x in re.findall(_ID, a.group(1))]
        rhs = [_norm(x) for x in re.findall(_ID, a.group(2))]
        if len(lhs) != len(rhs):
            raise ValueError(f"unsupported assign: {a.group(0)}")
        alias.update(zip(lhs, rhs))

    def canon(n):
        seen = set()
        while n in alias and n not in seen:
            seen.add(n)
            n = alias[n]
        return n

    cells, flops, consts, tie_cells = [], [], dict(const_assign), {}
    inst_re = re.compile(r"\b([A-Za-z_][\w$]*)\s+(" + _ID + r")\s*\((.*?)\)\s*;", re.S)
    for im in inst_re.finditer(body):
        libcell, inst, conns = im.group(1), _norm(im.group(2)), im.group(3)
        if libcell in ("module", "assign", "input", "output", "wire", "inout", "reg"):
            continue
        pins = {p: _norm(n) for p, n in re.findall(r"\.(\w+)\s*\(\s*(" + _ID + r")\s*\)", conns)}
        lc = lib.cells.get(libcell) if lib is not None else None
        base = libcell[len(PREFIX):] if libcell.startswith(PREFIX) else libcell
        if lc is None and not libcell.startswith(PREFIX):
            if re.search(r"(?i)(tap|fill|decap|diode|endcap|welltie)", libcell):
                continue                                # physical-only cell not in the Liberty
            raise ValueError(f"unknown cell type {libcell} ({inst}): not in the Liberty library")
        if PHYSICAL_RE.match(base):
            continue
        if lc is not None:
            outs_all = [p for p in lc.pins.values() if p.direction == "output"]
            if not outs_all and lc.seq is None:
                continue                                # physical-only cell (no outputs)
            fn = {p.name: (p.function or "").replace(" ", "") for p in outs_all}
            if outs_all and all(fn[p.name] in ("0", "1") for p in outs_all):   # tie cell
                for p in outs_all:
                    if p.name in pins:
                        consts[canon(pins[p.name])] = int(fn[p.name])
                        tie_cells[canon(pins[p.name])] = (libcell, p.name)
                continue
            if lc.seq is not None:
                flops.append(_flop_from_liberty(inst, libcell, lc, pins, canon))
                continue
        elif re.match(r"^conb_\d+$", base):        # tie cell without Liberty: HI = 1, LO = 0
            for pin, val in (("HI", 1), ("LO", 0)):
                if pin in pins:
                    consts[canon(pins[pin])] = val
                    tie_cells[canon(pins[pin])] = (libcell, pin)
            continue
        if lc is None and FLOP_RE.match(base):
            flops.append(Flop(inst, libcell, canon(pins["D"]), canon(pins["Q"]), canon(pins["CLK"])))
            continue
        kind = kind_of(libcell)
        if kind not in SUPPORTED_KINDS:
            if lib is None or libcell not in lib.cells:
                raise ValueError(f"unsupported cell {libcell} ({inst}); pass a Liberty library")
            lc = lib.cells[libcell]
            outs = [p for p in lc.pins.values() if p.direction == "output" and p.function]
            if len(outs) != 1:
                raise ValueError(f"cell {libcell} is not a single-output combinational cell")
            kind = "LIB:" + outs[0].function
            out_pins = [outs[0].name]
        else:
            out_pins = [p for p in pins if p in ("X", "Y")] or [
                p.name for p in getattr(lib.cells.get(libcell), "pins", {}).values()
                if p.direction == "output"] if lib is not None else [p for p in pins if p in ("X", "Y")]
        if len(out_pins) != 1:
            raise ValueError(f"cannot identify output pin of {inst}: {pins}")
        out = out_pins[0]
        if out not in pins:          # output left unconnected (e.g. CTS dummy load cells)
            continue
        ins = {p: canon(n) for p, n in pins.items() if p != out}
        cells.append(Cell(inst, kind, ins, canon(pins[out]), 1000, 1000,
                          library_cell=libcell, library_output_pin=out))

    # clock network: from clock ports through single-input buffers/inverters (CTS)
    roots = {i for i in inputs if i in clocks}
    if flops and not roots:
        # no clock port by name: walk back from the flop clock pins through single-input
        # cells (clock buffers / inverters) to the input ports that drive them
        drv = {c.output: c for c in cells}
        for f in flops:
            n_, seen = f.clk, set()
            while n_ in drv and len(drv[n_].inputs) == 1 and n_ not in seen:
                seen.add(n_); n_ = next(iter(drv[n_].inputs.values()))
            if n_ in inputs:
                roots.add(n_)
    tree = []
    if roots and flops:
        clock_nets, changed = set(roots), True
        while changed:
            changed = False
            for c in cells:
                if len(c.inputs) == 1 and next(iter(c.inputs.values())) in clock_nets and c.output not in clock_nets:
                    clock_nets.add(c.output); changed = True
        tree = [c for c in cells if len(c.inputs) == 1 and next(iter(c.inputs.values())) in clock_nets]
        missing = {f.clk for f in flops} - clock_nets
        if missing:
            raise ValueError(f"flop clock nets not reached from clock ports {sorted(roots)}: {sorted(missing)[:5]}")
        cells = [c for c in cells if c not in tree]
        clk_nets = sorted(roots)
    else:
        clk_nets = sorted({f.clk for f in flops} | roots)
    real_inputs = [i for i in inputs if i not in clk_nets]
    const_inputs = [n for n in consts if n not in real_inputs]
    flop_outs = [n for f in flops for n, _, _ in f.outputs if n not in real_inputs]
    comb_inputs = real_inputs + flop_outs + const_inputs
    # primary outputs driven through an alias keep the driving net name
    drivers = {c.output for c in cells} | {n for f in flops for n, _, _ in f.outputs}
    po, port_net = [], {}
    for o in outputs:
        co = canon(o)
        if co not in drivers and co not in real_inputs and co not in consts:
            # the PO itself may be the canonical driven net
            if o in drivers:
                co = o
            else:
                raise ValueError(f"undriven primary output {o}")
        po.append(co)
        port_net[o] = co
    comb_outputs = po + [f.d for f in flops if f.d not in po]
    init = {pi: initial_value for pi in comb_inputs}
    init.update(consts)
    for f in flops:                       # state 0 after reset: Q = 0, QN = 1
        for n, _, inv in f.outputs:
            init[n] = inv
    net = Network(comb_inputs, comb_outputs, cells, init)
    return Design(net, flops, real_inputs, po, clk_nets, module=m.group(1), input_ports=list(inputs),
                  output_ports=list(outputs), port_net=port_net, tie_cells=tie_cells, clock_tree=tree)


def _flop_from_liberty(inst, libcell, lc, pins, canon):
    seq = lc.seq
    if seq["kind"] != "ff":
        raise ValueError(f"{inst} ({libcell}): latches are not supported yet")
    clk = seq.get("clocked_on", "")
    nxt = seq.get("next_state", "")
    if not re.fullmatch(r"[A-Za-z_]\w*", clk):
        raise ValueError(f"{inst} ({libcell}): only rising-edge flip-flops are supported (clocked_on: {clk})")
    if not re.fullmatch(r"[A-Za-z_]\w*", nxt):
        raise ValueError(f"{inst} ({libcell}): next_state '{nxt}' not supported (scan / enable flops: use plain DFFs)")
    st = seq.get("state", ("IQ", "IQN"))
    q_pin = qn_pin = None
    for p in lc.pins.values():
        if p.direction != "output":
            continue
        f = (p.function or "").replace(" ", "").strip('"')
        if f == st[0]:
            q_pin = p.name
        elif (len(st) > 1 and f == st[1]) or f == "!" + st[0]:
            qn_pin = p.name
    ctrl = {}
    for key in ("clear", "preset"):
        for pin in re.findall(r"[A-Za-z_]\w*", seq.get(key, "")):
            if pin in pins:
                ctrl[pin] = canon(pins[pin])
    q = canon(pins[q_pin]) if q_pin and q_pin in pins else None
    qn = canon(pins[qn_pin]) if qn_pin and qn_pin in pins else None
    if q is None and qn is None:
        raise ValueError(f"{inst} ({libcell}): no connected state output")
    return Flop(inst, libcell, canon(pins[nxt]), q, canon(pins[clk]), qn=qn, d_pin=nxt, clk_pin=clk,
                q_pin=q_pin, qn_pin=qn_pin, clear=seq.get("clear"), preset=seq.get("preset"), ctrl=ctrl)
