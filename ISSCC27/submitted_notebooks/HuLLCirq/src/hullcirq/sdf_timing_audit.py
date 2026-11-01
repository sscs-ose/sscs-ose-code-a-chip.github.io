"""Independent signed timing and capture audit for one finite recorded trace.

This is not a general implementation of Verilog's nine-argument setuphold.
The supported model is the original SKY130 dfxtp_2 with separate signed
SETUP/HOLD records and CLK WIDTH/IOPATH records, on a one-picosecond grid.
Original signed windows are never clamped.  A deliberately stronger trace
qualification requires D to remain constant from the earliest original setup
boundary through the actual adapter capture point.  That proves the observed
capture value agrees with the stable original timing-window value; it does not
prove arbitrary traces, notifier/X behaviour on a violation, or pulse rules.

IEEE 1364-2005 sections 15.5.1, 15.5.3, 15.8 and 16.2.2 are the semantic basis:
https://www.csie.nuk.edu.tw/~stpan/course/Verilog1964-2005.pdf .
The independent circuit evidence is always the caller's original SDF and VCD.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re

from .sdf_interconnect import parse_sdf, _children, _one


class TimingAuditError(ValueError):
    """An input cannot be audited without guessing timing semantics."""


def _need(condition, message):
    if not condition:
        raise TimingAuditError(message)


def _value_ps(node, selection):
    _need(isinstance(node, list) and len(node) == 1 and isinstance(node[0], str),
          "Require scalar timing value")
    values = node[0].split(":")
    _need(len(values) in (1, 3) and all(values), "Require complete timing triple")
    try:
        parsed = [Decimal(value) * 1000 for value in values]
    except InvalidOperation as error:
        raise TimingAuditError("Invalid timing value") from error
    _need(all(value.is_finite() and value == value.to_integral_value() for value in parsed),
          "Timing values must be finite exact integer picoseconds; no rounding")
    return int(parsed[0] if len(parsed) == 1 else parsed[{"min": 0, "typ": 1, "max": 2}[selection]])


def timing_records(sdf_text, *, selection="typ"):
    """Return all supported sequential records, or reject incomplete coverage."""
    _need(selection in ("min", "typ", "max"), "Unknown timing selection")
    root = parse_sdf(sdf_text)
    _need(_one(root, "TIMESCALE")[1:] == ["1ns"], "Require exact 1ns SDF timescale")
    records, seen = [], set()
    for cell in _children(root, "CELL"):
        checks = _children(cell, "TIMINGCHECK")
        celltype = _one(cell, "CELLTYPE")[1:]
        if not checks:
            _need(celltype != ['"sky130_fd_sc_hd__dfxtp_2"'],
                  "Sequential CELL is missing original timing checks")
            continue
        _need(len(checks) == 1, "Duplicate TIMINGCHECK section")
        _need(celltype == ['"sky130_fd_sc_hd__dfxtp_2"'],
              "Only original dfxtp_2 sequential timing is qualified")
        instance = _one(cell, "INSTANCE")
        _need(len(instance) == 2 and isinstance(instance[1], str)
              and re.fullmatch(r"[A-Za-z_$][\w$]*", instance[1]),
              "Require flat unescaped sequential instance")
        name = instance[1]
        _need(name not in seen, "Duplicate timing instance")
        seen.add(name)
        values, width = {}, {}
        for check in checks[0][1:]:
            _need(isinstance(check, list) and bool(check), "Malformed timing check")
            kind = check[0]
            if kind in ("SETUP", "HOLD"):
                _need(len(check) == 4 and check[1] in (["posedge", "D"], ["negedge", "D"])
                      and check[2] == ["posedge", "CLK"], "Unsupported signed timing event")
                key = (kind, check[1][0])
                _need(key not in values, "Duplicate signed timing event")
                values[key] = _value_ps(check[3], selection)
            elif kind == "WIDTH":
                _need(len(check) == 3 and check[1] in (["posedge", "CLK"], ["negedge", "CLK"]),
                      "Unsupported WIDTH event")
                edge = check[1][0]
                _need(edge not in width, "Duplicate WIDTH event")
                width[edge] = _value_ps(check[2], selection)
            else:
                raise TimingAuditError("Uncovered timing construct: " + str(kind))
        _need(set(values) == {(kind, edge) for kind in ("SETUP", "HOLD")
                              for edge in ("posedge", "negedge")}
              and set(width) == {"posedge", "negedge"}, "Incomplete signed/WIDTH coverage")
        pairs = {edge: {"setup_ps": values["SETUP", edge], "hold_ps": values["HOLD", edge]}
                 for edge in ("posedge", "negedge")}
        _need(all(pair["setup_ps"] > 0 and pair["hold_ps"] < 0
                  and pair["setup_ps"] + pair["hold_ps"] > 1 for pair in pairs.values())
              and all(value > 0 for value in width.values()),
              "Require positive SETUP, negative HOLD and nondegenerate original windows")
        delay = _one(cell, "DELAY")
        absolute = _one(delay, "ABSOLUTE")
        _need(len(delay) == 2 and len(absolute) == 2, "Sequential IOPATH coverage must be exact")
        arc = absolute[1]
        _need(len(arc) == 5 and arc[:3] == ["IOPATH", "CLK", "Q"], "Require original CLK Q IOPATH")
        rise, fall = _value_ps(arc[3], selection), _value_ps(arc[4], selection)
        _need(rise >= 0 and fall >= 0, "Negative CLK Q delay unsupported")
        records.append({"instance": name, "pairs": pairs, "width_ps": width,
                        "q_rise_ps": rise, "q_fall_ps": fall})
    def count(node, name):
        return (int(bool(node) and node[0] == name) +
                sum(count(item, name) for item in node if isinstance(item, list)))
    _need(records and count(root, "TIMINGCHECK") == len(records)
          and all(count(root, kind) == 2 * len(records) for kind in ("SETUP", "HOLD", "WIDTH")),
          "Missing or uncovered original timing records")
    return records


def _read_vcd(path, required_paths):
    """Stream scalar VCD, retaining all value changes of the required signals.

    Same-time changes are retained, so a pulse within one timestamp cannot be
    erased by keeping only the last value. VCD lacks delta-cycle ordering;
    same-timestamp capture uncertainty therefore fails the stability guard.
    """
    scopes, paths, traces = [], {}, {}
    time_ps, multiplier, in_header = 0, None, True
    initial_dump = set()
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for raw in handle:
            digest.update(raw)
            line = raw.decode("ascii").strip()
            if not line:
                continue
            if in_header:
                while "$end" not in line:
                    following = handle.readline()
                    _need(bool(following), "Truncated VCD header")
                    digest.update(following)
                    line += " " + following.decode("ascii").strip()
                tokens = line.split()
                command = tokens[0]
                if command == "$scope":
                    _need(len(tokens) == 4, "Malformed VCD scope")
                    scopes.append(tokens[2])
                elif command == "$upscope":
                    _need(bool(scopes), "Unbalanced VCD scopes")
                    scopes.pop()
                elif command == "$var":
                    _need(len(tokens) >= 6, "Malformed VCD var")
                    reference = tokens[4].removeprefix("\\")
                    name = ".".join(scopes + [reference])
                    if name in required_paths:
                        _need(name not in paths, "Duplicate required VCD path")
                        _need(tokens[2] == "1", "Timing audit requires scalar pin signals")
                        paths[name] = tokens[3]
                        traces.setdefault(tokens[3], [])
                elif command == "$timescale":
                    spec = "".join(tokens[1:-1])
                    match = re.fullmatch(r"(1|10|100)(s|ms|us|ns|ps|fs)", spec)
                    _need(match is not None and multiplier is None, "Invalid/duplicate VCD timescale")
                    units = {"s": 10**12, "ms": 10**9, "us": 10**6, "ns": 1000, "ps": 1}
                    _need(match[2] in units, "Sub-picosecond VCD precision unsupported")
                    multiplier = int(match[1]) * units[match[2]]
                    _need(multiplier == 1, "Require one-picosecond VCD precision")
                elif command == "$enddefinitions":
                    _need(multiplier is not None and not scopes, "Incomplete VCD header")
                    in_header = False
                continue
            if line.startswith("#"):
                _need(re.fullmatch(r"#[0-9]+", line) is not None, "Invalid VCD timestamp")
                current = int(line[1:]) * multiplier
                _need(current >= time_ps, "VCD time moved backwards")
                time_ps = current
                continue
            if line.startswith("$"):
                _need(line in ("$dumpvars", "$dumpall", "$end", "$comment") or line.startswith("$comment "),
                      "VCD dump suspension or unsupported directive")
                continue
            if line[0] in "01xXzZ":
                value, code = line[0].lower(), line[1:]
            elif line[0] in "bB":
                tokens = line.split()
                _need(len(tokens) == 2, "Malformed VCD binary value")
                value, code = tokens[0][1:].lower(), tokens[1]
            else:
                continue
            if code not in traces:
                continue
            _need(value in ("0", "1", "x", "z"), "Required scalar pin has nonscalar VCD value")
            if time_ps == 0:
                initial_dump.add(code)
            trace = traces[code]
            if not trace or trace[-1][1] != value:
                trace.append((time_ps, value))
    _need(not in_header and multiplier is not None, "Missing VCD enddefinitions")
    missing = sorted(required_paths - paths.keys())
    _need(not missing, "Missing required VCD pins: " + ", ".join(missing[:12]))
    _need(all(code in initial_dump for code in traces), "Required VCD pin lacks time-zero initial dump")
    return paths, traces, time_ps, digest.hexdigest()


def _edges(before, after):
    """IEEE posedge/negedge four-state classes, treating z like x."""
    before, after = before.replace("z", "x"), after.replace("z", "x")
    result = []
    if (before, after) in (("0", "1"), ("0", "x"), ("x", "1")):
        result.append("posedge")
    if (before, after) in (("1", "0"), ("1", "x"), ("x", "0")):
        result.append("negedge")
    return result


def _at(trace, times, at):
    index = bisect_right(times, at) - 1
    return None if index < 0 else trace[index][1]


def audit_sdf_timing(sdf_text, vcd_path, *, dut_scope="tb.dut", offset_ps=0, selection="typ",
                     qualify_initial_clock_settlement=False, source_clock_path=None):
    """Audit every observed sequential capture; no startup/reset-cycle exclusion.

    offset_ps is an exact nonnegative integer, or a complete instance->integer
    mapping. Current zero-offset copy adapters must pass zero explicitly.
    Constant X/Z data is recorded and compared using the original UDP's X
    capture semantics; unknown clocks and changed capture windows never pass.
    An explicit opt-in can qualify only the initial X->0 clock-tree settlement:
    the named source clock must start at zero and remain zero through the
    settlement, before its first binary rising edge; the local clock has exactly
    that X->0 prefix, Q remains X before capture, and delayed clock is identical.
    This is a separately reported four-state startup proof, never a skipped
    reset cycle. The caller must bind the original clk=0 declaration/TB hash.
    A Failed result means an observed contradiction, Unsupported means missing
    or ambiguous evidence, and Passed is finite-trace qualification only.
    """
    report = {"kind": "hullcirq-sdf-finite-trace-timing-audit-v1", "status": "Unsupported",
              "scope": "one_recorded_trace_not_general_9_argument_timing_model_equivalence",
              "sdf_sha256": hashlib.sha256(sdf_text.encode("utf-8")).hexdigest(),
              "vcd_sha256": None, "dut_scope": dut_scope, "selection": selection,
              "ignored_startup_or_reset_cycles": 0, "notifier_violation_semantics_qualified": False,
              "startup_settlement_opt_in": qualify_initial_clock_settlement,
              "source_clock_path": source_clock_path,
              "capture_window": "closed union from C-max(S) through actual capture; original signed windows open",
              "counts": {"timing_cells": 0, "mapped_cells": 0, "required_pins": 0,
                         "signed_pairs": 0, "width_records": 0, "clock_captures": 0,
                         "signed_violations": 0, "width_violations": 0,
                         "capture_qualified": 0, "capture_unqualified": 0,
                         "constant_unknown_captures": 0, "initial_unknown_q": 0,
                         "unknown_clock_events": 0, "delayed_data_mismatches": 0,
                         "delayed_clock_mismatches": 0,
                         "qualified_initial_clock_settlements": 0,
                         "q_mismatches": 0, "q_checks": 0},
              "diagnostics": [], "cells": []}
    counts = report["counts"]
    failures, unsupported = [], []
    try:
        _need(isinstance(dut_scope, str) and re.fullmatch(r"[\w$]+(?:\.[\w$]+)*", dut_scope) is not None,
              "Invalid DUT scope")
        _need(type(qualify_initial_clock_settlement) is bool, "Startup settlement opt-in must be boolean")
        _need(not qualify_initial_clock_settlement
              or isinstance(source_clock_path, str) and re.fullmatch(r"[\w$]+(?:\.[\w$]+)*", source_clock_path),
              "Explicit startup qualification requires the original source-clock path")
        records = timing_records(sdf_text, selection=selection)
        counts.update(timing_cells=len(records), required_pins=5 * len(records),
                      signed_pairs=2 * len(records), width_records=2 * len(records))
        names = {record["instance"] for record in records}
        if type(offset_ps) is int:
            _need(offset_ps >= 0, "Negative delayed-data offset")
            offsets = dict.fromkeys(names, offset_ps)
        else:
            _need(type(offset_ps) is dict and set(offset_ps) == names
                  and all(type(value) is int and value >= 0 for value in offset_ps.values()),
                  "Require exact offset for every timing instance")
            offsets = offset_ps
        required_pins = ("D", "CLK", "D_delayed", "CLK_delayed", "Q")
        required = {f"{dut_scope}.{name}.{pin}" for name in names for pin in required_pins}
        if qualify_initial_clock_settlement:
            required.add(source_clock_path)
        vcd_path = Path(vcd_path)
        paths, traces, end, observed_sha = _read_vcd(vcd_path, required)
        report["vcd_sha256"] = observed_sha
        report["end_time_ps"] = end
        counts["mapped_cells"] = len(records)
        times = {code: [item[0] for item in trace] for code, trace in traces.items()}
        report["offset_ps"] = offset_ps
        source, first_source_posedge = None, None
        if qualify_initial_clock_settlement:
            source = traces[paths[source_clock_path]]
            first_source_posedge = next((time for index, (time, value) in enumerate(source)
                                         if index and source[index - 1][1] == "0" and value == "1"), None)
            _need(source[0] == (0, "0") and first_source_posedge is not None
                  and all(value == "0" for time, value in source if time < first_source_posedge),
                  "Original source clock must begin at zero without unknown pre-rising transitions")
            report["startup_source_first_posedge_ps"] = first_source_posedge
        for record in records:
            name = record["instance"]
            pins = {pin: paths[f"{dut_scope}.{name}.{pin}"] for pin in required_pins}
            d, clk, delayed, q = (traces[pins[pin]] for pin in ("D", "CLK", "D_delayed", "Q"))
            dt, ct, ddt, qt = (times[pins[pin]] for pin in ("D", "CLK", "D_delayed", "Q"))
            offset = offsets[name]
            cell = {**record, "offset_ps": offset,
                    "vcd_paths": {pin: f"{dut_scope}.{name}.{pin}" for pin in pins},
                    "vcd_codes": pins, "captures": 0, "qualified": 0,
                    "unqualified": 0, "unknown_captures": 0}
            report["cells"].append(cell)
            counts["initial_unknown_q"] += int(q[0][1] in ("x", "z"))
            first_local_posedge = next((time for index, (time, value) in enumerate(clk)
                                        if index and clk[index - 1][1] == "0" and value == "1"), None)
            startup_qualified = bool(
                qualify_initial_clock_settlement and len(clk) > 1
                and clk[0] == (0, "x") and clk[1][1] == "0"
                and 0 < clk[1][0] < first_source_posedge
                and first_local_posedge is not None
                and all(value == "0" for time, value in source if time <= clk[1][0])
                and q[0] == (0, "x")
                and all(value == "x" for time, value in q if time < first_local_posedge)
                and traces[pins["CLK_delayed"]] == clk)
            cell["startup_settlement_qualified"] = startup_qualified
            if startup_qualified:
                counts["qualified_initial_clock_settlements"] += 1
                cell["startup_settlement_ps"] = clk[1][0]
            elif clk[0][1] not in ("0", "1"):
                counts["unknown_clock_events"] += 1
                unsupported.append({"code": "unknown_initial_clock", "instance": name, "time_ps": 0})
            data_edges = []
            for index in range(1, len(d)):
                for edge in _edges(d[index - 1][1], d[index][1]):
                    data_edges.append((d[index][0], edge))
            de_times = [event[0] for event in data_edges]
            previous_edge = {}
            # A scalar continuous copy at offset zero must preserve every
            # observable time/value change, including same-time transients.
            expected_delayed = [(time + offset, value) for time, value in d if time + offset <= end]
            if offset:
                expected_delayed.insert(0, (0, "x"))
                expected_delayed = [item for i, item in enumerate(expected_delayed)
                                    if not i or expected_delayed[i - 1][1] != item[1]]
            if delayed != expected_delayed:
                counts["delayed_data_mismatches"] += 1
                failures.append({"code": "delayed_data_copy_mismatch", "instance": name})
            if traces[pins["CLK_delayed"]] != clk:
                counts["delayed_clock_mismatches"] += 1
                failures.append({"code": "delayed_clock_copy_mismatch", "instance": name})
            for index in range(1, len(clk)):
                c, value = clk[index]
                before = clk[index - 1][1]
                if value not in ("0", "1") or before not in ("0", "1"):
                    if startup_qualified and index == 1:
                        # X->0 is an IEEE negedge. Its timestamp starts the
                        # first low-pulse WIDTH check; no posedge is excluded.
                        previous_edge["negedge"] = c
                        continue
                    counts["unknown_clock_events"] += 1
                    unsupported.append({"code": "unknown_clock_transition", "instance": name, "time_ps": c})
                    continue
                edge = "posedge" if value == "1" else "negedge"
                opposite = "negedge" if edge == "posedge" else "posedge"
                if opposite in previous_edge:
                    width = c - previous_edge[opposite]
                    if 0 < width < record["width_ps"][opposite]:
                        counts["width_violations"] += 1
                        failures.append({"code": "width_violation", "instance": name, "time_ps": c,
                                         "edge": opposite, "observed_ps": width,
                                         "limit_ps": record["width_ps"][opposite]})
                    elif width == 0:
                        unsupported.append({"code": "same_timestamp_clock_pulse", "instance": name, "time_ps": c})
                previous_edge[edge] = c
                if edge != "posedge":
                    continue
                counts["clock_captures"] += 1
                cell["captures"] += 1
                for polarity, pair in record["pairs"].items():
                    left, right = c - pair["setup_ps"], c + pair["hold_ps"]
                    for data_time, data_edge in data_edges[bisect_right(de_times, left):bisect_left(de_times, right)]:
                        if data_edge == polarity:
                            counts["signed_violations"] += 1
                            failures.append({"code": "signed_setuphold_violation", "instance": name,
                                             "clock_ps": c, "data_ps": data_time, "edge": polarity,
                                             "setup_ps": pair["setup_ps"], "hold_ps": pair["hold_ps"],
                                             "open_window_ps": [left, right]})
                lower = min(c - max(pair["setup_ps"] for pair in record["pairs"].values()), c - offset)
                upper = max(c, c - offset)
                start = bisect_left(dt, lower)
                stop = bisect_right(dt, upper)
                # The initial dump defines the state, rather than a transition.
                changes = [event for i, event in enumerate(d[start:stop], start) if i > 0]
                stable = _at(d, dt, lower)
                observed = _at(delayed, ddt, c)
                if lower < 0 or stable is None or changes or observed != stable:
                    counts["capture_unqualified"] += 1
                    cell["unqualified"] += 1
                    unsupported.append({"code": "capture_window_unqualified", "instance": name,
                                        "clock_ps": c, "closed_window_ps": [lower, upper],
                                        "value": stable, "delayed_value": observed,
                                        "changes": changes, "starts_before_trace": lower < 0})
                    continue
                counts["capture_qualified"] += 1
                cell["qualified"] += 1
                if stable in ("x", "z"):
                    counts["constant_unknown_captures"] += 1
                    cell["unknown_captures"] += 1
                expected = "x" if stable in ("x", "z") else stable
                if expected == "1":
                    delay = record["q_rise_ps"]
                elif expected == "0":
                    delay = record["q_fall_ps"]
                else:
                    # For a 0/1->X transition the two-value specify mapping uses
                    # min(rise,fall). Check its settled value after both possible
                    # deadlines; this does not prove the exact X-arrival time.
                    delay = max(record["q_rise_ps"], record["q_fall_ps"])
                deadline = c + delay
                if deadline > end:
                    unsupported.append({"code": "trace_ends_before_q_deadline", "instance": name,
                                        "clock_ps": c, "deadline_ps": deadline})
                    continue
                counts["q_checks"] += 1
                actual = _at(q, qt, deadline)
                if actual != expected:
                    counts["q_mismatches"] += 1
                    failures.append({"code": "q_capture_mismatch", "instance": name, "clock_ps": c,
                                     "deadline_ps": deadline, "expected": expected, "actual": actual})
            if not cell["captures"]:
                unsupported.append({"code": "no_observed_capture", "instance": name})
        report["diagnostics"] = failures + unsupported
        report["status"] = "Failed" if failures else "Unsupported" if unsupported else "Passed"
        report["failure_count"] = len(failures)
        report["unsupported_count"] = len(unsupported)
    except (TimingAuditError, ValueError, OSError, UnicodeError) as error:
        report["diagnostics"].append({"code": "timing_audit_input_unsupported", "message": str(error)})
        report["failure_count"] = len(failures)
        report["unsupported_count"] = len(unsupported) + 1
    return report
