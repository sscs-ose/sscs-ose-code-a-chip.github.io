"""Read-only attribution of ambiguous SDF IOPATH records.

This audit never annotates a simulator, edits a model, or grants acceptance.
It combines a byte-exact (apart from DATE) OpenSTA SDF replay with independently
queried graph edge senses and numeric delay profiles. Duplicate profiles remain
ambiguous. For duplicate combinational paths, Boolean conditions are derived
from the original Liberty output function and checked against every conditional
path in an explicitly preprocessed PDK model. This is a two-state truth-table
comparison, not four-state Verilog equivalence or native VPI path identity.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import io
import itertools
import re

from .sdf_interconnect import parse_sdf


class ConditionalPathError(ValueError):
    """An input is outside the deliberately narrow audited subset."""


def _need(value, message):
    if not value:
        raise ConditionalPathError(message)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare_sdf_replay(original, replay):
    """Exclude exactly one DATE value; all other bytes of the text must agree."""
    pattern = re.compile(r'\(DATE "[^"\r\n]*"\)')
    _need(len(pattern.findall(original)) == len(pattern.findall(replay)) == 1,
          "Require exactly one DATE in each SDF")
    a = pattern.sub('(DATE "DATE-ONLY-EXCLUDED")', original)
    b = pattern.sub('(DATE "DATE-ONLY-EXCLUDED")', replay)
    return {"raw_text_equal": original == replay,
            "text_equal_excluding_date_only": a == b,
            "original_utf8_sha256": _sha(original), "replay_utf8_sha256": _sha(replay),
            "date_excluded_original_sha256": _sha(a),
            "date_excluded_replay_sha256": _sha(b)}


def _children(node, name):
    return [v for v in node[1:] if isinstance(v, list) and v and v[0] == name]


def _one(node, name):
    values = _children(node, name)
    _need(len(values) == 1, f"Require one SDF {name}")
    return values[0]


def _triple(node):
    _need(isinstance(node, list) and len(node) == 1 and isinstance(node[0], str),
          "Require scalar IOPATH delay")
    parts = node[0].split(":")
    _need(len(parts) in (1, 3) and all(parts), "Require complete IOPATH delay triple")
    values = [Decimal(v) * 1000 for v in parts]
    _need(all(v.is_finite() and v >= 0 and v == v.to_integral_value() for v in values),
          "Require nonnegative whole-picosecond IOPATH delays")
    values = [int(v) for v in values]
    return values * 3 if len(values) == 1 else values


def iopath_records(text):
    """Inventory every bare ABSOLUTE IOPATH, retaining all min/typ/max values."""
    tree = parse_sdf(text)
    _need(_one(tree, "TIMESCALE")[1:] == ["1ns"], "Require 1ns timescale")
    _need(_one(tree, "DIVIDER")[1:] == ["."], "Require dot divider")
    result, row = [], 0
    for cell in _children(tree, "CELL"):
        instance = _one(cell, "INSTANCE")[1:]
        _need(len(instance) <= 1, "Require flat scalar instance")
        master = _one(cell, "CELLTYPE")
        _need(len(master) == 2 and master[1].startswith('"') and master[1].endswith('"'),
              "Require quoted CELLTYPE")
        for delay in _children(cell, "DELAY"):
            _need(len(delay) == 2 and delay[1][0] == "ABSOLUTE", "Require ABSOLUTE delay")
            for item in delay[1][1:]:
                _need(isinstance(item, list) and item, "Malformed delay record")
                _need(item[0] in ("IOPATH", "INTERCONNECT"),
                      "Conditional or other delay syntax requires a separate audit")
                row += 1
                if item[0] != "IOPATH":
                    continue
                _need(len(instance) == 1 and len(item) in (4, 5), "Require flat two-transition IOPATH")
                _need(all(isinstance(v, str) and re.fullmatch(r"[A-Za-z_$][\w$]*", v)
                          for v in item[1:3]), "Edge-qualified or escaped IOPATH unsupported")
                rise = _triple(item[3])
                result.append({"source_record_id": row, "instance": instance[0],
                               "celltype": master[1][1:-1], "source": item[1], "destination": item[2],
                               "rise_triple_ps": rise,
                               "fall_triple_ps": _triple(item[4]) if len(item) == 5 else rise[:]})
    _need(result, "No IOPATH records")
    return result


def _profile(record):
    return tuple(record["rise_triple_ps"] + record["fall_triple_ps"])


def read_graph_edges(text):
    fields = ["instance", "source", "dest", "index", "sense", "min_rise_ns", "max_rise_ns",
              "min_fall_ns", "max_fall_ns"]
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    _need(reader.fieldnames == fields, "Unexpected OpenSTA graph TSV columns")
    result, seen = [], set()
    for row in reader:
        _need(None not in row and all(row.values()), "Missing OpenSTA graph field")
        _need(row["sense"] in ("positive_unate", "negative_unate", "non_unate"), "Unknown graph sense")
        index = int(row["index"])
        key = (row["instance"], row["source"], row["dest"], index)
        _need(index > 0 and key not in seen, "Duplicate OpenSTA graph edge")
        seen.add(key)
        values = [Decimal(row[v]) for v in fields[5:]]
        _need(all(v.is_finite() and v >= 0 for v in values), "Invalid graph delay")
        triples = []
        for low, high in (values[:2], values[2:]):
            # These are analysis-point labels. Slew/load differences can make
            # the min analysis point numerically larger than the max point.
            triples.append([int((v * 1000).to_integral_value(rounding=ROUND_HALF_EVEN))
                            for v in (low, (low + high) / 2, high)])
        result.append({"instance": row["instance"], "source": row["source"], "destination": row["dest"],
                       "graph_index": index, "sense": row["sense"],
                       "rise_triple_ps": triples[0], "fall_triple_ps": triples[1],
                       "raw_graph_delay_ns": row.copy()})
    _need(result, "No graph edges")
    return result


def _strip_comments(text):
    return re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)


def _blocks(text, kind):
    """Yield balanced Liberty group bodies, respecting quoted strings."""
    pattern = re.compile(r"\b" + re.escape(kind) + r"\s*\(([^()]*)\)\s*\{")
    for match in pattern.finditer(text):
        depth, quote, escape, pos = 1, False, False, match.end()
        while pos < len(text) and depth:
            char = text[pos]
            if quote:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    quote = False
            elif char == '"':
                quote = True
            elif char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
            pos += 1
        _need(depth == 0 and not quote, f"Unterminated Liberty {kind}")
        yield match[1].strip().strip('"'), text[match.end():pos - 1]


def _attribute(text, name, required=True):
    matches = re.findall(r"\b" + re.escape(name) + r'\s*:\s*(?:"([^"\\]*)"|([^;{}]+))\s*;', text)
    _need(len(matches) <= 1 and (matches or not required), f"Missing or duplicate Liberty {name}")
    return (matches[0][0] or matches[0][1]).strip() if matches else None


def liberty_cells(text, selected):
    text = _strip_comments(text)
    result = {}
    for name, body in _blocks(text, "cell"):
        if name not in selected:
            continue
        _need(name not in result, "Duplicate Liberty cell")
        pins = {}
        for pin, pin_body in _blocks(body, "pin"):
            _need(pin not in pins, "Duplicate Liberty pin")
            direction = _attribute(pin_body, "direction")
            timing = []
            for _, timing_body in _blocks(pin_body, "timing"):
                timing.append({key: _attribute(timing_body, key, required=False)
                               for key in ("related_pin", "timing_sense", "timing_type", "when", "sdf_cond")})
            pins[pin] = {"direction": direction, "function": _attribute(pin_body, "function", required=False),
                         "timing": timing}
        result[name] = pins
    _need(set(result) == set(selected), "Missing selected Liberty cell")
    return result


def boolean_expression(expression):
    """Compile a small explicit two-state Liberty/Verilog Boolean subset.

    Implicit conjunction, ternary, equality, vector operations and X/Z constants
    are deliberately rejected. No Python eval or host expression execution.
    """
    scanner = re.compile(r"\s+|[A-Za-z_$][\w$]*|[01]|[()!~'&*|+^]")
    tokens, position = [], 0
    for match in scanner.finditer(expression):
        _need(match.start() == position, "Unsupported Boolean syntax")
        position = match.end()
        if not match[0].isspace():
            tokens.append(match[0])
    _need(position == len(expression) and tokens, "Incomplete Boolean expression")
    index, names = 0, set()

    def atom():
        nonlocal index
        _need(index < len(tokens), "Truncated Boolean operand")
        token = tokens[index]
        index += 1
        if token in ("!", "~"):
            value = ("not", atom())
        elif token == "(":
            value = binary(0)
            _need(index < len(tokens) and tokens[index] == ")", "Unbalanced Boolean expression")
            index += 1
        elif token in ("0", "1"):
            value = ("constant", int(token))
        else:
            _need(re.fullmatch(r"[A-Za-z_$][\w$]*", token), "Unexpected Boolean operand")
            names.add(token)
            value = ("name", token)
        while index < len(tokens) and tokens[index] == "'":
            value = ("not", value)
            index += 1
        return value

    levels = [{"|", "+"}, {"^"}, {"&", "*"}]

    def binary(level):
        nonlocal index
        value = atom() if level == len(levels) else binary(level + 1)
        while level < len(levels) and index < len(tokens) and tokens[index] in levels[level]:
            op = tokens[index]
            index += 1
            value = (op, value, binary(level + 1))
        return value

    tree = binary(0)
    _need(index == len(tokens), "Unconsumed Boolean syntax")

    def evaluate(values):
        def run(node):
            op = node[0]
            if op == "name":
                _need(node[1] in values and type(values[node[1]]) in (int, bool)
                      and values[node[1]] in (0, 1), "Require complete two-state valuation")
                return int(values[node[1]])
            if op == "constant":
                return node[1]
            if op == "not":
                return 1 - run(node[1])
            a, b = run(node[1]), run(node[2])
            return a & b if op in ("&", "*") else (a | b if op in ("|", "+") else a ^ b)
        return run(tree)
    return names, evaluate


def model_paths(text, selected):
    """Read every conditional +/- scalar path from preprocessed selected cells."""
    _need(not re.search(r"^\s*`(?:if|else|endif|define|include)", text, re.M),
          "PDK model must be explicitly preprocessed with recorded defines")
    text = _strip_comments(text)
    result = {}
    conditional = re.compile(r"if\s*\((.*?)\)\s*\(\s*([A-Za-z_$][\w$]*)\s*([+-])=>\s*"
                             r"([A-Za-z_$][\w$]*)\s*\)\s*=\s*\([^;]*\)\s*;", re.S)
    for match in re.finditer(r"\bmodule\s+([A-Za-z_$][\w$]*)\s*\([^;]*\)\s*;(.*?)\bendmodule\b", text, re.S):
        name, body = match.groups()
        if name not in selected:
            continue
        _need(name not in result, "Duplicate preprocessed module")
        specify = re.findall(r"\bspecify\b(.*?)\bendspecify\b", body, re.S)
        _need(len(specify) == 1, "Require one specify block per selected module")
        paths = []
        for path in conditional.finditer(specify[0]):
            condition, source, polarity, destination = path.groups()
            names, evaluate = boolean_expression(condition)
            paths.append({"source": source, "destination": destination,
                          "sense": "positive_unate" if polarity == "+" else "negative_unate",
                          "condition": condition.strip(), "condition_names": names, "evaluate": evaluate})
        # Every path declaration in this selected subset must have been parsed.
        # '=>', '+=>', '-=>' are the only path operators used here.
        all_paths = len(re.findall(r"(?:[+-])?=>|\*>", specify[0]))
        _need(all_paths == len(paths), "Uncovered or unsupported selected model path")
        _need(paths, "No selected model paths")
        result[name] = paths
    _need(set(result) == set(selected), "Missing selected preprocessed model")
    return result


def condition_truth_table(pins, paths, source, destination):
    """Compare function-derived sense conditions against PDK path unions."""
    _need(source in pins and pins[source]["direction"] == "input", "Source is not Liberty input")
    _need(destination in pins and pins[destination]["direction"] == "output", "Destination is not Liberty output")
    function = pins[destination]["function"]
    _need(function is not None, "Missing combinational output function")
    names, evaluate = boolean_expression(function)
    inputs = {pin for pin, data in pins.items() if data["direction"] == "input"}
    _need(source in names and names <= inputs, "Function contains unknown or noninput variables")
    others = sorted(inputs - {source})
    _need(len(others) <= 8, "Truth table exceeds bounded supported input size")
    selected = [p for p in paths if p["source"] == source and p["destination"] == destination]
    _need(selected and all(p["condition_names"] <= set(others) for p in selected),
          "Model condition depends on changed source or unknown inputs")
    timing = [t for t in pins[destination]["timing"] if t["related_pin"] == source]
    _need(timing and all(t["timing_type"] == "combinational" and t["when"] is None
                        and t["sdf_cond"] is None for t in timing), "Unexpected Liberty conditional timing")
    _need(Counter(t["timing_sense"] for t in timing) == Counter({"positive_unate": 1, "negative_unate": 1}),
          "Require one positive and one negative Liberty timing arc set")
    table, mismatches = [], []
    for bits in itertools.product((0, 1), repeat=len(others)):
        values = dict(zip(others, bits))
        low, high = evaluate({**values, source: 0}), evaluate({**values, source: 1})
        expected = "positive_unate" if (low, high) == (0, 1) else (
            "negative_unate" if (low, high) == (1, 0) else None)
        hits = [index for index, path in enumerate(selected, 1) if path["evaluate"](values)]
        senses = sorted({selected[index - 1]["sense"] for index in hits})
        matched = senses == ([] if expected is None else [expected])
        row = {"inputs": values, "function_source_0": low, "function_source_1": high,
               "derived_sense": expected, "model_active_path_indices": hits,
               "model_active_senses": senses, "matched": matched}
        table.append(row)
        if not matched:
            mismatches.append(row)
    return {"source": source, "destination": destination, "function": function,
            "other_inputs": others, "valuation_count": len(table), "two_state_only": True,
            "liberty_timing_groups": timing,
            "model_conditions": [{k: p[k] for k in ("source", "destination", "sense", "condition")}
                                 for p in selected],
            "truth_table": table, "mismatch_count": len(mismatches),
            "four_state_equivalence_proven": False, "native_path_identity_proven": False}


def conditional_path_inventory(original_sdf, replay_sdf, graph_tsv, liberty_text, preprocessed_models):
    """Return complete read-only attribution and its explicit remaining limits.

    A numeric graph profile must match uniquely. No source-order fallback and
    no fabricated COND are used. The report always denies circuit adoption;
    matching source semantics is separate from simulator annotation repair.
    """
    replay = compare_sdf_replay(original_sdf, replay_sdf)
    _need(replay["text_equal_excluding_date_only"], "SDF replay differs beyond DATE")
    records, edges = iopath_records(original_sdf), read_graph_edges(graph_tsv)
    groups, graph = defaultdict(list), defaultdict(list)
    key = lambda row: (row["instance"], row["source"], row["destination"])
    for row in records:
        groups[key(row)].append(row)
    for edge in edges:
        graph[key(edge)].append(edge)
    duplicate_keys = {k for k, rows in groups.items() if len(rows) > 1}
    masters = {rows[0]["celltype"] for k, rows in groups.items() if k in duplicate_keys}
    libraries, models = liberty_cells(liberty_text, masters), model_paths(preprocessed_models, masters)
    tables, errors = {}, []
    for k in sorted(duplicate_keys):
        master = groups[k][0]["celltype"]
        table_key = (master, k[1], k[2])
        if table_key not in tables:
            tables[table_key] = condition_truth_table(libraries[master], models[master], k[1], k[2])
    mappings, duplicates = [], []
    for k, rows in groups.items():
        candidates = graph.get(k, [])
        mapped_rows = []
        for row in rows:
            hits = [edge for edge in candidates if _profile(edge) == _profile(row)]
            match = {**row, "candidate_graph_indices": [e["graph_index"] for e in hits],
                     "status": "Unique" if len(hits) == 1 else ("Ambiguous" if hits else "Unmatched"),
                     "graph_index": hits[0]["graph_index"] if len(hits) == 1 else None,
                     "sense": hits[0]["sense"] if len(hits) == 1 else None}
            mappings.append(match)
            mapped_rows.append(match)
        if len(candidates) != len(rows):
            errors.append({"group": list(k), "reason": "graph/source cardinality mismatch",
                           "source_records": len(rows), "graph_edges": len(candidates)})
        unique_indices = [r["graph_index"] for r in mapped_rows if r["status"] == "Unique"]
        if len(unique_indices) != len(set(unique_indices)):
            errors.append({"group": list(k), "reason": "multiple source rows map to the same graph edge"})
        if k in duplicate_keys:
            duplicates.append({"instance": k[0], "source": k[1], "destination": k[2],
                               "celltype": rows[0]["celltype"], "records": mapped_rows,
                               "graph_edges": candidates,
                               "condition_table_key": list((rows[0]["celltype"], k[1], k[2])),
                               "native_annotation_repaired": False})
    extra = sorted(set(graph) - set(groups))
    status_counts = Counter(row["status"] for row in mappings)
    return {"schema": "hullcirq-conditional-path-attribution-v1",
            "kind": "read-only-source-semantics-audit", "overall_stage_status": "Unsupported",
            "adoption_permitted": False, "original_inputs_modified": False,
            "simulator_annotation_modified": False, "circuit_dynamic_validation_performed": False,
            "replay_comparison": replay,
            "input_utf8_sha256": {"original_sdf": _sha(original_sdf), "replay_sdf": _sha(replay_sdf),
                                  "graph_tsv": _sha(graph_tsv), "liberty": _sha(liberty_text),
                                  "preprocessed_models": _sha(preprocessed_models)},
            "summary": {"source_iopath_records": len(records), "graph_edges": len(edges),
                        "source_groups": len(groups), "duplicate_groups": len(duplicate_keys),
                        "duplicate_source_records": sum(len(groups[k]) for k in duplicate_keys),
                        "unique_record_attributions": status_counts["Unique"],
                        "ambiguous_record_attributions": status_counts["Ambiguous"],
                        "unmatched_record_attributions": status_counts["Unmatched"],
                        "group_mapping_errors": len(errors), "extra_graph_groups": len(extra),
                        "duplicate_groups_by_celltype": dict(Counter(groups[k][0]["celltype"] for k in duplicate_keys)),
                        "condition_tables": len(tables),
                        "condition_valuations": sum(t["valuation_count"] for t in tables.values()),
                        "condition_truth_mismatches": sum(t["mismatch_count"] for t in tables.values()),
                        "native_binding_repair_count": 0},
            "group_mapping_errors": errors, "extra_graph_groups": [list(v) for v in extra],
            "all_record_mappings": mappings, "all_duplicate_groups": duplicates,
            "condition_tables": [{"celltype": k[0], **v} for k, v in sorted(tables.items())],
            "limits": ["No derived SDF, VPI writer or model correction was applied.",
                       "Original SDF omitted conditional identity; it is not sufficient alone for repair.",
                       "Native Icarus 13 ignores SDF COND/CONDELSE and does not expose path condition through its public VPI implementation.",
                       "Numeric graph properties are rounded to picoseconds; nonunique or unmatched profiles remain explicit.",
                       "Condition comparison covers two-state valuations only, not X/Z or simultaneous transitions.",
                       "PDK condition truth tables do not establish native simulator path ordinal identity.",
                       "This source audit does not establish complete dynamic timing or pulse semantics."]}
