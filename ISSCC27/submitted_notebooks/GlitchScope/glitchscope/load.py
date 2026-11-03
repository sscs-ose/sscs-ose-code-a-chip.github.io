from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class NetLoadBreakdown:
    sink_pin_cap_ff: float
    wire_cap_ff: float
    primary_output_load_ff: float
    total_ff: float

def _nonnegative_map(name, values):
    out = {}
    for net, value in dict(values or {}).items():
        q = float(value)
        if q < 0.0:
            raise ValueError(f"{name} must be nonnegative: net={net} value={q}")
        out[net] = q
    return out

def derive_net_loads(network, liberty, wire_cap_ff_by_net=None,
                     primary_output_load_ff_by_net=None):
    """Derive deterministic capacitive loads from downstream Liberty input pins.

    total_load(net) =
        sum(input-pin capacitances of all sink pins on net)
      + optional wire capacitance
      + optional external load for primary-output nets.

    B2 deliberately does not infer interconnect capacitance from geometry.
    Optional wire capacitance is an explicit user/model input.
    """
    wire = _nonnegative_map("wire capacitance", wire_cap_ff_by_net)
    po = _nonnegative_map("primary-output load", primary_output_load_ff_by_net)

    primary_outputs = set(network.primary_outputs)
    bad_po = sorted(set(po) - primary_outputs)
    if bad_po:
        raise ValueError(
            "primary_output_load_ff_by_net contains non-primary-output nets: "
            + ",".join(bad_po)
        )

    sink = defaultdict(float)
    all_nets = set(network.primary_inputs) | set(network.primary_outputs)

    for cell in network.cells:
        all_nets.add(cell.output)
        libname = cell.library_cell or cell.kind
        if libname not in liberty.cells:
            raise KeyError(
                f"Liberty cell not found while deriving load: {cell.name} -> {libname}"
            )
        lc = liberty.cells[libname]

        for pin, net in cell.inputs.items():
            all_nets.add(net)
            if pin not in lc.pins:
                raise KeyError(
                    f"Liberty pin not found while deriving load: "
                    f"instance={cell.name} cell={libname} pin={pin}"
                )
            lp = lc.pins[pin]
            if lp.direction not in ("input", "inout"):
                raise ValueError(
                    f"Connected sink pin is not an input: "
                    f"instance={cell.name} cell={libname} pin={pin} "
                    f"direction={lp.direction}"
                )
            if lp.capacitance_ff is None:
                raise ValueError(
                    f"Missing input-pin capacitance: "
                    f"instance={cell.name} cell={libname} pin={pin}"
                )
            sink[net] += float(lp.capacitance_ff)

    all_nets |= set(wire) | set(po)
    out = {}
    for net in sorted(all_nets):
        s = float(sink.get(net, 0.0))
        w = float(wire.get(net, 0.0))
        p = float(po.get(net, 0.0))
        out[net] = NetLoadBreakdown(s, w, p, s + w + p)
    return out
