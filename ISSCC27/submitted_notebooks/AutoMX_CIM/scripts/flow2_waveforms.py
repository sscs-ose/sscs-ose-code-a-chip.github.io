"""Read real ngspice ASCII raw files and evaluate aligned, nonloading probes.

No simulator is called by this module. A gate witness is computed at the
same saved time in every vector, never from maxima reached at different times.
"""
from __future__ import annotations

from pathlib import Path
import math
import re

import numpy as np


def completed_run_log(log: str, *, phase: str) -> tuple[str, dict]:
    """Select the run that produced the raw file, excluding a later batch run.

    ngspice -b may run .tran again after .control returns. The exported raw
    belongs to the explicit run before RUN_RETURNED, not to that later run.
    Ambiguous/missing markers fail closed rather than choosing a result.
    """
    if not re.fullmatch(r"[A-Z0-9_]+", phase):
        raise ValueError("invalid waveform phase")
    positions = {}
    for name in ("RUN_ENTER", "RUN_RETURNED", "RAW_WRITTEN"):
        found = list(re.finditer(rf"(?m)^AUTOMX_{phase}_PHASE={name}\s*$", log))
        if len(found) != 1:
            raise ValueError(f"missing or ambiguous waveform marker: {name}")
        positions[name] = found[0]
    if not (positions["RUN_ENTER"].start() < positions["RUN_RETURNED"].start()
            < positions["RAW_WRITTEN"].start()):
        raise ValueError("waveform markers are out of order")
    selected = log[:positions["RUN_RETURNED"].end()]
    count = len(re.findall(r"(?m)^\s*Measurements for Transient Analysis\s*$", selected))
    if count != 1:
        raise ValueError("expected exactly one measurement block for the exported waveform")
    return selected, {"source": "EXPLICIT_CONTROL_RUN_THAT_WROTE_RAW",
        "selected_measurement_blocks": count,
        "excluded_later_measurement_blocks": len(re.findall(
            r"(?m)^\s*Measurements for Transient Analysis\s*$", log[positions["RAW_WRITTEN"].end():])),
        "scope": "later automatic batch runs are retained in the log but not mixed with this raw"}


def read_raw(path: Path) -> dict[str, np.ndarray]:
    """Read the single real transient plot written by ``set filetype=ascii``.

    Reject incomplete, complex, binary, duplicate and nonfinite evidence.
    Bounds prevent a corrupt header from allocating an unbounded array.
    """
    with Path(path).open(encoding="utf-8", errors="strict") as stream:
        headers = {}
        for line in stream:
            key, sep, value = line.partition(":")
            if not sep:
                raise ValueError("invalid raw header")
            key = key.strip().lower()
            if key == "variables":
                break
            headers[key] = value.strip()
        else:
            raise ValueError("raw file has no variable table")
        if headers.get("flags", "").split() != ["real"]:
            raise ValueError("a real ASCII raw plot is required")
        if "transient" not in headers.get("plotname", "").lower():
            raise ValueError("a transient plot is required")
        try:
            nv, np_ = int(headers["no. variables"]), int(headers["no. points"])
        except (KeyError, ValueError) as error:
            raise ValueError("invalid raw dimensions") from error
        if not 2 <= nv <= 256 or not 2 <= np_ <= 5_000_000 or nv*np_ > 10_000_000:
            raise ValueError("raw dimensions exceed the diagnostic limits")
        names = []
        for index in range(nv):
            parts = stream.readline().split()
            if len(parts) != 3 or parts[0] != str(index):
                raise ValueError("invalid raw variable index")
            names.append(parts[1].lower())
        if len(names) != len(set(names)) or names[0] != "time":
            raise ValueError("raw variables must be unique and start with time")
        if stream.readline().strip().lower() != "values:":
            raise ValueError("raw data must use ASCII Values, not Binary")
        values = np.empty((np_, nv), dtype=float)
        for point in range(np_):
            for var in range(nv):
                line = stream.readline()
                # ngspice 31 writes a blank separator after every complete
                # point. Skip separators only here, never within its values:
                # a missing scalar must still be treated as truncated data.
                if var == 0:
                    while line and not line.strip():
                        line = stream.readline()
                parts = line.split()
                if var == 0:
                    if len(parts) != 2 or parts[0] != str(point):
                        raise ValueError("missing or unordered raw point")
                    item = parts[1]
                else:
                    if len(parts) != 1:
                        raise ValueError("truncated raw point")
                    item = parts[0]
                try:
                    values[point, var] = float(item)
                except ValueError as error:
                    raise ValueError("invalid raw scalar") from error
        if stream.read().strip():
            raise ValueError("unexpected second plot or trailing raw data")
    if not np.isfinite(values).all() or not np.all(np.diff(values[:, 0]) > 0):
        raise ValueError("raw values must be finite with increasing time")
    return {name: values[:, i] for i, name in enumerate(names)}


def sample(vectors: dict, name: str, at_s: float) -> float:
    key = name.lower()
    if key not in vectors or not math.isfinite(at_s):
        raise ValueError(f"missing waveform or invalid sample: {name}")
    time = vectors["time"]
    tolerance = max(1e-21, abs(float(time[-1]))*1e-12)
    if not time[0]-tolerance <= at_s <= time[-1]+tolerance:
        raise ValueError(f"sample outside measured time: {name}")
    return float(np.interp(min(max(at_s, time[0]), time[-1]), time, vectors[key]))


def sampling_witness(vectors: dict, probes: dict, *, start_s=8e-9, stop_s=12e-9,
                     high_v=1.62, low_v=.18) -> dict:
    if not 0 <= start_s < stop_s or not low_v < high_v:
        raise ValueError("invalid witness window or rails")
    time = vectors["time"]
    if time[0] > start_s or time[-1] < stop_s:
        raise ValueError("gate waveforms do not cover the witness window")
    selected = (time >= start_s) & (time <= stop_s)
    if np.count_nonzero(selected) < 2:
        raise ValueError("not enough aligned gate samples")
    margins = []
    for group in probes["input_switches"].values():
        for device in group:
            key = f"v(xadc.{device['gate']})".lower()
            if key not in vectors:
                raise ValueError(f"missing gate waveform: {key}")
            v = vectors[key][selected]
            margins.append(v-high_v if "__nfet_" in device["primitive"] else low_v-v)
    if len(margins) != 16:
        raise ValueError("the pinned ADC needs 16 input gate probes")
    simultaneous = np.min(np.asarray(margins), axis=0)
    best = int(np.argmax(simultaneous))
    return {"source": "POSTPROCESS_ALIGNED_RAW_GATE_SAMPLES",
            "window_s": [start_s, stop_s], "sample_count": int(np.count_nonzero(selected)),
            "sampling_command_margin_v": float(simultaneous[best]),
            "witness_time_s": float(time[selected][best]),
            "sampling_command_on_witnessed": bool(simultaneous[best] >= 0),
            "interpretation": "a sampled simultaneous gate command witness, not a continuous aperture or conversion proof"}


def control_block(vectors: list[str], *, filename="probe.raw", phase="PROBE") -> str:
    if not re.fullmatch(r"[A-Za-z0-9_]+\.raw", filename) or not re.fullmatch(r"[A-Z0-9_]+", phase):
        raise ValueError("unsafe raw filename or phase marker")
    names = list(dict.fromkeys(vectors))
    if not names or any(not re.fullmatch(r"[vi]\([^\s\n;]+\)", name, re.I) for name in names):
        raise ValueError("invalid waveform vector")
    return "\n".join([".control", "set filetype=ascii", "set numdgt=17",
        f"echo AUTOMX_{phase}_PHASE=DECK_PARSED", "rusage",
        f"echo AUTOMX_{phase}_PHASE=RUN_ENTER", "run",
        f"echo AUTOMX_{phase}_PHASE=RUN_RETURNED",
        f"write {filename} {' '.join(names)}", "rusage",
        f"echo AUTOMX_{phase}_PHASE=RAW_WRITTEN", ".endc"])
