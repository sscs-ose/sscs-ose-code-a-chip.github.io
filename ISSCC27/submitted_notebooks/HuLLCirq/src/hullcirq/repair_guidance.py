"""Source-bound repair planning and comparison. No model or EDA execution.

Lexical rules are proposed edits, never verification results. Full original
contracts and logs remain addressable; only an explicit bounded view is sent.
"""
from __future__ import annotations

import copy
import difflib
import json
import re

from .verification import content_hash, object_hash

VERSION = "s05-repair-guidance-v1"
OUTCOMES = {"no_baseline", "unchanged", "same_diagnostic", "new_diagnostic", "passed", "not_comparable"}


def code_only(rtl):
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                  lambda match: " " * len(match.group().replace("\n", "")) + "\n" * match.group().count("\n"),
                  rtl or "", flags=re.S)


def _record(run):
    return {key: value for key, value in run.items() if key not in {"freshness", "artifacts", "repair_status"}}


def actionable_diagnostics(run, rtl):
    """Compare surviving errors, ignoring paths/line numbers, retaining targets.

    This is a bounded lexical identity, not a semantic equivalence claim.
    Unknown diagnostics without source anchors remain explicitly comparable
    only when their normalized message supplies a concrete target.
    """
    checks = run.get("checks", {})
    stdout = str(checks.get("stdout", ""))
    passes = list(re.finditer(r"(?m)^\d+(?:\.\d+)*\. Executing CHECK pass", stdout))
    final = stdout[passes[-1].start():] if passes else stdout
    output = str(checks.get("stderr", "")) + "\n" + final
    lines = code_only(rtl).splitlines()
    selected = [line for line in output.splitlines()
                if re.search(r"\bERROR\b|conflicting\s+drivers|undriven", line, re.I)]
    if any(re.search(r"conflicting\s+drivers|undriven", line, re.I) for line in selected):
        selected = [line for line in selected if not re.search(r"Found \d+ problems?", line, re.I)]
    if not selected:
        selected = [str(item.get("message", "")) for item in run.get("diagnostics", [])
                    if item.get("severity") in {None, "error"} and item.get("code") != "synthesis_failed"]
    result, seen = [], set()
    for diagnostic in selected:
        location = re.search(r"(?:\.v|\.sv)(?::|\()(\d+)\)?", diagnostic)
        number = int(location.group(1)) if location else None
        source = lines[number - 1].strip() if number and 0 < number <= len(lines) else ""
        target = re.search(r"(?:drivers\s+for|undriven\s+wire)\s+([^\s:]+)", diagnostic, re.I)
        normalized = re.sub(r"(?:[A-Za-z]:)?[^\s()]*\.(?:sv|v)(?::|\()\d+\)?", "<source>", diagnostic)
        normalized = re.sub(r"\bline\s+\d+\b", "line <n>", normalized, flags=re.I)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        anchor = re.sub(r"\s+", "", source)
        construct, source_target = None, None
        declaration = re.match(r"(?:signed|reg(?:\s+signed)?|wire(?:\s+signed)?)\s*\[[^]]+\]\s*([A-Za-z_$][\w$]*)", source)
        assignment = re.match(r"([A-Za-z_$][\w$]*)\s*<=", source)
        if re.search(r"TOK_SIGNED", diagnostic) and declaration and source.startswith("signed"):
            construct, source_target = "untyped_signed_declaration", declaration[1]
        elif re.search(r"Invalid array access|OP_CAST", diagnostic, re.I) and assignment:
            construct, source_target = "whole_array_assignment", assignment[1]
        identity = {"message": normalized, "source_code": anchor,
                    "target": target.group(1).rstrip(":") if target else source_target,
                    "construct": construct}
        signature = {**identity, "source_code": construct} if construct else identity
        digest = object_hash(signature)
        if digest not in seen:
            seen.add(digest)
            result.append({**identity, "line": number, "source": source, "raw_message": diagnostic,
                           "signature": digest})
    return result


def compare_attempt(run, rtl, baseline_run=None, baseline_rtl=None):
    status = {"outcome": "no_baseline", "candidate_id": run.get("candidate_id"), "run_id": run.get("id"),
              "base_candidate_id": (baseline_run or {}).get("candidate_id"),
              "base_run_id": (baseline_run or {}).get("id"), "repeated": False,
              "reconsideration_required": False, "method": "source_anchored_diagnostics_v1"}
    if run.get("execution_status") != "Completed" or run.get("checks", {}).get("executed") is not True:
        status["outcome"] = "not_comparable"
    elif run.get("validation_status") == "Passed":
        status["outcome"] = "passed"
    elif baseline_run is not None:
        comparable = (baseline_run.get("execution_status") == "Completed"
                      and baseline_run.get("checks", {}).get("executed") is True
                      and baseline_run.get("validation_status") == "Failed"
                      and all(run.get(key) == baseline_run.get(key) for key in ("node_id", "input_hash", "stage_id"))
                      and run.get("tool_configuration") == baseline_run.get("tool_configuration")
                      and isinstance(rtl, str) and isinstance(baseline_rtl, str))
        if not comparable:
            status["outcome"] = "not_comparable"
        elif content_hash(rtl) == content_hash(baseline_rtl):
            status["outcome"] = "unchanged"
        else:
            current = {item["signature"] for item in actionable_diagnostics(run, rtl)}
            previous = {item["signature"] for item in actionable_diagnostics(baseline_run, baseline_rtl)}
            status["outcome"] = "same_diagnostic" if current and current == previous else "new_diagnostic" if current and previous else "not_comparable"
    status["repeated"] = status["outcome"] in {"unchanged", "same_diagnostic"}
    status["reconsideration_required"] = status["repeated"]
    return status


def attempt_history(job, jobs, runs, limit=2):
    indexed = {item["id"]: item for item in jobs}
    history, current = [], job
    while current and current.get("operation") == "repair" and len(history) < limit:
        parent = indexed.get(current.get("base_job_id"))
        matches = [run for run in runs if run.get("candidate_id") == current["id"] and run.get("stage_id") == "local_synthesis"]
        older = [run for run in runs if parent and run.get("candidate_id") == parent["id"] and run.get("stage_id") == "local_synthesis"]
        run, prior = matches[-1] if matches else None, older[-1] if older else None
        rtl, old = current.get("rtl"), (parent or {}).get("rtl")
        history.append({"job_id": current["id"], "base_job_id": (parent or {}).get("id"),
                        "rtl_sha256": content_hash(rtl) if rtl else None, "base_rtl_sha256": content_hash(old) if old else None,
                        "instruction": current.get("instruction", ""),
                        "instruction_sha256": content_hash(current.get("instruction", "")),
                        "diff": "".join(difflib.unified_diff((old or "").splitlines(True), (rtl or "").splitlines(True), fromfile="base.v", tofile="candidate.v")),
                        "run_id": (run or {}).get("id"), "validation_status": (run or {}).get("validation_status", "Not Run"),
                        "outcome": compare_attempt(run, rtl, prior, old) if run else {"outcome": "not_comparable", "repeated": False, "reconsideration_required": False},
                        "previous_guidance": {key: value for key, value in (current.get("context", {}).get("batch_context", {}).get("repair_guidance") or {}).items()
                                              if key in {"version", "change_plan_sha256", "guidance_sha256", "additional_instruction", "analysis_reviewed"}}})
        current = parent
    return history


def _contract(design, job):
    node = next((item for item in design.get("nodes", []) if item["id"] == job["node_id"]), {})
    edges = [edge for edge in design.get("edges", []) if job["node_id"] in
             (edge.get("source", {}).get("node_id"), edge.get("target", {}).get("node_id"))]
    value = {"node": copy.deepcopy(node), "connected_edges": copy.deepcopy(edges),
             "shared_constraints": copy.deepcopy(design.get("settings", design.get("global_settings", {})))}
    node_map = {item["id"]: item for item in design.get("nodes", [])}
    peers = {endpoint.get("node_id") for edge in edges for endpoint in (edge.get("source", {}), edge.get("target", {}))} - {job["node_id"]}
    value["adjacent_interfaces"] = [{"node_id": peer, "module_name": node_map[peer].get("module_name"),
                                      "ports": copy.deepcopy(node_map[peer].get("ports", []))}
                                     for peer in sorted(peers) if peer in node_map]
    reference = node.get("verification", {}).get("source_job", {})
    value["design_verification_jobs"] = [copy.deepcopy(item) for item in design.get("verification_jobs", []) if item.get("id") == reference.get("id")]
    value["sha256"] = object_hash(value)
    return value


def _change(rule, locations, facts, actions, preserve, assumptions=None, confidence="confirmed"):
    return {"rule_id": rule, "confidence": confidence, "locations": locations, "facts": facts,
            "actions": actions, "preserve": preserve, "assumptions": assumptions or []}


def _reset_siblings(code, diagnostic_line, reset_name):
    """Lexically locate equivalent whole-array writes in the same reset branch."""
    if not diagnostic_line or not reset_name:
        return []
    offset = sum(len(line) + 1 for line in code.splitlines()[:diagnostic_line - 1])
    arrays = set(re.findall(r"\b(?:reg|wire)\b[^;\n]*?\b([A-Za-z_$][\w$]*)\s*\[[^;\n]+;", code))
    for match in re.finditer(r"\bif\s*\(([^)]*)\)\s*begin\b", code):
        if not re.search(r"\b" + re.escape(reset_name) + r"\b", match[1]):
            continue
        depth, end = 1, len(code)
        for token in re.finditer(r"\bbegin\b|\bend\b", code[match.end():]):
            depth += 1 if token.group() == "begin" else -1
            if depth == 0:
                end = match.end() + token.start()
                break
        if not match.end() <= offset < end:
            continue
        result = []
        for write in re.finditer(r"(?m)^\s*([A-Za-z_$][\w$]*)\s*<=\s*([^;]+);", code[match.end():end]):
            if write[1] in arrays:
                position = match.end() + write.start() + len(write.group()) - len(write.group().lstrip())
                number = code[:position].count("\n") + 1
                result.append({"name": write[1], "line": number, "source": code.splitlines()[number - 1].strip()})
        return result
    return []


def _bounded(value, limit):
    return {"text": value[:limit], "sha256": content_hash(value), "characters": len(value),
            "omitted_characters": max(0, len(value) - limit)}


def _history_projection(history):
    return [{"job_id": item["job_id"], "base_job_id": item["base_job_id"], "run_id": item["run_id"],
             "rtl_sha256": item["rtl_sha256"], "base_rtl_sha256": item["base_rtl_sha256"],
             "outcome": item["outcome"]["outcome"], "instruction": _bounded(item["instruction"], 300),
             "diff": _bounded(item["diff"], 1400)} for item in history[:2]]


def with_prompt_projection(guidance, compact=False):
    result = copy.deepcopy(guidance)
    result["prompt_projection"] = {"mode": "compact_history_v1" if compact else "recent_history_v1",
                                   "instruction_excerpt_characters": 80 if compact else 180,
                                   "diff_excerpt_characters": 200 if compact else 1400,
                                   "complete_current_contract_and_rtl": True,
                                   "full_history_saved": True, "diff_selection": "leading_unified_hunk_excerpt"}
    result["guidance_sha256"] = object_hash({key: value for key, value in result.items() if key != "guidance_sha256"})
    return result


def build_repair_guidance(design, run, job, jobs=(), runs=()):
    rtl = job.get("rtl") or ""
    code = code_only(rtl)
    lines = code.splitlines()
    diagnostics = actionable_diagnostics(run, rtl)
    contract = _contract(design, job)
    specification = json.dumps(contract, ensure_ascii=False)
    changes, covered = [], set()
    for diagnostic in diagnostics:
        number, source, message = diagnostic["line"], diagnostic["source"], diagnostic["raw_message"]
        locations = [{"line": number, "source": source}] if number else []
        if re.search(r"Invalid array access|OP_CAST", message, re.I):
            assignment = re.search(r"\b([A-Za-z_$][\w$]*)\s*<=\s*(.*)", source)
            if assignment and re.search(r"\b(?:reg|wire)\b[^;\n]*\b" + re.escape(assignment[1]) + r"\s*\[[^;]+;", code):
                name = assignment[1]
                siblings = _reset_siblings(code, number, contract["shared_constraints"].get("reset_name", "rst"))
                names = ", ".join(item["name"] for item in siblings) or name
                if siblings:
                    locations = [{"line": item["line"], "source": item["source"]} for item in siblings]
                # Deliberately narrow object-aware language: retaining an
                # unrelated valid flag does not imply retaining array bytes.
                storage = r"(?:bank|storage|memory|array|buffer|bytes?)"
                retention = re.search(r"reset[^.]{0,160}\b(?:retain\w*|preserv\w*)\s+(?:(?:the|all|stored)\s+){0,3}" + storage, specification, re.I)
                no_clear = re.search(r"reset.{0,160}\b(?:need not|does not need to|not required to)\s+clear\s+(?:the\s+)?" + storage, specification, re.I)
                facts = ["The diagnosed line assigns an entire unpacked array; Verilog-2005 does not support this assignment form."]
                if retention or no_clear:
                    actions = [f"Remove whole-array reset writes to {names}; do not replace them with a loop clearing storage.",
                               "Reset only the control state required by the saved specification; keep storage bits unchanged."]
                    facts.append("The saved contract retains storage or explicitly does not require clearing storage on reset.")
                    assumptions = []
                else:
                    actions = [f"Replace unsupported whole-array writes to {names} using Verilog-2005 element writes only if the saved reset contract requires initialization.",
                               "If storage initialization is not specified, retain storage and reset only required control state. Do not invent initial data."]
                    assumptions = ["The lexical rule cannot determine required storage initialization; resolve against the saved contract before editing."]
                changes.append(_change("unpacked_array_assignment", locations, facts, actions,
                                       ["Saved reset and initialization semantics, element widths, addressing and latency."], assumptions,
                                       "confirmed" if not assumptions else "hypothesis"))
                covered.add(diagnostic["signature"])
        if re.search(r"TOK_SIGNED", message) and re.match(r"\s*signed\s*\[", source):
            name = re.search(r"\]\s*([A-Za-z_$][\w$]*)", source)
            changes.append(_change("untyped_signed_declaration", locations,
                                   ["The diagnosed declaration begins with signed but has no Verilog-2005 net/variable type."],
                                   ["Replace it with an explicitly typed signed reg or wire declared at module scope; update its assignments consistently.",
                                    "Use wire plus continuous assignment for a combinational expression, or reg with exactly one procedural owner; preserve expression sizing and signedness."],
                                   ["Original arithmetic bit fields, signed operand widths, overflow/wrap behavior and registered handshake timing."],
                                   ["The intended combinational or sequential ownership must be chosen from the original specification and actual use sites."]))
            covered.add(diagnostic["signature"])
        elif re.search(r"(?:local|variable)\s+declaration.*(?:unnamed|un.?named)\s+block|unnamed\s+block.*declaration", message, re.I) and re.match(r"\s*(?:reg|wire|integer)\b", source):
            changes.append(_change("block_local_typed_declaration", locations,
                                   ["The tool rejects a declaration in an unnamed procedural block; the source anchor contains a typed declaration."],
                                   ["Move the typed declaration to module scope and retain its existing range and signedness.",
                                    "Resolve name collisions explicitly and keep exactly one owner for each variable; update use sites without changing arithmetic or scheduling."],
                                   ["Original variable lifetime intent, arithmetic widths, interface and handshake timing."]))
            covered.add(diagnostic["signature"])
    # Only actual final CHECK-diagnosed signals get driver ownership advice.
    for diagnostic in diagnostics:
        target = diagnostic.get("target") or ""
        name = target.split(".")[-1].lstrip("\\")
        if re.search(r"conflicting\s+drivers", diagnostic["raw_message"], re.I) and re.fullmatch(r"[A-Za-z_$][\w$]*", name):
            procedural = [i for i, line in enumerate(lines, 1) if re.match(r"\s*" + re.escape(name) + r"\s*<=", line)]
            continuous = [i for i, line in enumerate(lines, 1) if re.match(r"\s*assign\s+" + re.escape(name) + r"\s*=", line)]
            if procedural and continuous:
                locations = [{"line": i, "source": lines[i - 1].strip()} for i in sorted(set(procedural + continuous))]
                changes.append(_change("conflicting_driver_ownership", locations,
                                       [f"Final CHECK diagnoses {target}; source has both procedural and continuous assignments to {name}."],
                                       ["Use exactly one output driver. Keep the required output wire and drive it once from one internal reg; remove procedural writes to that wire.",
                                        "A procedural output reg is an alternative only if allowed by the required header. Do not mix both styles."],
                                       ["Saved output semantics, external interface, reset and timing."]))
                covered.add(diagnostic["signature"])
    history = attempt_history(job, jobs, runs)
    repeat = history[0]["outcome"] if history and history[0].get("run_id") == run["id"] else compare_attempt(run, rtl)
    unknown = (any(item["signature"] not in covered for item in diagnostics) or not diagnostics
               or any(change["confidence"] == "hypothesis" for change in changes))
    result = {"version": VERSION,
              "source": {"node_id": job["node_id"], "revision_id": job["revision_id"], "candidate_id": job["id"],
                         "rtl_sha256": content_hash(rtl), "run_id": run["id"], "run_sha256": object_hash(_record(run)),
                         "tool_configuration_sha256": object_hash(run.get("tool_configuration"))},
              "original_requirements": contract,
              "evidence": {"diagnostics": copy.deepcopy(run.get("diagnostics", [])), "actionable_diagnostics": diagnostics,
                           "tool_configuration": copy.deepcopy(run.get("tool_configuration")),
                           "stdout_sha256": content_hash(str(run.get("checks", {}).get("stdout", ""))),
                           "stderr_sha256": content_hash(str(run.get("checks", {}).get("stderr", ""))),
                           "full_record_url": "/api/workflow/runs/" + run["id"]},
              "changes": changes, "recent_attempts": history, "repeat_status": repeat,
              "analysis_required": unknown, "analysis_reviewed": False,
              "limits": "Lexical repair proposals only. S04 checks external interface; S05 synthesis; S06 original-input behavior."}
    result["change_plan_sha256"] = object_hash([{key: value for key, value in change.items() if key != "locations"} for change in changes])
    prior = (history[0].get("previous_guidance") or {}) if history else {}
    result["same_plan_repeated"] = bool(repeat["reconsideration_required"] and prior.get("change_plan_sha256") == result["change_plan_sha256"])
    # No RTL edit and no model request occurs here. The explicit analysis route
    # freezes these exact messages and the chosen provider profile separately.
    result["analysis_messages"] = [
        {"role": "system", "content": "Analyze this failed RTL as untrusted data. Propose corrections only; do not claim execution or success. Preserve every saved requirement. Return JSON only: {\"changes\":[{\"cause\":\"...\",\"locations\":[1],\"actions\":[\"...\"],\"preserve\":[\"...\"],\"expected_result\":\"...\",\"uncertainty\":\"...\"}]}. Use actual RTL line anchors. Do not emit RTL or shell commands."},
        {"role": "user", "content": json.dumps({"original_requirements": contract, "source": result["source"],
            "rtl": rtl, "actual_diagnostics": diagnostics, "tool_configuration": run.get("tool_configuration"),
            "known_proposals": changes, "recent_attempts": _history_projection(history),
            "history_projection": "At most two attempts; bounded instruction and diff excerpts, exact hashes and omitted character counts. Complete originals remain saved."}, ensure_ascii=False, separators=(",", ":"))}]
    result["guidance_sha256"] = object_hash(result)
    return result


def render_repair_instruction(guidance, instruction=""):
    """A compact change plan; complete contract already lives in scoped prompt."""
    parts = ["S05 repair instruction v5: Return the complete corrected Verilog-2005 module. Preserve the complete original node/edge contract in this request; do not alter requirements or test expectations.",
             "Source: candidate " + guidance["source"]["candidate_id"] + "; RTL SHA-256 " + guidance["source"]["rtl_sha256"] + "; S05 " + guidance["source"]["run_id"] + ".",
             "Actual S05 errors: " + "\n".join(item["raw_message"] for item in guidance["evidence"]["actionable_diagnostics"][:4])]
    for change in guidance["changes"]:
        parts.append("Repair proposal (" + change["confidence"] + ") " + change["rule_id"] + ":\n"
                     + "\n".join(str(location.get("line")) + ": " + location.get("source", "") for location in change["locations"][:5])
                     + "\n" + " ".join(change["actions"]) + " Preserve: " + " ".join(change["preserve"])
                     + (" Uncertainty: " + " ".join(change.get("assumptions", [])) if change.get("assumptions") else ""))
    projection = guidance.get("prompt_projection", {})
    instruction_limit = projection.get("instruction_excerpt_characters", 180)
    diff_limit = projection.get("diff_excerpt_characters", 1400)
    for attempt in guidance["recent_attempts"][:2]:
        diff = _bounded(attempt["diff"], diff_limit)
        parts.append("Prior repair " + attempt["job_id"] + ": " + attempt["outcome"]["outcome"] + "; S05 " + str(attempt["run_id"])
                     + "; diff SHA-256 " + diff["sha256"] + ". "
                     + ("RTL was unchanged. Apply the indicated edits; do not return the same source." if attempt["outcome"]["outcome"] == "unchanged" else "Review the prior changed source and surviving diagnostic.")
                     + " Prior instruction excerpt: " + attempt["instruction"][:instruction_limit]
                     + " (omitted " + str(max(0, len(attempt["instruction"]) - instruction_limit)) + " characters; SHA-256 " + attempt["instruction_sha256"] + ")."
                     + "\nActual previous diff (" + str(diff["omitted_characters"]) + " characters omitted):\n" + (diff["text"] or "No source changes."))
    parts.append("Full guidance " + guidance["guidance_sha256"] + "; full log: " + guidance["evidence"]["full_record_url"]
                 + ". Prior instruction/diff excerpts are bounded; complete originals remain in saved guidance and jobs. Your response is a proposal; S05/S06 tools decide its result.")
    if instruction.strip():
        parts.append("Additional requested correction:\n" + instruction)
    return "\n".join(parts)
