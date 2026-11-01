"""Conservative whole-event audit of the pinned SKY130 dfxtp_2 subset.

This new auditor leaves the historical VCD/deadline auditor unchanged. A VPI
callback sequence is an invocation order, never a delta-cycle/region number.
Every recorded Q transition is checked, including pulses between captures.
The signed timing windows retain their original negative HOLD values.

Supported capture proof: D is constant on the closed union [C-max(SETUP), C]
and the observed delayed pins are zero-offset copies. For each original pair,
any admissible data-minus-reference offset delta satisfies -H <= delta <= S,
so its original input sample lies inside that union. This is a finite stable
trace argument, not an implementation of arbitrary nine-argument setuphold.
There need not be a shared offset for the two polarities; this is reported.

Q rules come from the original PDK dfxtp_2 timing module and udp_dff$P_pp$PG$N
table. Two-value *module path* expansion is used, not primitive delay rules:
0->X uses rise, 1->X uses fall, X->0 uses fall, X->1 uses rise. The pinned
Icarus 13 source vvp/delay.cc modpath_src_put_delays documents the same map.
Native X/path and pulse qualifications are separate mandatory obligations.
Even a Passed finite_event_status never permits S14 adoption on its own.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

from .sdf_timing_audit import timing_records, _edges


class EventAuditError(ValueError):
    """The transcript cannot establish complete, unambiguous evidence."""


def _need(condition, message):
    if not condition:
        raise EventAuditError(message)


def _number(text):
    _need(isinstance(text, str) and re.fullmatch(r"0|[1-9][0-9]*", text),
          "Require canonical nonnegative integer")
    return int(text)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            _need(key not in result, "Duplicate summary JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          EventAuditError("Nonfinite summary value: " + value)))


@dataclass
class EventTranscript:
    """Raw initial/change callbacks include no-op callbacks and exact sequence."""
    sha256: str
    summary_sha256: str
    signals: dict
    paths: dict
    traces: dict
    counts: dict
    end_time_ps: int
    last_sequence: int
    metadata: dict


def read_event_transcript(path, summary_path):
    """Read the complete HULLCIRQ_EVENTS_V1 contract, or fail closed.

    EVENT kinds are initial/change/settled. A change is a callback notification
    and may repeat the prior bit value. Such callbacks are retained and counted
    but are not invented signal edges. Settled records must confirm the actual
    previous value at t=0. All counters/footer and the post-close summary are
    mandatory; a normal simulation exit cannot replace them.
    """
    signals, paths, traces, counts, declared = {}, {}, {}, {}, {}
    metadata, current = {}, {}
    sequence, last_time, footer, phase = 0, 0, None, "header"
    initial_seen, callbacks_started, output_bytes = 0, False, 0
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for line_number, raw in enumerate(handle, 1):
            digest.update(raw)
            output_bytes += len(raw)
            _need(raw.endswith(b"\n"), "Truncated transcript line")
            fields = raw.decode("ascii").rstrip("\n").rstrip("\r").split("\t")
            if line_number == 1:
                _need(fields == ["HULLCIRQ_EVENTS_V1"], "Unknown event transcript version")
                continue
            _need(footer is None, "Data after event footer")
            kind = fields[0]
            if kind == "META":
                _need(phase == "header" and len(fields) == 3 and fields[1] not in metadata,
                      "Invalid/duplicate transcript metadata")
                metadata[fields[1]] = fields[2]
            elif kind == "SIGNAL":
                _need(phase == "header" and len(fields) == 5, "Invalid signal mapping")
                signal_id, name, width, role = _number(fields[1]), fields[2], _number(fields[3]), fields[4]
                _need(signal_id > 0 and signal_id not in signals and name not in paths
                      and name and not any(char.isspace() for char in name)
                      and 0 < width <= 4096 and role, "Duplicate/invalid signal mapping")
                signals[signal_id] = {"path": name, "width": width, "role": role}
                paths[name] = signal_id
                traces[signal_id] = []
                counts[signal_id] = Counter(initial=0, change=0, settled=0)
            elif kind == "EVENT":
                _need(phase in ("header", "events") and signals and len(fields) == 6,
                      "Invalid or unbound event")
                phase = "events"
                seq, time_ps, signal_id = map(_number, fields[1:4])
                event_kind, value = fields[4:]
                _need(seq == sequence + 1 and time_ps >= last_time and signal_id in signals,
                      "Event sequence gap, time reversal or unknown signal")
                _need(event_kind in ("initial", "change", "settled")
                      and len(value) == signals[signal_id]["width"]
                      and re.fullmatch(r"[01xz]+", value), "Invalid event kind/value/width")
                if event_kind == "initial":
                    _need(time_ps == 0 and counts[signal_id]["initial"] == 0
                          and not callbacks_started,
                          "Initial snapshot must be complete, unique and before callbacks")
                    initial_seen += 1
                else:
                    callbacks_started = True
                    _need(initial_seen == len(signals),
                          "Callback before complete initial snapshot")
                    if event_kind == "settled":
                        _need(time_ps == 0 and counts[signal_id]["settled"] == 0
                              and value == current[signal_id], "Invalid settled snapshot")
                if event_kind != "settled":
                    traces[signal_id].append((time_ps, seq, value))
                counts[signal_id][event_kind] += 1
                current[signal_id] = value
                sequence, last_time = seq, time_ps
            elif kind == "COUNTS":
                _need(phase in ("events", "counts") and len(fields) == 5, "Invalid per-signal counts")
                phase = "counts"
                signal_id, initial, change, settled = map(_number, fields[1:])
                _need(signal_id in signals and signal_id not in declared, "Duplicate/unknown signal counts")
                declared[signal_id] = {"initial": initial, "change": change, "settled": settled}
            elif kind == "END":
                _need(phase == "counts" and len(fields) == 7, "Invalid/missing event footer")
                last_seq, end, signal_count, event_count, error_count, complete = map(_number, fields[1:])
                _need(last_seq == sequence == event_count and end >= last_time
                      and signal_count == len(signals) and error_count == 0 and complete == 1,
                      "Incomplete event recording or inconsistent footer")
                footer = {"end_time_ps": end, "last_sequence": last_seq,
                          "signal_count": signal_count, "event_count": event_count}
            else:
                raise EventAuditError("Unknown transcript record at line " + str(line_number))
    _need(footer is not None and set(declared) == set(signals)
          and set(signals) == set(range(1, len(signals) + 1))
          and set(metadata) == {"time_precision", "delta_identity"}
          and metadata == {"time_precision": "-12", "delta_identity": "unavailable"},
          "Missing footer/counts or unsupported timing precision/identity")
    _need(all(dict(counts[key]) == declared[key] and counts[key]["initial"] == 1
              and counts[key]["settled"] == 1 for key in signals), "Per-signal count/snapshot mismatch")
    raw_summary = Path(summary_path).read_bytes()
    summary = _strict_json(raw_summary)
    _need(type(summary) is dict, "Summary must be one JSON object")
    # Exact post-close summary bindings supplement, rather than replace, TSV.
    _need(summary.get("schema_version") == "hullcirq-event-capture-summary-v1"
          and summary.get("capture_complete") is True and summary.get("flush_complete") is True
          and summary.get("end_callback_seen") is True
          and type(summary.get("dropped_events")) is int and summary["dropped_events"] == 0,
          "Missing successful post-close flush or dropped events")
    _need(type(summary.get("time_precision")) is int and summary["time_precision"] == -12,
          "Summary timing precision mismatch")
    _need(summary.get("delta_identity") == "unavailable"
          and summary.get("ordering") == "callback_invocation_order"
          and summary.get("initial_scope") == "cbStartOfSimulation_before_initial_threads"
          and summary.get("settled_scope") == "time_zero_cbReadOnlySynch",
          "Unknown summary event-order/snapshot semantics")
    summary_bindings = {"last_sequence": footer["last_sequence"],
                        "end_time_ps": footer["end_time_ps"],
                        "manifest_signal_count": footer["signal_count"],
                        "resolved_signal_count": footer["signal_count"],
                        "events_written": footer["event_count"], "output_bytes": output_bytes,
                        "initial_events": sum(item["initial"] for item in counts.values()),
                        "change_callbacks": sum(item["change"] for item in counts.values()),
                        "settled_events": sum(item["settled"] for item in counts.values())}
    for name, value in summary_bindings.items():
        _need(type(summary.get(name)) is int and summary[name] == value, "Summary/footer mismatch: " + name)
    _need(summary.get("error_count") == 0 and type(summary.get("error_count")) is int,
          "Logger reported errors")
    _need(summary.get("last_error") == "none"
          and type(summary.get("max_events")) is int and summary["max_events"] >= sequence
          and type(summary.get("max_bytes")) is int and summary["max_bytes"] >= output_bytes,
          "Logger quota/error summary is incomplete or inconsistent")
    items = summary.get("signals")
    _need(type(items) is list and all(type(item) is dict for item in items), "Missing summary signal list")
    _need(all(type(item.get("id")) is int for item in items), "Invalid summary signal ID")
    per_signal = {item["id"]: item for item in items}
    _need(len(items) == len(per_signal) and set(per_signal) == set(signals),
          "Missing/duplicated summary signal counts")
    for key in signals:
        item = per_signal[key]
        _need(item.get("path") == signals[key]["path"] == item.get("resolved_path")
              and type(item.get("width")) is int and item["width"] == signals[key]["width"]
              and item.get("role") == signals[key]["role"]
              and type(item.get("object_type")) is int and item["object_type"] > 0,
              "Summary signal identity mismatch")
        _need(all(type(item.get(name + "_count")) is int
                  and item[name + "_count"] == counts[key][name] for name in ("initial", "change", "settled")),
              "Summary per-signal count mismatch")
    return EventTranscript(digest.hexdigest(), _sha(raw_summary), signals, paths, traces,
                           {key: dict(value) for key, value in counts.items()},
                           footer["end_time_ps"], sequence, metadata)


def _semantic_trace(raw):
    """Remove no-op notifications without removing any real same-tick edge."""
    result = []
    for event in raw:
        if not result or event[2] != result[-1][2]:
            result.append(event)
    return result


def _value_at(trace, times, time_ps):
    index = bisect_right(times, time_ps) - 1
    return None if index < 0 else trace[index][2]


def _clock_source_proof(path, expected_sha256, source_clock_path):
    _need(path is not None and isinstance(expected_sha256, str)
          and re.fullmatch(r"[0-9a-f]{64}", expected_sha256),
          "Startup proof requires the exact execution-bound testbench bytes and expected SHA")
    raw = Path(path).read_bytes()
    _need(_sha(raw) == expected_sha256, "Startup testbench raw hash mismatch")
    text = raw.decode("utf-8")
    # A displayed string or a commented declaration is not executable source.
    text = re.sub(r'"(?:\\.|[^"\\])*"|/\*.*?\*/|//[^\n]*',
                  lambda match: "\n" * match[0].count("\n"), text, flags=re.S)
    module = re.findall(r"(?m)^module ([A-Za-z_$][\w$]*)\s*;", text)
    _need(len(module) == 1 and source_clock_path == module[0] + ".clk"
          and len(re.findall(r"(?m)^[ \t]*reg\s+clk\s*=\s*0\s*,\s*rst\s*=\s*1\s*;[ \t]*$", text)) == 1,
          "Unknown original source-clock initialization syntax")
    return {"testbench_raw_sha256": expected_sha256, "source_clock_path": source_clock_path,
            "declared_initial_value": "0", "scope": "raw source identity; process input binding is external"}


def audit_postlayout_events(sdf_text, transcript_path, summary_path, *, dut_scope="tb.dut",
                           source_clock_path=None, selection="typ", offset_ps=0,
                           qualify_initial_clock_settlement=False, testbench_path=None,
                           expected_testbench_sha256=None):
    """Audit all sequential events; retain a separate, explicitly limited status.

    ``finite_event_status`` describes this fixed subset. ``status`` remains
    Unsupported unless an observed contradiction makes it Failed. Logger
    callback fidelity, actual process/model binding, arbitrary pulse behavior,
    original nine-argument notifier semantics and complete combinational SDF
    coverage are deliberately not inferred from a well-formed transcript.
    """
    report = {"kind": "hullcirq-postlayout-whole-event-audit-v1", "status": "Unsupported",
              "finite_event_status": "Unsupported", "adoption_permitted": False,
              "scope": "all_recorded_sequential_events_in_one_finite_stable_capture_trace",
              "original_sdf_sha256": _sha(sdf_text.encode("utf-8")), "transcript_sha256": None,
              "ignored_startup_or_reset_cycles": 0, "delta_region_identity_known": False,
              "sequence_meaning": "callback invocation order; no inferred delta or scheduling region",
              "complete_timing_model_qualification": False,
              "remaining_qualification": ["independent native callback-fidelity/pulse/X probes",
                  "exact executed model/compiler/testbench/process binding",
                  "all combinational IOPATH/INTERCONNECT semantics and pulse qualification",
                  "general delayed-reference/data and notifier-on-violation semantics"],
              "counts": {"timing_cells": 0, "mapped_cells": 0, "raw_callbacks": 0,
                  "no_op_callbacks": 0, "captures": 0, "capture_qualified": 0,
                  "signed_violations": 0, "width_violations": 0, "q_expected_transitions": 0,
                  "q_observed_transitions": 0, "q_matched_transitions": 0, "q_extra_transitions": 0,
                  "q_missing_transitions": 0, "q_wrong_transitions": 0,
                  "constant_unknown_captures": 0, "qualified_initial_clock_settlements": 0,
                  "source_local_clock_edges_matched": 0, "unobserved_final_source_falling_edges": 0,
                  "shared_signed_offset_intersection_empty": 0}, "cells": [], "diagnostics": []}
    failures, unsupported = [], []
    counts = report["counts"]
    def issue(target, code, name, **values):
        target.append({"code": code, "instance": name, **values})
    try:
        _need(type(offset_ps) is int and offset_ps == 0, "Only explicitly zero-offset delayed-pin copies supported")
        _need(type(qualify_initial_clock_settlement) is bool, "Startup opt-in must be boolean")
        _need(isinstance(dut_scope, str) and re.fullmatch(r"[\w$]+(?:\.[\w$]+)*", dut_scope), "Invalid DUT scope")
        records = timing_records(sdf_text, selection=selection)
        transcript = read_event_transcript(transcript_path, summary_path)
        report.update(transcript_sha256=transcript.sha256, summary_sha256=transcript.summary_sha256,
                      end_time_ps=transcript.end_time_ps, transcript_event_count=transcript.last_sequence)
        counts["timing_cells"] = len(records)
        if qualify_initial_clock_settlement:
            report["source_clock_proof"] = _clock_source_proof(
                testbench_path, expected_testbench_sha256, source_clock_path)
            _need(source_clock_path in transcript.paths, "Missing original source clock")
            source = _semantic_trace(transcript.traces[transcript.paths[source_clock_path]])
            _need(transcript.signals[transcript.paths[source_clock_path]]["width"] == 1,
                  "Source clock is not scalar")
            # Allow initial X->0 at t=0 only with the bound clk=0 declaration.
            if source[0][2] == "x":
                _need(len(source) > 1 and source[1][0] == 0 and source[1][2] == "0",
                      "Source clock did not initialize to zero at t=0")
                source = source[1:]
            _need(source[0][0] == 0 and source[0][2] == "0"
                  and all(event[2] in ("0", "1") for event in source), "Unknown original source clock")
            source_first = next((event[0] for event in source[1:] if event[2] == "1"), None)
            _need(source_first is not None and source_first > 0, "No qualified original source rising edge")
            source_edges = source[1:]
            source_times = [event[0] for event in source_edges]
            _need(all(source_times[index] > source_times[index - 1]
                      for index in range(1, len(source_times))),
                  "Same-tick source-clock changes lack independent region qualification")
        for record in records:
            name = record["instance"]
            paths = {pin: f"{dut_scope}.{name}.{pin}" for pin in ("D", "CLK", "D_delayed", "CLK_delayed", "Q")}
            _need(all(path in transcript.paths and transcript.signals[transcript.paths[path]]["width"] == 1
                      for path in paths.values()), "Missing/scalar-width mismatch for sequential pin: " + name)
            raw = {pin: transcript.traces[transcript.paths[path]] for pin, path in paths.items()}
            traces = {pin: _semantic_trace(value) for pin, value in raw.items()}
            d, clk, q = (traces[pin] for pin in ("D", "CLK", "Q"))
            dt = [event[0] for event in d]
            counts["mapped_cells"] += 1
            counts["raw_callbacks"] += sum(len(value) - 1 for value in raw.values())
            counts["no_op_callbacks"] += sum(len(raw[pin]) - len(traces[pin]) for pin in raw)
            lower_offset = max(-pair["hold_ps"] for pair in record["pairs"].values())
            upper_offset = min(pair["setup_ps"] for pair in record["pairs"].values())
            counts["shared_signed_offset_intersection_empty"] += int(lower_offset > upper_offset)
            cell = {"instance": name, "signed_pairs": record["pairs"],
                    "shared_data_minus_reference_offset_ps": [lower_offset, upper_offset],
                    "shared_offset_exists": lower_offset <= upper_offset,
                    "captures": 0, "capture_qualified": 0, "q_trace_complete": False,
                    "startup_settlement_qualified": False}
            report["cells"].append(cell)
            cell_unsupported = len(unsupported)
            # Alias callbacks may have different sequence IDs, but every real
            # copied value transition must have the same exact picosecond.
            for pin, original in (("D_delayed", "D"), ("CLK_delayed", "CLK")):
                if [(time, value) for time, _, value in traces[pin]] != [(time, value) for time, _, value in traces[original]]:
                    issue(failures, "delayed_pin_copy_mismatch", name, pin=pin)
            if q[0][2] != "x":
                issue(failures, "original_udp_initial_q_mismatch", name, value=q[0][2])
            startup = bool(qualify_initial_clock_settlement and len(clk) > 1
                           and clk[0][2] == "x" and clk[1][2] == "0"
                           and 0 <= clk[1][0] < source_first)
            first_posedge = next((event[0] for i, event in enumerate(clk)
                                  if i and clk[i-1][2] == "0" and event[2] == "1"), None)
            if startup:
                if first_posedge is not None and any(event[2] != "x" for event in q if event[0] < first_posedge):
                    issue(failures, "q_transition_before_first_capture", name)
                startup = bool(first_posedge is not None and q[0][2] == "x"
                               and all(event[2] == "x" for event in q if event[0] < first_posedge))
            if startup:
                counts["qualified_initial_clock_settlements"] += 1
                cell["startup_settlement_qualified"] = True
                cell["startup_settlement_ps"] = clk[1][0]
            elif clk[0][2] not in ("0", "1"):
                issue(unsupported, "unknown_initial_clock", name)
            data_edges = [(event[0], polarity) for i, event in enumerate(d) if i
                          for polarity in _edges(d[i-1][2], event[2])]
            data_times = [event[0] for event in data_edges]
            expected_q, model_state, last_clock_edge, last_capture = [], "x", None, None
            next_source_edge = 0
            for index, event in enumerate(clk[1:], 1):
                c, seq, value = event
                before = clk[index-1][2]
                if before not in ("0", "1") or value not in ("0", "1"):
                    if startup and index == 1:
                        last_clock_edge = (c, "negedge")
                        continue
                    issue(unsupported, "unknown_clock_transition", name, time_ps=c, sequence=seq)
                    continue
                edge = "posedge" if value == "1" else "negedge"
                if qualify_initial_clock_settlement:
                    source_index = bisect_right(source_times, c) - 1
                    if source_index < 0 or source_index != next_source_edge or source_edges[source_index][2] != value:
                        issue(unsupported, "source_local_clock_edge_correspondence_unqualified", name,
                              time_ps=c, local_value=value, expected_source_index=next_source_edge,
                              preceding_source_index=source_index)
                    elif source_edges[source_index][0] == c:
                        issue(unsupported, "same_tick_source_local_clock_region_ambiguous", name, time_ps=c)
                        next_source_edge += 1
                    else:
                        counts["source_local_clock_edges_matched"] += 1
                        next_source_edge += 1
                if last_clock_edge is not None:
                    previous_time, previous_polarity = last_clock_edge
                    width = c - previous_time
                    if width < record["width_ps"][previous_polarity]:
                        counts["width_violations"] += 1
                        issue(failures, "width_violation", name, time_ps=c, width_ps=width,
                              polarity=previous_polarity, minimum_ps=record["width_ps"][previous_polarity])
                    if width <= max(record["q_rise_ps"], record["q_fall_ps"]):
                        issue(unsupported, "clock_pulse_not_isolated_from_q_delay", name, time_ps=c, width_ps=width)
                last_clock_edge = (c, edge)
                if edge != "posedge":
                    continue
                counts["captures"] += 1
                cell["captures"] += 1
                if last_capture is not None and c - last_capture <= max(record["q_rise_ps"], record["q_fall_ps"]):
                    issue(unsupported, "overlapping_capture_paths", name, time_ps=c)
                last_capture = c
                for polarity, pair in record["pairs"].items():
                    left, right = c - pair["setup_ps"], c + pair["hold_ps"]
                    for time, data_edge in data_edges[bisect_right(data_times, left):bisect_left(data_times, right)]:
                        if data_edge == polarity:
                            counts["signed_violations"] += 1
                            issue(failures, "signed_setuphold_violation", name, clock_ps=c, data_ps=time,
                                  polarity=polarity, open_window_ps=[left, right], **pair)
                left = c - max(pair["setup_ps"] for pair in record["pairs"].values())
                changes = [item for i, item in enumerate(d[bisect_left(dt, left):bisect_right(dt, c)], bisect_left(dt, left)) if i]
                data = _value_at(d, dt, left)
                if left < 0 or data is None or changes:
                    issue(unsupported, "capture_window_unqualified", name, clock_ps=c,
                          closed_window_ps=[left, c], changes=changes)
                    continue
                counts["capture_qualified"] += 1
                cell["capture_qualified"] += 1
                target = "x" if data in ("x", "z") else data
                counts["constant_unknown_captures"] += int(target == "x")
                maximum_deadline = c + max(record["q_rise_ps"], record["q_fall_ps"])
                if maximum_deadline > transcript.end_time_ps:
                    issue(unsupported, "trace_ends_before_full_q_deadline", name, clock_ps=c)
                if target != model_state:
                    # Two-value *modpath* expansion, including X, not the
                    # different generic primitive-delay min(rise,fall) rule.
                    delay = record["q_rise_ps"] if target == "1" or model_state == "0" and target == "x" else record["q_fall_ps"]
                    if delay <= 0:
                        issue(unsupported, "zero_q_delay_region_ambiguous", name, clock_ps=c)
                    expected_q.append((c + delay, target, c, seq))
                    model_state = target
            observed_q = q[1:]
            if qualify_initial_clock_settlement:
                pending = source_edges[next_source_edge:]
                if len(pending) == 1 and pending[0][2] == "0" and pending[0][0] == transcript.end_time_ps:
                    # The transcript ends before this final falling edge has
                    # traversed the clock tree. No posedge/capture is skipped.
                    cell["unobserved_final_source_falling_edge_ps"] = pending[0][0]
                    counts["unobserved_final_source_falling_edges"] += 1
                elif pending:
                    issue(unsupported, "unmatched_source_clock_edges", name, count=len(pending))
            counts["q_observed_transitions"] += len(observed_q)
            counts["q_expected_transitions"] += len(expected_q)
            cell["q_observed_transitions"] = len(observed_q)
            cell["q_expected_transitions"] = len(expected_q)
            if not cell["captures"]:
                issue(unsupported, "no_observed_capture", name)
            if len(unsupported) != cell_unsupported:
                # Never invent a predicted waveform through an unqualified
                # capture/unknown-clock/pulse region, then label it wrong.
                continue
            qi = ei = 0
            while qi < len(observed_q) or ei < len(expected_q):
                observed = observed_q[qi] if qi < len(observed_q) else None
                expected = expected_q[ei] if ei < len(expected_q) else None
                if observed is not None and (expected is None or observed[0] < expected[0]):
                    counts["q_extra_transitions"] += 1
                    issue(failures, "extra_q_transition", name, time_ps=observed[0], sequence=observed[1], value=observed[2])
                    qi += 1
                elif expected is not None and (observed is None or observed[0] > expected[0]):
                    counts["q_missing_transitions"] += 1
                    issue(failures, "missing_q_transition", name, time_ps=expected[0], value=expected[1], clock_ps=expected[2])
                    ei += 1
                else:
                    if observed[2] != expected[1]:
                        counts["q_wrong_transitions"] += 1
                        issue(failures, "wrong_q_transition", name, time_ps=observed[0], sequence=observed[1],
                              actual=observed[2], expected=expected[1], clock_ps=expected[2])
                    else:
                        counts["q_matched_transitions"] += 1
                    qi += 1
                    ei += 1
            cell["q_trace_complete"] = True
        report["finite_event_status"] = "Failed" if failures else "Unsupported" if unsupported else "Passed"
        report["status"] = "Failed" if failures else "Unsupported"
        report["diagnostics"] = failures + unsupported
    except (ValueError, OSError, UnicodeError, KeyError, TypeError) as error:
        unsupported.append({"code": "event_audit_input_unsupported", "message": str(error)})
        report["diagnostics"] = failures + unsupported
        if failures:
            report["status"] = report["finite_event_status"] = "Failed"
    report["failure_count"], report["unsupported_count"] = len(failures), len(unsupported)
    return report
