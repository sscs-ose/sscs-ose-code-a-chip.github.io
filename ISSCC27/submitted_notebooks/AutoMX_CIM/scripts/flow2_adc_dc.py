"""PDK/model gates for the full-active ADC DC recovery experiment."""
from __future__ import annotations

import math
from pathlib import Path
import re

from automx_cim.spice import parse_measurements


def modelled_resistors(text):
    cards = [line for line in text.splitlines() if re.match(r"(?i)^R\S+\s", line)
             and "sky130_fd_pr__res_generic_po" in line]
    if len(cards) != 8 or any(len(c.split()) < 6 for c in cards):
        raise ValueError("the pinned ADC needs eight complete modeled poly-resistor cards")
    return cards


def model_deck(model: Path, resistors):
    lines = [".title TT generic-poly model parser/conductance smoke",
        f'.lib "{model.as_posix()}" tt', ".temp 25", ".option klu reltol=1e-6"]
    expressions = []
    for i, raw in enumerate(resistors):
        fields = raw.split()
        for polarity, voltage in (("pos", ".001"), ("neg", "-.001")):
            node, source = f"probe_{polarity}_{i}", f"VCHK_{polarity}_{i}"
            lines += [f"{source} {node} 0 {voltage}",
                f"RCHK_{polarity}_{i} {node} 0 {' '.join(fields[3:])}"]
            expressions += [f"let r_{polarity}_{i} = abs({voltage}/i({source}))",
                            f"print r_{polarity}_{i}"]
    lines += [".control", "echo AUTOMX_ADC_MODEL_PHASE=DECK_PARSED", "rusage", "op",
        "echo AUTOMX_ADC_MODEL_PHASE=SOLVE_RETURNED", *expressions,
        "echo AUTOMX_ADC_MODEL_PHASE=DONE", "rusage", "quit", ".endc", ".end", ""]
    return "\n".join(lines)


def simulator_errors(log):
    return re.findall(r"(?im)^.*(?:unrecognized parameter|unknown parameter|model issue on line|\bError:|\bFatal:).*$", log)


def require_klu(log):
    if not re.search(r"(?i)Using\s+KLU\b", log):
        raise ValueError("KLU was not observed as the selected solver; compiled-with-KLU is insufficient")
    errors = simulator_errors(log)
    if errors:
        raise ValueError("PDK/simulator parsing failed: "+errors[0].strip())


def analyze_model(log):
    require_klu(log)
    if "AUTOMX_ADC_MODEL_PHASE=DONE" not in log or "singular matrix" in log.lower():
        raise ValueError("the isolated resistor-model DC solve did not complete cleanly")
    keys = [f"r_{polarity}_{i}" for i in range(8) for polarity in ("pos", "neg")]
    values = parse_measurements(log, keys)
    if set(values) != set(keys) or any(not math.isfinite(v) or not 1e-6 < v < 1e12 for v in values.values()):
        raise ValueError("missing/nonphysical modeled-resistor conductance measurements")
    for i in range(8):
        if abs(values[f"r_pos_{i}"]/values[f"r_neg_{i}"]-1) > 1e-4:
            raise ValueError("generic-poly resistor polarity symmetry check failed")
    return {"status": "MEASURED_PDK_POLY_PARSE_CONDUCTANCE_SMOKE", "resistance_ohms": values,
        "scope": "TT +/-1mV positive conductance and parser smoke only; no ADC conversion or PVT claim"}
