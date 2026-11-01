"""Durable sequential S04 conversations. One frozen node request per model call.

The current node's complete scoped contract is never removed to make room for
history. Prior requests and answers remain exact in generation.json; packing
explicitly records which prior turns were sent or represented by the ledger.
"""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import threading
import time

from .domain import DomainError
from .provider import estimate_message_input
from .store import new_id, strict_loads, utc_now, _replace_with_windows_retry
from .store import _io_path
from .execution_submissions import PROTOCOL_VERSION, submission_view, validate_submissions
from .verification import object_hash, content_hash
from .repair_guidance import build_repair_guidance, render_repair_instruction, with_prompt_projection
from .repair_explanation import build_repair_explanation


NODE_INSTRUCTION_VERSION = "per-node-additional-instructions-v1"
REPAIR_NODE_INSTRUCTION_VERSION = "per-node-repair-instructions-v2"


def _node_instruction(shared, node_id, specific):
    """Compose only this target's optional NL; the full map stays off prompt."""
    return shared + ("\nAdditional instruction for saved node " + node_id + ":\n" + specific if specific else "")


def netlist_repair_evidence(run, synthesis, projection_version="s06-netlist-repair-evidence-v2"):
    """Versioned actual first-failure view; complete records remain saved."""
    checks = run.get("checks") or {}
    lines = (str(checks.get("stdout", "")) + "\n" + str(checks.get("stderr", ""))).splitlines()
    if projection_version not in {"s06-netlist-repair-evidence-v1", "s06-netlist-repair-evidence-v2"}:
        raise DomainError("unsupported_netlist_repair_projection", "This saved S06 repair evidence projection is unsupported.", 409)
    pattern = r"(?:^|\s)(?:FAIL|FATAL|ERROR)(?:\s|:)" if projection_version.endswith("v1") else r"HULLCIRQ_FAIL\b|(?:^|\s)(?:FAIL|FATAL|ERROR)(?:\s|:)"
    failure = next((line for line in lines if re.search(pattern, line)), None)
    plan = run.get("verification_plan") or {}
    return {"projection_version": projection_version,
            "source": {"node_id": run["node_id"], "candidate_id": run["candidate_id"], "rtl_sha256": run["rtl_sha256"],
                       "source_workflow_run_id": run["id"], "source_synthesis_run_id": synthesis["id"],
                       "netlist_sha256": run["netlist_sha256"],
                       "run_sha256": object_hash({k: v for k, v in run.items() if k not in {"freshness", "artifacts", "repair_status"}}),
                       "synthesis_sha256": object_hash({k: v for k, v in synthesis.items() if k not in {"freshness", "artifacts", "repair_status"}})},
            "actual_diagnostics": copy.deepcopy(run.get("diagnostics", [])),
            "first_failure": failure, "first_failure_sha256": content_hash(failure or ""),
            "frozen_plan": {"sha256": object_hash(plan), **{key: copy.deepcopy(plan.get(key)) for key in (
                "kind", "version", "contract_hash", "vector_hash", "reference_trace_hash", "testbench_sha256", "testbench_template_version")}},
            "stdout_sha256": content_hash(str(checks.get("stdout", ""))), "stderr_sha256": content_hash(str(checks.get("stderr", ""))),
            "full_record_url": "/api/workflow/runs/" + run["id"],
            "scope": checks.get("scope"), "limits": "Actual first observed S06 failure only. Original finite plan, expectations and full tool output remain saved and unchanged."}


def netlist_repair_instruction(evidence, instruction="", reviewed_guidance=None):
    version = 4 if reviewed_guidance is not None else 3
    # The full evidence is frozen on the plan/item/job. The model needs its
    # complete actual diagnostics and first failure, plus the exact identities
    # of current RTL, adopted S05 netlist and finite S06 plan. Repeated artifact
    # metadata is explicitly referenced, not copied into each provider input.
    prompt_evidence = {"projection_version": "s06-netlist-repair-prompt-v3",
        "source": copy.deepcopy(evidence["source"]), "actual_diagnostics": copy.deepcopy(evidence["actual_diagnostics"]),
        "first_failure": evidence["first_failure"], "first_failure_sha256": evidence["first_failure_sha256"],
        "frozen_plan_sha256": evidence["frozen_plan"]["sha256"], "full_evidence_sha256": object_hash(evidence),
        "full_record_url": evidence["full_record_url"],
        "projection_scope": "Complete current diagnostics; duplicate plan/artifact metadata remains in full saved evidence."}
    result = (f"S06 RTL repair instruction v{version}: Return the complete corrected Verilog-2005 module. "
            "Preserve the complete saved node/edge behavior, interface and current RTL context. "
            "Correct the RTL cause of the actual netlist failure. Do not alter requirements, tests, expected values or tools. "
            "The cause is unproved until S05 synthesis and S06 rerun.\n"
            + json.dumps(prompt_evidence, ensure_ascii=False, separators=(",", ":"))
            + ("\nAdditional requested correction:\n" + instruction if instruction.strip() else ""))
    if reviewed_guidance is not None:
        result += "\nReviewed repair proposals (hypotheses, not verified results):\n" + json.dumps({
            "analysis_provenance": reviewed_guidance.get("analysis_provenance"),
            "changes": reviewed_guidance.get("changes", [])}, ensure_ascii=False, separators=(",", ":"))
    return result

ACTIVE = {"Queued", "Running"}
ITEM_STATES = ACTIVE | {"Passed", "Failed", "Skipped", "Blocked", "Cancelled", "Interrupted"}
PROVIDER_IDENTITY_FIELDS = ("api_type", "base_url", "model", "execution_location", "credential_env")
FATAL_PROVIDER_CODES = {"credentials_missing", "invalid_credentials", "authentication", "model_unavailable",
                        "redirect_rejected", "credential_echo", "context_limit", "invalid_profile",
                        "connection_error", "connection", "rate_limit", "http_error", "provider_error", "transport_error"}
POLICY = {"kind": "exact_turns_with_ledger_v1", "current_contract": "complete_final_user_turn",
          "history": "newest_exact_turn_pairs_then_compact_user_and_exact_answer",
          "overflow": "explicit_hashed_ledger_no_hidden_truncation",
          "automatic_retry": False, "one_model_request_per_node": True}
POLICY_V2 = {"kind": "useful_turns_with_refs_v2", "current_contract": "complete_final_user_turn",
             "history": "newest_useful_exact_pairs_then_compact_request_exact_answer",
             "overflow": "optional_compact_reference_message_full_ledger_saved_separately",
             "empty_failed_turns": "saved_references_only_not_duplicate_prompts",
             "automatic_retry": False, "one_model_request_per_node": True}
RECOVERABLE_TRANSPORT_CODES = {"connection_error", "connection", "transport_error", "timeout", "interrupted"}


def same_provider(first, second):
    return all(first.get(key) == second.get(key) for key in PROVIDER_IDENTITY_FIELDS)


def _excerpt(value, maximum):
    text = value if type(value) is str else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return {"text": text[:maximum], "full_sha256": content_hash(text), "original_characters": len(text), "omitted_characters": max(0, len(text) - maximum)}


def _synthesis_repair_evidence_v2(run):
    """Historical projection, kept unchanged for explicit reconstruction."""
    checks = run.get("checks", {})
    diagnostics = run.get("diagnostics", [])
    selected = [{"code": str(item.get("code", ""))[:96], "severity": item.get("severity"),
                 "message": _excerpt(item.get("message", ""), 384)} for item in diagnostics[:4]]
    output = "\n".join(str(checks.get(key, "")) for key in ("stderr", "stdout"))
    lines = output.splitlines()
    indices = {index for index, line in enumerate(lines) if re.search(r"error|syntax|failed|unsupported|warning|conflicting\s+drivers|undriven", line, re.I)}
    with_context = {neighbor for index in indices for neighbor in (index, index + 1, index + 2) if neighbor < len(lines)}
    focused = "\n".join(lines[index] for index in sorted(with_context)) or output[-768:]
    return {"projection_version": "s05-repair-diagnostics-v2", "run_id": run["id"], "stage_id": run["stage_id"], "candidate_id": run["candidate_id"],
            "input_hash": run["input_hash"], "rtl_sha256": run.get("rtl_sha256"),
            "full_record_sha256": object_hash({key: value for key, value in run.items() if key not in {"freshness", "artifacts"}}),
            "full_record_url": "/api/workflow/runs/" + run["id"],
            "tool_configuration_sha256": object_hash(run.get("tool_configuration")),
            "executed": checks.get("executed"), "exit_code": checks.get("exit_code"),
            "diagnostics": selected, "diagnostic_count": len(diagnostics), "omitted_diagnostic_count": max(0, len(diagnostics) - 4),
            "all_diagnostics_sha256": object_hash(diagnostics), "focused_tool_error": _excerpt(focused, 768),
            "full_tool_output_sha256": content_hash(output), "full_tool_output_characters": len(output),
            "scope": "repair_actual_synthesis_failure_preserve_saved_requirements"}


def synthesis_repair_evidence(run, projection_version="s05-repair-diagnostics-v3"):
    """Prioritize actionable errors rather than verbose preliminary warnings.

    The complete run is retained, hash-bound and addressable. This is an
    explicitly bounded prompt view, not a replacement of the tool evidence.
    Existing plans and retries retain their already-frozen instruction text;
    they are never reprojected merely by loading the new code.
    """
    if projection_version == "s05-repair-diagnostics-v2":
        return _synthesis_repair_evidence_v2(run)
    if projection_version != "s05-repair-diagnostics-v3":
        raise DomainError("unsupported_repair_projection", "Saved synthesis repair projection is not supported; original evidence retained.")
    checks = run.get("checks", {})
    diagnostics = run.get("diagnostics", [])
    output = "\n".join(str(checks.get(key, "")) for key in ("stderr", "stdout"))
    lines, selected, seen = output.splitlines(), [], set()
    # The final CHECK pass identifies the surviving conflict. Preliminary
    # wire-assignment warnings may otherwise consume the whole prompt budget.
    for pattern, neighbors in ((r"conflicting\s+drivers|undriven", 3),
                               (r"\berror\b|syntax\s+error|failed|unsupported", 1)):
        for index in reversed(range(len(lines))):
            line = lines[index]
            if line not in seen and re.search(pattern, line, re.I):
                seen.add(line)
                selected.extend(lines[index:index + neighbors])
    if not selected:
        selected = [line for line in lines if re.search(r"\bwarning\b", line, re.I)]
    focused = "\n".join(selected).strip() or output[-400:].strip()
    if not focused:
        focused = "\n".join(str(item.get("message", "")) for item in diagnostics)
    return {"projection_version": projection_version,
            "run_id": run["id"], "candidate_id": run["candidate_id"],
            "full_record_sha256": object_hash({key: value for key, value in run.items() if key not in {"freshness", "artifacts"}}),
            "full_record_url": "/api/workflow/runs/" + run["id"],
            "executed": checks.get("executed"), "exit_code": checks.get("exit_code"),
            "diagnostic_codes": [str(item.get("code", ""))[:96] for item in diagnostics[:4]],
            "diagnostic_count": len(diagnostics), "focused_tool_error": focused[:400],
            "full_tool_output_characters": len(output),
            "omissions": "Bounded codes and prioritized 400-character excerpt. Full diagnostics and tool output remain at full_record_url, bound by full_record_sha256."}


def _conflicting_driver_guidance(run, rtl):
    """Bounded lexical guidance, only for a tool-diagnosed simple signal.

    This is not a Verilog parser or a new validation result. Ignore comments
    and strings, and require both line-start assignment styles in the actual
    repair base. Final CHECK output takes precedence over preliminary checks.
    """
    if type(rtl) is not str:
        return ""
    stdout = str(run.get("checks", {}).get("stdout", ""))
    checks = list(re.finditer(r"(?m)^\d+(?:\.\d+)*\. Executing CHECK pass", stdout))
    output = stdout[checks[-1].start():] if checks else stdout
    diagnosed = list(dict.fromkeys(re.findall(
        r"multiple\s+conflicting\s+drivers\s+for\s+[^.\s]+\.\\?([A-Za-z_$][A-Za-z_0-9$]*)\s*:", output, re.I)))
    # Preserve line numbering while masking non-code text. Escaped identifiers,
    # packed slices and assignments embedded in other statements are outside
    # this deliberately narrow source hint; no conclusion is inferred for them.
    code = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"',
                  lambda match: "\n" * match.group().count("\n"), rtl, flags=re.S)
    evidence = []
    for name in diagnosed[:3]:
        procedural, continuous = [], []
        for number, line in enumerate(code.splitlines(), 1):
            if re.match(r"\s*" + re.escape(name) + r"\s*<=", line):
                procedural.append(number)
            if re.match(r"\s*assign\s+" + re.escape(name) + r"\s*=", line):
                continuous.append(number)
        if procedural and continuous:
            evidence.append(f"{name} <= at lines {','.join(map(str, procedural[:8]))}; assign {name} at lines {','.join(map(str, continuous[:8]))}")
    if not evidence:
        return ""
    return ("Driver correction (lexical evidence; confirm in RTL): " + "; ".join(evidence)
            + ". Use exactly one output driver. Keep output wire and drive it once from one internal reg; remove procedural writes to that wire. "
              "A procedural output reg is an alternative only if allowed by the required header. Do not mix both styles.")


def synthesis_repair_instruction(run, rtl, instruction="", guidance=None):
    """v4 adds concrete source guidance without rewriting saved v2/v3 text.

    The unchanged v3 diagnostic projection still binds the full original run.
    Only fresh plans use this instruction. Retries preserve their frozen text.
    """
    if guidance is not None:
        return render_repair_instruction(guidance, instruction)
    evidence = synthesis_repair_evidence(run)
    parts = ["S05 repair instruction v4: Return the complete corrected Verilog-2005 module. Preserve saved behavior, constraints, external interface and original test expectations."]
    guidance = _conflicting_driver_guidance(run, rtl)
    if guidance:
        parts.append(guidance)
    parts.append("S05 source evidence:\n" + json.dumps(evidence, ensure_ascii=False, separators=(",", ":")))
    if instruction.strip():
        parts.append("Additional requested correction:\n" + instruction)
    return "\n".join(parts)


def pack_batch_context(base, prior_jobs, profile, metadata):
    """Pure, reconstructible packing; preserves full current scoped contract."""
    if metadata.get("packing_policy_version") == POLICY_V2["kind"]:
        return _pack_useful_context_v2(base, prior_jobs, profile, metadata)
    if metadata.get("packing_policy_version") not in (None, POLICY["kind"]):
        raise DomainError("unsupported_context_policy", "Saved conversation packing policy is unsupported; original history retained.")
    result = copy.deepcopy(base)
    ledger = [{"job_id": job["id"], "node_id": job["node_id"], "context_id": job["context_id"],
               "request_messages_sha256": object_hash(job["context"]["messages"]),
               "answer_sha256": content_hash(job["raw_content"]),
               "rtl_sha256": content_hash(job["rtl"]) if job.get("rtl") else None,
               "execution_status": job["execution_status"], "validation_status": job["validation_status"],
               "profile_revision_id": job["profile_revision_id"],
               "module": job["context"].get("interface", {}).get("module_name"),
               "public_port_names": [port["name"] for port in job["context"].get("interface", {}).get("ports", [])][:8],
               "public_port_count": len(job["context"].get("interface", {}).get("ports", [])),
               "public_interface_sha256": object_hash(job["context"].get("interface", {})),
               "requested_correction": _excerpt(job.get("instruction", ""), 160),
               "result_diagnostics": _excerpt(job.get("diagnostics", []), 160)}
              for job in prior_jobs]
    system, current = base["messages"][0], base["messages"][1:]
    columns = list(ledger[0]) if ledger else []
    projected_ledger = {"kind": "full_semantic_rows", "columns": columns, "rows": [[entry[key] for key in columns] for entry in ledger]}
    if len(json.dumps(projected_ledger, ensure_ascii=False).encode("utf-8")) > 2048:
        # Bound conversation overhead independently of the number of nodes.
        # Every complete row stays in durable metadata. Older rows are carried
        # as an explicitly hashed segment plus their node/module/outcome list.
        newest = ledger[-2:]
        older = ledger[:-2]
        projected_ledger = {"kind": "older_hashed_segment_and_recent_semantics", "full_ledger_sha256": object_hash(ledger),
            "older_segment_sha256": object_hash(older), "older_record_count": len(older),
            "older_node_outcomes": [[entry["node_id"], entry["module"], entry["execution_status"], entry["validation_status"]] for entry in older],
            "recent": [{"job_id": entry["job_id"], "node_id": entry["node_id"], "module": entry["module"],
                        "ports": entry["public_port_names"], "port_count": entry["public_port_count"],
                        "execution_status": entry["execution_status"], "validation_status": entry["validation_status"],
                        "correction_excerpt": entry["requested_correction"]["text"],
                        "diagnostic_excerpt": entry["result_diagnostics"]["text"], "full_record_sha256": object_hash(entry)} for entry in newest],
            "omissions": "Older correction/interface details and complete turns are retained in the saved full ledger and jobs; only their outcomes and aggregate hash are sent here."}
    ledger_message = {"role": "user", "content": "Sequential node conversation ledger: this is a bounded semantic summary with hashed full saved history, not the full transcript. Prior results are context, not proof; the complete current scoped contract below is authoritative. Omitted port names and excerpt characters stay in the original job.\n" + json.dumps(projected_ledger, ensure_ascii=False, separators=(",", ":"))}
    history = []
    packing = []
    budget = profile["context_window"] - profile["max_output_tokens"]
    def messages(turns):
        return [system] + ([ledger_message] if prior_jobs else []) + turns + current
    if prior_jobs and estimate_message_input(messages([])) > budget:
        # A long current node contract still takes priority. Retain meaningful
        # prior node outcomes/corrections with exact hashes, rather than filling
        # its remaining budget with repeated hash-field names and port detail.
        projected_ledger = {"kind": "budget_compact_semantic_segment", "full_ledger_sha256": object_hash(ledger),
            "prior_node_outcomes": [[entry["node_id"], entry["module"], entry["execution_status"], entry["validation_status"]] for entry in ledger],
            "last_correction_excerpt": ledger[-1]["requested_correction"]["text"][:80],
            "last_diagnostic_excerpt": ledger[-1]["result_diagnostics"]["text"][:80],
            "omissions": "Full prior prompts, answers, public ports and longer correction/diagnostic text are saved in the full ledger/jobs, not all sent here."}
        ledger_message["content"] = "Prior node conversation semantic summary; current complete node contract below is authoritative.\n" + json.dumps(projected_ledger, ensure_ascii=False, separators=(",", ":"))
    if estimate_message_input(messages([])) > budget:
        raise DomainError("context_budget", "Complete node contract plus the saved conversation ledger exceeds the context window. Increase a verified context window or reduce the output limit, then prepare a new batch.", 422)
    for job in reversed(prior_jobs):
        request = [copy.deepcopy(message) for message in job["context"]["messages"] if message["role"] == "user"][-1:]
        answer = {"role": "assistant", "content": job["raw_content"]}
        compact = {"role": "user", "content": "Previous node request (complete original request retained under context_id): " + json.dumps({"node_id": job["node_id"], "context_id": job["context_id"], "operation": job["operation"], "instruction": job["instruction"]}, ensure_ascii=False, separators=(",", ":"))}
        chosen, kind = [], "ledger_only"
        for pair, label in ((request + [answer], "exact_user_and_assistant"), ([compact, answer], "compact_user_exact_assistant")):
            if estimate_message_input(messages(pair + history)) <= budget:
                chosen, kind = pair, label
                break
        history = chosen + history
        packing.insert(0, {"job_id": job["id"], "representation": kind,
                           "sent_turns_sha256": object_hash(chosen),
                           "original_messages_sha256": object_hash(job["context"]["messages"]),
                           "original_answer_sha256": content_hash(job["raw_content"])})
    result["messages"] = messages(history)
    result["batch_context"] = {**copy.deepcopy(metadata), "policy": copy.deepcopy(POLICY), "ledger": ledger,
                               "ledger_projection": projected_ledger, "packing": packing, "base_messages_sha256": object_hash(base["messages"])}
    result["provider_input_estimated_tokens"] = estimate_message_input(result["messages"])
    return result


def _context_budget(base_messages, messages, profile, ledger_messages=None):
    base_tokens = estimate_message_input(base_messages)
    total = estimate_message_input(messages)
    with_ledger = estimate_message_input(ledger_messages or base_messages)
    output, window = profile["max_output_tokens"], profile["context_window"]
    return {"scope": "packed_request", "estimation_method": "conservative_serialized_messages_utf8_upper_bound",
            "base_input_estimated_tokens": base_tokens,
            "ledger_input_estimated_tokens": with_ledger - base_tokens,
            "retained_history_input_estimated_tokens": total - with_ledger,
            "provider_input_estimated_tokens": total, "max_output_tokens": output,
            "context_window": window, "maximum_output_tokens": max(0, window - total),
            "total_estimated_tokens": total + output, "fits": total + output <= window}


def _pack_useful_context_v2(base, prior_jobs, profile, metadata):
    """New plans only: failed empty requests consume durable references, not input.

    V1 remains byte-reconstructible above. All omitted original prompts/answers
    are hash-bound in metadata. The optional in-prompt ledger is admitted only
    when it fits; the complete current source is never shortened.
    """
    result = copy.deepcopy(base)
    ledger = [{"job_id": job["id"], "node_id": job["node_id"], "context_id": job["context_id"],
               "request_messages_sha256": object_hash(job["context"]["messages"]),
               "answer_sha256": content_hash(job["raw_content"]),
               "rtl_sha256": content_hash(job["rtl"]) if job.get("rtl") else None,
               "execution_status": job["execution_status"], "validation_status": job["validation_status"],
               "error_code": (job.get("error") or {}).get("code")}
              for job in prior_jobs]
    system, current = base["messages"][0], base["messages"][1:]
    history, prefix, packing = [], [], []
    budget = profile["context_window"] - profile["max_output_tokens"]
    def messages(turns):
        return [system] + prefix + turns + current
    if estimate_message_input(messages([])) > budget:
        error = DomainError("context_budget", "The complete current request exceeds the configured input budget. Reduce the output limit or increase a verified context window.", 422)
        error.context_budget = _context_budget(base["messages"], messages([]), profile)
        raise error
    projected = {"kind": "saved_history_references", "history_count": len(ledger), "full_ledger_sha256": object_hash(ledger),
                 "omissions": "Empty failed turns and omitted prompts/answers remain saved; no omitted text is represented as an exact conversation turn."}
    if ledger:
        candidate = {"role": "user", "content": "Saved prior conversation references; the complete current request below is authoritative.\n" + json.dumps(projected, ensure_ascii=False, separators=(",", ":"))}
        prefix = [candidate]
        if estimate_message_input(messages([])) > budget:
            prefix = []
            projected["sent"] = False
        else:
            projected["sent"] = True
    else:
        projected["sent"] = False
    ledger_messages = messages([])
    for job in reversed(prior_jobs):
        chosen, kind = [], "saved_reference_only"
        if job.get("raw_content", "").strip():
            request = [copy.deepcopy(message) for message in job["context"]["messages"] if message["role"] == "user"][-1:]
            answer = {"role": "assistant", "content": job["raw_content"]}
            compact = {"role": "user", "content": "Previous node request reference: " + json.dumps({"node_id": job["node_id"], "context_id": job["context_id"], "operation": job["operation"]}, ensure_ascii=False, separators=(",", ":"))}
            for pair, label in ((request + [answer], "exact_user_and_assistant"), ([compact, answer], "compact_user_exact_assistant")):
                if estimate_message_input(messages(pair + history)) <= budget:
                    chosen, kind = pair, label
                    break
        history = chosen + history
        packing.insert(0, {"job_id": job["id"], "representation": kind,
                           "sent_turns_sha256": object_hash(chosen),
                           "original_messages_sha256": object_hash(job["context"]["messages"]),
                           "original_answer_sha256": content_hash(job["raw_content"])})
    result["messages"] = messages(history)
    result["context_budget"] = _context_budget(base["messages"], result["messages"], profile, ledger_messages)
    result["batch_context"] = {**copy.deepcopy(metadata), "policy": copy.deepcopy(POLICY_V2), "ledger": ledger,
                               "ledger_projection": projected, "packing": packing,
                               "base_messages_sha256": object_hash(base["messages"]),
                               "context_budget": copy.deepcopy(result["context_budget"])}
    result["provider_input_estimated_tokens"] = result["context_budget"]["provider_input_estimated_tokens"]
    return result


class GenerationBatchManager:
    def __init__(self, store, generation, workflow):
        self.store, self.generation, self.workflow = store, generation, workflow
        self.path = store.state_path.parent / "generation_batches.json"
        self.lock, self._worker = threading.RLock(), None
        self._cancel, self._closed = threading.Event(), False
        self._storage_error = None
        self._state = {"generation_batch_store_version": "0.1", "plans": [], "batches": []}
        if _io_path(self.path).exists():
            try:
                self._state = strict_loads(_io_path(self.path).read_text(encoding="utf-8"))
                self._validate_saved()
                self._committed = copy.deepcopy(self._state)
            except (OSError, ValueError, KeyError, TypeError, DomainError) as error:
                raise DomainError("invalid_generation_batch_store", "Sequential generation history is inconsistent; original file preserved.") from error
            changed = False
            for batch in self._state["batches"]:
                if batch["execution_status"] in ACTIVE:
                    for index, item in enumerate(batch["items"]):
                        if item.get("job_id") is None:
                            # A restart may occur after generation.json commits
                            # the child but before this scheduler commits its ID.
                            # Reconnect to that exact child; never send it again.
                            candidates = [job for job in generation._state["jobs"] if job.get("batch_id") == batch["id"] and job.get("batch_index") == index]
                            if len(candidates) > 1:
                                raise DomainError("invalid_generation_batch_store", "Sequential history contains multiple children for one node; original jobs preserved.")
                            if candidates:
                                child = candidates[0]
                                if any(child[key] != item[key] for key in ("node_id", "operation", "base_job_id", "instruction")):
                                    raise DomainError("invalid_generation_batch_store", "Interrupted child does not match its saved node request; original jobs preserved.")
                                item["job_id"] = child["id"]
                    batch.update(execution_status="Interrupted", validation_status="Not Checked", finished_at=utc_now(), error={"code": "interrupted", "message": "Service restarted; no model request was resent. Prepare a new batch explicitly."})
                    for item in batch["items"]:
                        if item["status"] in ACTIVE:
                            item.update(status="Interrupted", reason="Service restarted; not resent.")
                    changed = True
            if changed:
                self._persist()
        # No empty file is written merely by opening a pre-existing project.
        self._committed = copy.deepcopy(self._state)

    def _validate_saved(self):
        state = self._state
        def saved_job(identifier):
            # Validate the saved conversation chain, without deriving current
            # UI readiness for every child in the historical batches.
            getter = getattr(self.generation, "_stored_job", None)
            if getter is None:
                return self.generation.job(identifier)
            with self.generation.lock:
                return getter(identifier)
        if state.get("generation_batch_store_version") != "0.1" or type(state.get("plans")) is not list or type(state.get("batches")) is not list:
            raise ValueError("Invalid store")
        plans = {}
        for plan in state["plans"]:
            if plan.get("plan_id") in plans or plan.get("plan_id") != "generation-plan-" + object_hash({key: value for key, value in plan.items() if key != "plan_id"}):
                raise ValueError("Plan changed")
            if self.store.snapshot(plan["revision_id"]) is None:
                raise ValueError("Missing source")
            inputs = plan.get("instruction_inputs")
            if inputs is not None:
                version = inputs.get("version") if type(inputs) is dict else None
                supported_mode = ((version == NODE_INSTRUCTION_VERSION and plan["mode"] == "generate")
                                  or (version == REPAIR_NODE_INSTRUCTION_VERSION and plan["mode"] in {"synthesis_repair", "netlist_repair"}))
                if (type(inputs) is not dict or set(inputs) != {"version", "shared", "nodes"}
                        or not supported_mode or plan.get("retry_of_batch_id") is not None
                        or type(inputs["shared"]) is not str or len(inputs["shared"].encode("utf-8")) > 8192
                        or type(inputs["nodes"]) is not dict
                        or any(type(key) is not str or type(value) is not str or len(value.encode("utf-8")) > 8192
                               for key, value in inputs["nodes"].items())
                        or set(inputs["nodes"]) - {item["node_id"] for item in plan["items"]}):
                    raise ValueError("Per-node instruction inputs changed")
                for item in plan["items"]:
                    effective = _node_instruction(inputs["shared"], item["node_id"], inputs["nodes"].get(item["node_id"], ""))
                    expected = effective
                    # V1 generation remains byte-compatible. V2 repairs retain
                    # the frozen actual-error guidance/evidence and render only
                    # this target's user hint. Never reconstruct old guidance
                    # from a newer live run or merge the complete hint map.
                    if version == REPAIR_NODE_INSTRUCTION_VERSION:
                        if plan["mode"] == "synthesis_repair" and item.get("repair_guidance"):
                            expected = render_repair_instruction(item["repair_guidance"], effective)
                        elif plan["mode"] == "netlist_repair" and item.get("netlist_repair_evidence"):
                            expected = netlist_repair_instruction(item["netlist_repair_evidence"], effective, item.get("repair_guidance"))
                    if item["instruction"] != expected:
                        raise ValueError("Per-node instruction inputs changed")
            plans[plan["plan_id"]] = plan
        ids, requests = set(), set()
        for batch in state["batches"]:
            if (batch["id"] in ids or batch["request_id"] in requests or batch["plan_id"] not in plans
                    or batch["record_hash"] != object_hash({key: value for key, value in batch.items() if key != "record_hash"})
                    or batch["execution_status"] not in ACTIVE | {"Completed", "Cancelled", "Failed", "Interrupted"}):
                raise ValueError("Batch changed")
            ids.add(batch["id"]); requests.add(batch["request_id"])
            plan = plans[batch["plan_id"]]
            if any(batch[key] != plan[key] for key in ("revision_id", "profile_revision_id", "mode")) or len(batch["items"]) != len(plan["items"]):
                raise ValueError("Batch source changed")
            earlier = list(plan.get("seed_job_ids", []))
            for index, (item, source) in enumerate(zip(batch["items"], plan["items"])):
                if item["status"] not in ITEM_STATES or any(item[key] != source[key] for key in ("node_id", "operation", "base_job_id", "source_workflow_run_id", "instruction")):
                    raise ValueError("Item source changed")
                if source.get("netlist_repair_evidence") != item.get("netlist_repair_evidence"):
                    raise ValueError("Netlist repair evidence changed")
                if item.get("job_id"):
                    job = saved_job(item["job_id"])
                    meta = job["context"].get("batch_context", {})
                    if (job.get("batch_id") != batch["id"] or meta.get("index") != index or meta.get("prior_job_ids") != earlier
                            or any(job[key] != item[key] for key in ("node_id", "operation", "base_job_id", "instruction"))
                            or job["revision_id"] != batch["revision_id"] or job["profile_revision_id"] != batch["profile_revision_id"]):
                        raise ValueError("Job chain changed")
                    if source.get("netlist_repair_evidence") != meta.get("netlist_repair_evidence"):
                        raise ValueError("Netlist repair job evidence changed")
                    earlier.append(job["id"])
        batches = {batch["id"]: batch for batch in state["batches"]}
        for plan in state["plans"]:
            if plan.get("retry_of_batch_id"):
                parent = batches.get(plan["retry_of_batch_id"])
                if parent is None:
                    raise ValueError("Missing conversation retry parent")
                parent_plan = plans[parent["plan_id"]]
                seed_ids = list(parent_plan.get("seed_job_ids", [])) + [item["job_id"] for item in parent["items"] if item.get("job_id")]
                if (plan.get("seed_job_ids") != seed_ids or parent["revision_id"] != plan["revision_id"]
                        or not same_provider(parent_plan["profile"], plan["profile"])):
                    raise ValueError("Conversation retry lineage changed")
                for item in plan["items"]:
                    parent_item = next((source for source in parent_plan["items"] if source["node_id"] == item["node_id"]), None)
                    if parent_item is None or any(item[key] != parent_item[key] for key in ("operation", "base_job_id", "source_workflow_run_id", "source_workflow_sha256")) or not item["instruction"].startswith(parent_item["instruction"]):
                        raise ValueError("Conversation retry repair source changed")
            elif plan.get("seed_job_ids"):
                raise ValueError("Unlinked conversation seeds")
        validate_submissions(state)

    def _persist(self):
        previous = getattr(self, "_committed", None)
        name = None
        try:
            for batch in self._state["batches"]:
                batch["record_hash"] = object_hash({key: value for key, value in batch.items() if key != "record_hash"})
            raw = json.dumps(self._state, ensure_ascii=False, allow_nan=False, indent=2) + "\n"
            _io_path(self.path.parent).mkdir(parents=True, exist_ok=True)
            descriptor, name = tempfile.mkstemp(prefix=".generation-batches-", suffix=".tmp", dir=_io_path(self.path.parent))
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(raw); handle.flush(); os.fsync(handle.fileno())
            _replace_with_windows_retry(name, _io_path(self.path))
            self._committed = copy.deepcopy(self._state)
            self._storage_error = None
        except (OSError, TypeError, ValueError):
            if previous is not None:
                self._state = copy.deepcopy(previous)
            self._storage_error = {"code": "storage_error", "message": "Batch history could not be saved. Stop and inspect the retained generation jobs before retrying."}
            raise
        finally:
            if name and os.path.exists(_io_path(name)):
                os.unlink(_io_path(name))

    def is_active(self):
        with self.lock:
            return bool(self._worker and self._worker.is_alive() or any(batch["execution_status"] in ACTIVE for batch in self._state["batches"]))

    def _plan(self, plan_id):
        plan = next((plan for plan in self._state["plans"] if plan["plan_id"] == plan_id), None)
        if plan is None:
            raise DomainError("generation_plan_not_found", "Prepare a sequential generation preview first.", 404)
        return plan

    def _batch(self, identifier):
        batch = next((batch for batch in self._state["batches"] if batch["id"] == identifier), None)
        if batch is None:
            raise DomainError("generation_batch_not_found", "Sequential generation batch does not exist.", 404)
        return batch

    def _current_sources(self):
        return self.generation.node_sources()

    def _repair_source(self, node_id, latest_id):
        with self.workflow.lock:
            runs = [run for run in self.workflow._state["runs"] if run["node_id"] == node_id and run["stage_id"] == "local_synthesis"]
            identifier = runs[-1]["id"] if runs else None
        run = self.workflow.run(identifier) if identifier else None
        if not run or run["candidate_id"] != latest_id or run["freshness"] != "Current" or run["execution_status"] != "Completed" or run["validation_status"] != "Failed" or run.get("checks", {}).get("executed") is not True:
            return None
        return run

    def _netlist_repair_source(self, node_id, candidate_id, allow_transport_recovery=False):
        with self.workflow.lock:
            identifiers = [run["id"] for run in self.workflow._state["runs"]
                           if run["node_id"] == node_id and run["stage_id"] == "local_netlist_simulation"]
        run = self.workflow.run(identifiers[-1]) if identifiers else None
        if (not run or run["candidate_id"] != candidate_id
                or run.get("execution_status") != "Completed" or run.get("validation_status") != "Failed"
                or run.get("checks", {}).get("executed") is not True or not run.get("verification_plan")
                or not run.get("prior_run_id")):
            return None
        if run.get("freshness") != "Current":
            # An explicitly recognized empty failed repair may supersede the
            # selected-candidate view, without changing any source requirement.
            if (not allow_transport_recovery
                    or self.workflow._state.get("node_inputs", {}).get(node_id) != run.get("input_hash")):
                return None
            run.pop("blocked_reason", None)
        synthesis = self.workflow.run(run["prior_run_id"])
        if (synthesis["stage_id"] != "local_synthesis" or synthesis["candidate_id"] != candidate_id
                or synthesis.get("freshness") != "Current" or synthesis.get("execution_status") != "Completed"
                or synthesis.get("validation_status") != "Passed" or synthesis.get("review_status") != "Accepted"
                or not synthesis.get("netlist") or synthesis.get("netlist_sha256") != run.get("netlist_sha256")
                or content_hash(synthesis["netlist"]) != run.get("netlist_sha256")):
            return None
        return run, synthesis

    def _netlist_repair_identity(self, node_id, latest_id):
        pair = self._netlist_repair_source(node_id, latest_id)
        if pair:
            return {"node_id": node_id, "latest_job_id": latest_id, "base_job_id": latest_id,
                    "source_workflow_run_id": pair[0]["id"], "recovery": None}
        with self.generation.lock:
            jobs = [job for job in self.generation._state["jobs"] if job["node_id"] == node_id]
            if not jobs or jobs[-1]["id"] != latest_id:
                return None
            index = next((i for i in reversed(range(len(jobs))) if jobs[i].get("rtl")), None)
            if index is None or index == len(jobs) - 1:
                return None
            base, failures = jobs[index], jobs[index + 1:]
            if any(job.get("rtl") is not None or job.get("raw_content", "").strip()
                   or job.get("execution_status") not in {"Failed", "Interrupted"}
                   or (job.get("error") or {}).get("code") not in RECOVERABLE_TRANSPORT_CODES
                   or job.get("operation") != "repair" or job.get("base_job_id") != base["id"]
                   or job.get("revision_id") != base["revision_id"] or job.get("input_hash") != base["input_hash"]
                   for job in failures):
                return None
            failed_ids = [job["id"] for job in failures]
        pair = self._netlist_repair_source(node_id, base["id"], allow_transport_recovery=True)
        if pair is None or any(job.get("context", {}).get("batch_context", {}).get("source_workflow_run_id") != pair[0]["id"] for job in failures):
            return None
        return {"node_id": node_id, "latest_job_id": latest_id, "base_job_id": base["id"],
                "source_workflow_run_id": pair[0]["id"], "recovery": {
                    "kind": "no_rtl_netlist_repair_transport_failure_v1", "base_job_id": base["id"],
                    "source_workflow_run_id": pair[0]["id"], "failed_job_ids": failed_ids,
                    "failed_jobs_sha256": object_hash([{key: job.get(key) for key in ("id", "context_id", "error", "execution_status")} for job in failures])}}

    def netlist_repair_sources(self):
        result = []
        for node_id, source in self._current_sources().items():
            identity = self._netlist_repair_identity(node_id, source["latest_job_id"])
            if identity and identity["base_job_id"] == source.get("accepted_job_id"):
                run, synthesis = self._netlist_repair_source(node_id, identity["base_job_id"], allow_transport_recovery=bool(identity.get("recovery")))
                evidence = netlist_repair_evidence(run, synthesis)
                result.append({**identity, "source_synthesis_run_id": synthesis["id"], "netlist_repair_evidence": evidence})
        return result

    def netlist_repair_guidance_for_run(self, run_id, evidence_version=None):
        """Normalize an exact current S06 failure for explicit model analysis."""
        run = self.workflow.run(run_id)
        source = self._current_sources().get(run.get("node_id"), {})
        identity = self._netlist_repair_identity(run.get("node_id"), source.get("latest_job_id"))
        if (identity is None or identity["base_job_id"] != run.get("candidate_id")
                or identity["source_workflow_run_id"] != run_id or source.get("accepted_job_id") != run.get("candidate_id")):
            raise DomainError("repair_source_changed", "Use the latest executed S06 failure for this adopted RTL and S05 netlist.", 409)
        pair = self._netlist_repair_source(run["node_id"], run["candidate_id"], allow_transport_recovery=bool(identity.get("recovery")))
        if pair is None:
            raise DomainError("repair_source_unavailable", "Current S06 failure evidence is unavailable.", 409)
        run, synthesis = pair
        job = self.generation.job(run["candidate_id"])
        with self.generation.lock:
            jobs = copy.deepcopy(self.generation._state["jobs"])
        with self.workflow.lock:
            runs = copy.deepcopy(self.workflow._state["runs"])
        result = build_repair_guidance(self.store.snapshot(job["revision_id"]), run, job, jobs, runs)
        evidence = netlist_repair_evidence(run, synthesis, evidence_version or "s06-netlist-repair-evidence-v2")
        result["version"] = "s06-repair-guidance-v1"
        result["source"].update(stage_id="local_netlist_simulation", source_synthesis_run_id=synthesis["id"],
                                netlist_sha256=run["netlist_sha256"], verification_plan_sha256=evidence["frozen_plan"]["sha256"])
        result["changes"] = []
        if evidence["first_failure"]:
            result["evidence"]["actionable_diagnostics"].append({"raw_message": evidence["first_failure"], "line": None,
                "source": "", "signature": evidence["first_failure_sha256"], "scope": "observed_netlist_failure_no_rtl_cause_inferred"})
        result["evidence"]["netlist_repair_evidence"] = evidence
        result.update(analysis_required=True, analysis_reviewed=False, same_plan_repeated=False,
                      limits="S06 finite saved-plan observation. Proposed RTL causes remain hypotheses until S05 and S06 rerun.")
        result["change_plan_sha256"] = object_hash([])
        result["guidance_sha256"] = object_hash({key: value for key, value in result.items() if key != "guidance_sha256"})
        return result

    def _repair_identity(self, node_id, latest_id):
        """Only empty transport failures may retain the exact earlier RTL source.

        This is an explicit recovery identity, not a latest-valid-RTL fallback.
        A new candidate (including a failed interface candidate) always wins.
        """
        run = self._repair_source(node_id, latest_id)
        if run:
            return {"node_id": node_id, "latest_job_id": latest_id, "base_job_id": latest_id,
                    "source_workflow_run_id": run["id"], "recovery": None}
        with self.generation.lock:
            # The read view is polled by the GUI. Inspect immutable identity
            # fields, not whole multi-megabyte prior conversation snapshots.
            keys = ("id", "node_id", "rtl", "raw_content", "execution_status", "error", "operation", "base_job_id",
                    "revision_id", "input_hash", "context_id", "rtl_sha256", "raw_content_sha256")
            jobs = [{**{key: job.get(key) for key in keys},
                     "context": {"batch_context": {"source_workflow_run_id": job.get("context", {}).get("batch_context", {}).get("source_workflow_run_id")}}}
                    for job in self.generation._state["jobs"] if job["node_id"] == node_id]
        if not jobs or jobs[-1]["id"] != latest_id:
            return None
        base_index = next((index for index in reversed(range(len(jobs))) if jobs[index].get("rtl")), None)
        if base_index is None or base_index == len(jobs) - 1:
            return None
        base, failures = jobs[base_index], jobs[base_index + 1:]
        run = self._repair_source(node_id, base["id"])
        if run is None or base["revision_id"] != self.store.envelope()["revision"]["id"]:
            return None
        if any(job.get("rtl") is not None or job.get("raw_content", "").strip()
               or job["execution_status"] not in {"Failed", "Interrupted"}
               or (job.get("error") or {}).get("code") not in RECOVERABLE_TRANSPORT_CODES
               or job["operation"] != "repair" or job.get("base_job_id") != base["id"]
               or job["revision_id"] != base["revision_id"] or job["input_hash"] != base["input_hash"]
               or job["context"].get("batch_context", {}).get("source_workflow_run_id") != run["id"]
               for job in failures):
            return None
        recovery = {"kind": "no_rtl_transport_failure_v1", "base_job_id": base["id"],
                    "source_workflow_run_id": run["id"], "failed_job_ids": [job["id"] for job in failures],
                    "failed_jobs_sha256": object_hash([{key: job.get(key) for key in ("id", "context_id", "input_hash", "revision_id", "base_job_id", "error", "execution_status", "rtl_sha256", "raw_content_sha256")} for job in failures])}
        return {"node_id": node_id, "latest_job_id": latest_id, "base_job_id": base["id"],
                "source_workflow_run_id": run["id"], "recovery": recovery}

    def repair_sources(self):
        """Small authoritative read view for S04/S05 recovery controls."""
        result = []
        for node_id, source in self._current_sources().items():
            identity = self._repair_identity(node_id, source["latest_job_id"])
            if identity:
                # Reading why synthesis failed must not require POSTing a new
                # repair plan. These facts are display-only and never saved to
                # generation history or inserted into a provider request.
                try:
                    with self.generation.lock:
                        # Only immutable repair fields are needed. Decorating
                        # all old jobs requalifies unrelated readiness plans.
                        jobs = [{**{key: copy.deepcopy(job.get(key)) for key in ("id", "node_id", "revision_id", "operation", "base_job_id", "rtl", "instruction")},
                                 "context": {"batch_context": {"repair_guidance": {
                                     key: copy.deepcopy(value) for key, value in (job.get("context", {}).get("batch_context", {}).get("repair_guidance") or {}).items()
                                     if key in {"version", "change_plan_sha256", "guidance_sha256", "additional_instruction", "analysis_reviewed"}}}}}
                                for job in self.generation._state["jobs"] if job["node_id"] == node_id]
                    with self.workflow.lock:
                        runs = [copy.deepcopy(run) for run in self.workflow._state["runs"] if run["node_id"] == node_id and run["stage_id"] == "local_synthesis"]
                    job = next(job for job in jobs if job["id"] == identity["base_job_id"])
                    run = next(run for run in runs if run["id"] == identity["source_workflow_run_id"])
                    source_keys = {"node_id": node_id, "revision_id": job["revision_id"], "candidate_id": job["id"],
                                   "rtl_sha256": content_hash(job["rtl"]), "run_id": run["id"],
                                   "run_sha256": object_hash({key: value for key, value in run.items() if key not in {"freshness", "artifacts", "repair_status"}})}
                    with self.lock:
                        guidance = next((item["repair_guidance"] for plan in reversed(self._state["plans"]) for item in plan["items"]
                                         if item.get("repair_guidance") and all(item["repair_guidance"].get("source", {}).get(key) == value for key, value in source_keys.items())), None)
                    if guidance is None:
                        guidance = build_repair_guidance(self.store.snapshot(job["revision_id"]), run, job, jobs, runs)
                    identity["repair_explanation"] = build_repair_explanation(guidance, run, job, jobs, runs)
                except DomainError:
                    # Setup failures or a changed source keep their existing
                    # blocker. Do not manufacture a circuit explanation.
                    pass
                result.append(identity)
        return result

    def repair_guidance_for_run(self, run_id, instruction=""):
        """Read-only source extraction shared by single/batch repair and analysis."""
        run = self.workflow.run(run_id)
        if (run.get("stage_id") != "local_synthesis" or run.get("execution_status") != "Completed"
                or run.get("validation_status") != "Failed" or run.get("checks", {}).get("executed") is not True):
            raise DomainError("repair_source_unavailable", "Use a completed, actually executed failed S05 result.", 409)
        job = self.generation.job(run["candidate_id"])
        sources = self._current_sources()
        identity = self._repair_identity(job["node_id"], sources[job["node_id"]]["latest_job_id"])
        if (run.get("freshness") != "Current" or identity is None
                or identity["base_job_id"] != job["id"] or identity["source_workflow_run_id"] != run["id"]):
            raise DomainError("repair_source_changed", "Use the latest failed S05 result for the current RTL candidate.", 409)
        with self.generation.lock:
            jobs = copy.deepcopy(self.generation._state["jobs"])
        with self.workflow.lock:
            runs = copy.deepcopy(self.workflow._state["runs"])
        guidance = build_repair_guidance(self.store.snapshot(job["revision_id"]), run, job, jobs, runs)
        guidance["additional_instruction"] = instruction
        previous = (guidance["recent_attempts"][0].get("previous_guidance") or {}) if guidance["recent_attempts"] else {}
        guidance["manual_correction_revised"] = bool(instruction.strip() and instruction != previous.get("additional_instruction", ""))
        guidance["guidance_sha256"] = object_hash({key: value for key, value in guidance.items() if key != "guidance_sha256"})
        return guidance

    def preview(self, revision_id, mode="generate", node_ids=None, instruction="", retry_batch_id=None, analysis_job_ids=None, node_instructions=None):
        if mode not in {"generate", "synthesis_repair", "netlist_repair"} or type(instruction) is not str or len(instruction.encode("utf-8")) > 8192 or node_ids is not None and (type(node_ids) is not list or any(type(value) is not str for value in node_ids) or len(set(node_ids)) != len(node_ids)):
            raise DomainError("invalid_batch_request", "Choose generation, synthesis repair or netlist repair and a distinct list of saved nodes.")
        if analysis_job_ids is not None and (type(analysis_job_ids) is not dict or any(type(key) is not str or type(value) is not str for key, value in analysis_job_ids.items())):
            raise DomainError("invalid_batch_request", "Choose saved repair analysis jobs by node ID.")
        if node_instructions is not None and (type(node_instructions) is not dict
                or any(type(key) is not str or type(value) is not str or len(value.encode("utf-8")) > 8192
                       for key, value in node_instructions.items())):
            raise DomainError("invalid_node_instructions", "Use node IDs and natural-language strings of at most 8,192 UTF-8 bytes per node.")
        if node_instructions and retry_batch_id is not None:
            raise DomainError("invalid_node_instructions", "Prepare a fresh preview to edit per-node guidance. A retry retains its frozen original node instructions.")
        with self.lock:
            if self.is_active():
                raise DomainError("generation_batch_busy", "Finish or cancel the current sequential generation first.", 409)
            current = self.store.envelope()
            if revision_id != current["revision"]["id"]:
                raise DomainError("revision_conflict", "Prepare the batch from the current saved design.", 409)
            sources = self._current_sources()
            if node_ids is not None and (not node_ids or set(node_ids) - set(sources)):
                raise DomainError("invalid_batch_nodes", "Select at least one node from the current saved design.")
            if node_instructions and (set(node_instructions) - set(sources)
                    or node_ids is not None and set(node_instructions) - set(node_ids)):
                raise DomainError("invalid_node_instructions", "Each per-node instruction must belong to a selected node in the saved design.")
            profile = copy.deepcopy(self.generation._require_profile())
            retry = self._batch(retry_batch_id) if retry_batch_id is not None else None
            retry_plan = self._plan(retry["plan_id"]) if retry else None
            seed_ids = []
            if retry:
                if retry["execution_status"] in ACTIVE or retry["revision_id"] != revision_id or retry["mode"] != mode:
                    raise DomainError("generation_retry_source_conflict", "Retry the finished batch with the same saved design and operation.", 409)
                if not same_provider(retry_plan["profile"], profile["profile"]):
                    raise DomainError("generation_retry_profile_conflict", "Conversation retries may change output, context and timeout settings on the same provider and model. To change provider or model, explicitly prepare a fresh generation request for the selected nodes.", 409)
                if any(item.get("context", {}).get("prompt_template_version") == "node-verilog-2005-v10" for item in retry_plan["items"] if item.get("context")) and retry_plan["profile"].get("reasoning_effort") != profile["profile"].get("reasoning_effort"):
                    raise DomainError("generation_retry_profile_conflict", "To change thinking control, prepare fresh generation. A conversation retry preserves its frozen prompt directive.", 409)
                seed_ids = list(retry_plan.get("seed_job_ids", [])) + [item["job_id"] for item in retry["items"] if item.get("job_id")]
            items = []
            for node in current["design"]["nodes"]:
                if node_ids is not None and node["id"] not in node_ids:
                    continue
                source = sources[node["id"]]
                retry_item = next((item for item in retry["items"] if item["node_id"] == node["id"]), None) if retry else None
                if retry and (retry_item is None or retry_item["status"] in {"Passed", "Skipped"}):
                    continue
                identity = (self._repair_identity(node["id"], source["latest_job_id"]) if mode == "synthesis_repair"
                            else self._netlist_repair_identity(node["id"], source["latest_job_id"]) if mode == "netlist_repair" else None)
                base = identity["base_job_id"] if identity else source["latest_job_id"] if mode in {"synthesis_repair", "netlist_repair"} else None
                run = self.workflow.run(identity["source_workflow_run_id"]) if identity else None
                if mode == "netlist_repair" and identity:
                    run = self._netlist_repair_source(node["id"], base, allow_transport_recovery=bool(identity.get("recovery")))[0]
                if retry:
                    original = next(item for item in retry_plan["items"] if item["node_id"] == node["id"])
                    expected = retry_item.get("job_id") or original["expected_latest_job_id"]
                    if source["latest_job_id"] != expected:
                        raise DomainError("generation_retry_source_conflict", "A node has a newer request outside this batch. Inspect it and prepare a fresh batch from the current source.", 409)
                    base = original["base_job_id"]
                    run = self.workflow.run(original["source_workflow_run_id"]) if original["source_workflow_run_id"] else None
                    if mode == "netlist_repair" and run:
                        with self.workflow.lock:
                            run = copy.deepcopy(self.workflow._run(original["source_workflow_run_id"]))
                if not retry and node_ids is None and ((mode == "generate" and source["accepted_job_id"] and source["accepted_job_id"] == source["latest_job_id"]) or (mode in {"synthesis_repair", "netlist_repair"} and run is None)):
                    continue
                effective_instruction = _node_instruction(instruction, node["id"], (node_instructions or {}).get(node["id"], ""))
                item = {"node_id": node["id"], "node_name": node.get("name", node["id"]), "operation": "repair" if run else "generate",
                        "base_job_id": base, "expected_latest_job_id": source["latest_job_id"],
                        "source_workflow_run_id": run["id"] if run else None, "source_workflow_sha256": object_hash({key: value for key, value in run.items() if key not in {"freshness", "artifacts"}}) if run else None,
                        "instruction": effective_instruction, "context": None, "status": "Queued", "reason": None}
                if identity and identity.get("recovery"):
                    item["source_recovery"] = copy.deepcopy(identity["recovery"])
                if mode == "netlist_repair":
                    if run is None or source.get("accepted_job_id") != base:
                        item.update(status="Blocked", reason="No current executed S06 failure with an accepted S05 netlist matches this RTL candidate.",
                                    error={"code": "netlist_repair_source_unavailable"})
                    elif not retry:
                        synthesis = self.workflow.run(run["prior_run_id"])
                        evidence = netlist_repair_evidence(run, synthesis)
                        item["netlist_repair_evidence"] = evidence
                        reviewed = None
                        analysis_id = (analysis_job_ids or {}).get(node["id"])
                        if analysis_id:
                            manager = getattr(self, "repair_analysis", None)
                            if manager is None:
                                raise DomainError("repair_analysis_unavailable", "Repair analysis service is unavailable.", 409)
                            reviewed = manager.reviewed_guidance(analysis_id, run["id"], self.netlist_repair_guidance_for_run(run["id"]))
                            item["repair_guidance"] = reviewed
                        item["instruction"] = netlist_repair_instruction(evidence, effective_instruction, reviewed)
                if mode == "synthesis_repair":
                    if run is None:
                        item.update(status="Blocked", reason="No current failed S05 result matches the latest RTL candidate.")
                    elif not retry:
                        guidance = self.repair_guidance_for_run(run["id"], effective_instruction)
                        analysis_id = (analysis_job_ids or {}).get(node["id"])
                        if analysis_id:
                            manager = getattr(self, "repair_analysis", None)
                            if manager is None:
                                raise DomainError("repair_analysis_unavailable", "Repair analysis service is unavailable.", 409)
                            guidance = manager.reviewed_guidance(analysis_id, run["id"], guidance)
                        guidance = with_prompt_projection(guidance)
                        item["repair_guidance"] = guidance
                        item["instruction"] = synthesis_repair_instruction(run, self.generation.job(base)["rtl"], effective_instruction, guidance)
                        if guidance["analysis_required"] and not guidance.get("analysis_reviewed") and not effective_instruction.strip():
                            item.update(status="Blocked", reason="No supported concrete repair method. Analyze the saved failure, review the proposed changes, then prepare a new repair preview.")
                        elif guidance.get("same_plan_repeated") and not guidance.get("analysis_reviewed") and not guidance.get("manual_correction_revised"):
                            item.update(status="Blocked", reason="The same repair plan left the problem unresolved. Reconsider its cause or add a revised correction before sending another request.")
                if retry:
                    item["operation"] = original["operation"]
                    item["instruction"] = original["instruction"] + ("\nAdditional correction for this explicitly requested retry:\n" + instruction if instruction.strip() else "")
                    if original.get("repair_guidance"):
                        item["repair_guidance"] = copy.deepcopy(original["repair_guidance"])
                    if original.get("netlist_repair_evidence"):
                        item["netlist_repair_evidence"] = copy.deepcopy(original["netlist_repair_evidence"])
                if item.get("repair_guidance") and run and mode != "netlist_repair":
                    # Display metadata remains outside the hashed guidance and
                    # model prompt. Legacy retry instructions are not rewritten.
                    with self.generation.lock:
                        explanation_jobs = copy.deepcopy(self.generation._state["jobs"])
                    with self.workflow.lock:
                        explanation_runs = copy.deepcopy(self.workflow._state["runs"])
                    item["repair_explanation"] = build_repair_explanation(item["repair_guidance"], run, self.generation.job(base), explanation_jobs, explanation_runs)
                if item["status"] == "Queued":
                    try:
                        item["context"] = self.generation.preview(node["id"], revision_id, item["operation"], item["base_job_id"], item["instruction"], _allow_budget_overflow=True,
                                                                  **({"_prompt_template_version": original["context"].get("prompt_template_version")} if retry and original.get("context") else {}))
                        if item["context"]["provider_input_estimated_tokens"] + profile["profile"]["max_output_tokens"] > profile["profile"]["context_window"]:
                            raise DomainError("context_budget", "Complete current request exceeds the configured context window.", 422)
                        if not item["context"]["ready_to_generate"]:
                            item.update(status="Blocked", reason=item["context"]["gate_reason"])
                    except DomainError as error:
                        if error.code == "context_budget" and item.get("repair_guidance") and not retry and mode != "netlist_repair":
                            # Reproject history only, preserving the complete
                            # current source contract/RTL and frozen old retries.
                            item["repair_guidance"] = with_prompt_projection(item["repair_guidance"], compact=True)
                            item["instruction"] = render_repair_instruction(item["repair_guidance"], effective_instruction)
                            try:
                                item["context"] = self.generation.preview(node["id"], revision_id, item["operation"], item["base_job_id"], item["instruction"], _allow_budget_overflow=True)
                                if item["context"]["provider_input_estimated_tokens"] + profile["profile"]["max_output_tokens"] > profile["profile"]["context_window"]:
                                    item.update(status="Blocked", reason="Complete current request exceeds the configured context window.", error={"code": "context_budget", "message": "Complete current request exceeds the configured context window."})
                                elif not item["context"]["ready_to_generate"]:
                                    item.update(status="Blocked", reason=item["context"]["gate_reason"])
                            except DomainError as compact_error:
                                item.update(status="Blocked", reason=compact_error.message, error={"code": compact_error.code, "message": compact_error.message})
                        else:
                            item.update(status="Blocked", reason=error.message, error={"code": error.code, "message": error.message})
                items.append(item)
                if item.get("context"):
                    item["context_budget"] = _context_budget(item["context"]["messages"], item["context"]["messages"], profile["profile"])
                    item["context_budget"]["scope"] = "base_contract"
            first = None
            for index, item in enumerate(items):
                if item["status"] != "Queued":
                    continue
                try:
                    first = pack_batch_context(item["context"], [self.generation.job(value) for value in seed_ids], profile["profile"],
                        {"batch_id": "preview_pending_batch_id", "index": index, "prior_job_ids": seed_ids,
                         "seed_job_ids": seed_ids, "retry_of_batch_id": retry_batch_id,
                         "source_workflow_run_id": item["source_workflow_run_id"], "packing_policy_version": POLICY_V2["kind"]})
                    if item.get("repair_guidance"):
                        first["batch_context"]["repair_guidance"] = copy.deepcopy(item["repair_guidance"])
                    if item.get("netlist_repair_evidence"):
                        first["batch_context"]["netlist_repair_evidence"] = copy.deepcopy(item["netlist_repair_evidence"])
                    item["context_budget"] = copy.deepcopy(first["context_budget"])
                    break
                except DomainError as error:
                    item.update(status="Blocked", reason=error.message, error={"code": error.code, "message": error.message})
                    if hasattr(error, "context_budget"):
                        item["context_budget"] = copy.deepcopy(error.context_budget)
            plan = {"revision_id": revision_id, "design_hash": current["revision"]["semantic_hash"], "mode": mode,
                    "profile_revision_id": profile["revision_id"], "profile": profile["profile"], "items": items,
                    "context_policy": copy.deepcopy(POLICY_V2), "first_request_context": first,
                    "ready_to_start": first is not None, "gate_reason": None if first else "No ready nodes. Inspect the selected nodes and source diagnostics.", "created_at": utc_now()}
            if node_instructions:
                if set(node_instructions) - {item["node_id"] for item in items}:
                    raise DomainError("invalid_node_instructions", "Select the instructed nodes explicitly; default selection skips nodes with accepted RTL.")
                plan["instruction_inputs"] = {"version": NODE_INSTRUCTION_VERSION if mode == "generate" else REPAIR_NODE_INSTRUCTION_VERSION, "shared": instruction, "nodes": copy.deepcopy(node_instructions)}
            plan.update(retry_of_batch_id=retry_batch_id, seed_job_ids=seed_ids)
            plan["plan_id"] = "generation-plan-" + object_hash(plan)
            self._state["plans"].append(plan)
            self._persist()
            return copy.deepcopy(plan)

    def _guard(self, plan, batch=None):
        if self.store.envelope()["revision"]["id"] != plan["revision_id"]:
            raise DomainError("batch_source_changed", "Saved design changed. Prepare a new batch from the current input.", 409)
        self.generation._require_profile(plan["profile_revision_id"])
        sources = self._current_sources()
        items = batch["items"] if batch else plan["items"]
        for source, item in zip(plan["items"], items):
            expected = item.get("job_id") or source["expected_latest_job_id"]
            if sources[source["node_id"]]["latest_job_id"] != expected:
                raise DomainError("batch_source_changed", "Latest node RTL changed. Prepare a new batch from the current candidates.", 409)
            if source["source_workflow_run_id"]:
                if plan["mode"] == "netlist_repair":
                    # Its own replacement candidate may make the old S06 view
                    # stale. Check the frozen original record, not that new
                    # candidate's adoption against the original FIFO source.
                    with self.workflow.lock:
                        run = copy.deepcopy(self.workflow._run(source["source_workflow_run_id"]))
                        latest_s05 = [value for value in self.workflow._state["runs"] if value["node_id"] == source["node_id"] and value["stage_id"] == "local_synthesis"]
                        latest_s06 = [value for value in self.workflow._state["runs"] if value["node_id"] == source["node_id"] and value["stage_id"] == "local_netlist_simulation"]
                    if (not latest_s05 or latest_s05[-1]["id"] != run.get("prior_run_id")
                            or not latest_s06 or latest_s06[-1]["id"] != run["id"]):
                        raise DomainError("batch_source_changed", "A newer S05 or S06 result replaced the frozen netlist repair source.", 409)
                    run["freshness"] = "Current"
                else:
                    run = self.workflow.run(source["source_workflow_run_id"])
                digest = object_hash({key: value for key, value in run.items() if key not in {"freshness", "artifacts"}})
                if digest != source["source_workflow_sha256"] or run["candidate_id"] != source["base_job_id"] or run["freshness"] != "Current":
                    raise DomainError("batch_source_changed", "The exact saved failure source changed. Prepare a new repair batch.", 409)
                if plan["mode"] == "netlist_repair":
                    synthesis = self.workflow.run(run["prior_run_id"])
                    if netlist_repair_evidence(run, synthesis, source.get("netlist_repair_evidence", {}).get("projection_version", "s06-netlist-repair-evidence-v1")) != source.get("netlist_repair_evidence"):
                        raise DomainError("batch_source_changed", "The exact S06 plan, first failure or S05 netlist changed. Prepare a new netlist repair preview.", 409)
                    if not item.get("job_id") and sources[source["node_id"]].get("accepted_job_id") != source["base_job_id"]:
                        raise DomainError("batch_source_changed", "The original S06 RTL candidate is no longer adopted.", 409)
                    if not item.get("job_id") and not plan.get("retry_of_batch_id"):
                        identity = self._netlist_repair_identity(source["node_id"], expected)
                        if identity is None or identity["base_job_id"] != source["base_job_id"] or identity["source_workflow_run_id"] != run["id"]:
                            raise DomainError("batch_source_changed", "The current S06 repair source changed. Prepare a new netlist repair preview.", 409)
                if source.get("source_recovery") and not item.get("job_id"):
                    identity = (self._netlist_repair_identity(source["node_id"], expected) if plan["mode"] == "netlist_repair"
                                else self._repair_identity(source["node_id"], expected))
                    if identity is None or identity.get("recovery") != source["source_recovery"]:
                        raise DomainError("batch_source_changed", "The exact failed transport lineage changed. Prepare a new repair preview.", 409)

    def start(self, plan_id, request_id, *, _submission=None):
        if type(request_id) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", request_id):
            raise DomainError("invalid_batch_request", "Supply a distinct sequential request ID.")
        with self.lock:
            old = next((batch for batch in self._state["batches"] if batch["request_id"] == request_id), None)
            if old:
                if old["plan_id"] != plan_id:
                    raise DomainError("batch_request_conflict", "Request ID belongs to another plan.", 409)
                if _submission is not None:
                    raise DomainError("submission_conflict", "Inspect the saved request using its original submission identity.", 409)
                return self.envelope()
            if self._closed or self.is_active() or self.workflow.is_active() or self.generation.is_active():
                raise DomainError("generation_batch_busy", "Finish or cancel active generation or synthesis first.", 409)
            plan = self._plan(plan_id)
            if not plan["ready_to_start"]:
                raise DomainError("generation_batch_not_ready", plan["gate_reason"], 409)
            self._guard(plan)
            self.generation._prerequisites()
            batch = {key: copy.deepcopy(plan[key]) for key in ("revision_id", "profile_revision_id", "mode", "context_policy", "retry_of_batch_id", "seed_job_ids")}
            batch.update(id=new_id("generation-batch"), plan_id=plan_id, request_id=request_id,
                         items=[{key: copy.deepcopy(value) for key, value in item.items() if key != "context"} | {"job_id": None, "error": item.get("error")} for item in plan["items"]],
                         execution_status="Queued", validation_status="Not Checked", error=None, created_at=utc_now(), finished_at=None)
            self.generation.reserve_batch(batch["id"])
            try:
                if _submission is not None:
                    batch["submission_id"] = _submission.submission_id
                    _submission.bind(batch["id"])
                self._state["batches"].append(batch); self._persist()
            except Exception:
                self.generation.release_batch(batch["id"])
                raise
            self._cancel = threading.Event()
            self._worker = threading.Thread(target=self._execute, args=(batch["id"], self._cancel), daemon=True, name="HuLLCirq-sequential-node-conversation")
            self._worker.start()
            return self.envelope()

    def _execute(self, identifier, cancelled):
        try:
            with self.lock:
                batch = self._batch(identifier); plan = self._plan(batch["plan_id"])
                batch["execution_status"] = "Running"; self._persist()
            for index in range(len(batch["items"])):
                with self.lock:
                    batch = self._batch(identifier); item = batch["items"][index]
                    if cancelled.is_set():
                        break
                    self._guard(plan, batch)
                    if item["status"] != "Queued":
                        continue
                    prior_ids = list(plan.get("seed_job_ids", [])) + [entry["job_id"] for entry in batch["items"][:index] if entry.get("job_id")]
                    meta = {"batch_id": identifier, "index": index, "prior_job_ids": prior_ids,
                            "seed_job_ids": list(plan.get("seed_job_ids", [])), "retry_of_batch_id": plan.get("retry_of_batch_id"),
                            "source_workflow_run_id": item["source_workflow_run_id"]}
                    if plan.get("context_policy", {}).get("kind") == POLICY_V2["kind"]:
                        meta["packing_policy_version"] = POLICY_V2["kind"]
                    if item.get("repair_guidance"):
                        meta["repair_guidance"] = copy.deepcopy(item["repair_guidance"])
                    if item.get("netlist_repair_evidence"):
                        meta["netlist_repair_evidence"] = copy.deepcopy(item["netlist_repair_evidence"])
                    frozen_context = plan["items"][index].get("context") or {}
                    frozen_version = frozen_context.get("prompt_template_version")
                    preview = self.generation.preview(item["node_id"], batch["revision_id"], item["operation"], item["base_job_id"], item["instruction"], _prompt_template_version=frozen_version)
                    from .generation import request_hash
                    context = pack_batch_context(preview, [self.generation.job(value) for value in prior_ids], plan["profile"], meta)
                    context_id = request_hash(context, batch["profile_revision_id"], context["parameters"], item["operation"], item["base_job_id"])
                    item["status"] = "Running"; self._persist()
                    self.generation.start(item["node_id"], batch["revision_id"], context_id, batch["profile_revision_id"], item["operation"], item["base_job_id"], item["instruction"], _batch_id=identifier, _batch_context=meta, _prompt_template_version=frozen_version)
                    # GenerationManager reserves the worker and saves provenance
                    # before returning; do not infer identity from terminal order.
                    with self.generation.lock:
                        job = next(job for job in reversed(self.generation._state["jobs"]) if job.get("batch_id") == identifier and job.get("batch_index") == index)
                        item["job_id"] = job["id"]
                    self._persist()
                while True:
                    with self.generation.lock:
                        job = self.generation._stored_job(item["job_id"])
                        execution_status, job_id = job["execution_status"], job["id"]
                        worker = self.generation._worker
                    if execution_status not in ACTIVE and not (worker and worker.is_alive()):
                        job = self.generation.job(job_id)
                        break
                    if cancelled.is_set():
                        if execution_status in ACTIVE:
                            self.generation.cancel(job_id)
                    else:
                        try:
                            self._guard(plan, self._batch(identifier))
                        except DomainError:
                            if execution_status in ACTIVE:
                                self.generation.cancel(job_id)
                            raise
                    cancelled.wait(.05) if not cancelled.is_set() else time.sleep(.05)
                with self.lock:
                    item = self._batch(identifier)["items"][index]
                    item.update(status="Cancelled" if cancelled.is_set() else "Passed" if job["execution_status"] == "Completed" and job["stage_validation"]["validation_status"] == "Passed" else "Failed", error=job.get("error"), reason=None)
                    self._persist()
                    if (job.get("error") or {}).get("code") in FATAL_PROVIDER_CODES:
                        raise DomainError("generation_batch_provider_blocked", "The provider cannot serve this batch: " + job["error"]["message"] + " Fix the connection or settings and explicitly prepare the remaining nodes.", 409)
            with self.lock:
                batch = self._batch(identifier)
                for item in batch["items"]:
                    if item["status"] in ACTIVE:
                        item.update(status="Cancelled", reason="Batch cancelled before this node completed.")
                batch.update(execution_status="Cancelled" if cancelled.is_set() else "Completed", validation_status="Not Checked" if cancelled.is_set() else "Passed" if all(item["status"] in {"Passed", "Skipped"} for item in batch["items"]) else "Failed", finished_at=utc_now())
                self._persist()
        except Exception as error:
            with self.lock:
                batch = self._batch(identifier)
                batch.update(execution_status="Cancelled" if cancelled.is_set() else "Failed", validation_status="Not Checked", finished_at=utc_now(), error={"code": getattr(error, "code", "generation_batch_error"), "message": getattr(error, "message", "Sequential scheduling or saving failed. Inspect saved jobs before retrying.")})
                for item in batch["items"]:
                    if item["status"] in ACTIVE:
                        item.update(status="Blocked" if isinstance(error, DomainError) else "Interrupted", reason=batch["error"]["message"])
                try:
                    self._persist()
                except OSError:
                    pass
        finally:
            self.generation.release_batch(identifier)

    def cancel(self, identifier):
        with self.lock:
            if self._batch(identifier)["execution_status"] not in ACTIVE:
                raise DomainError("generation_batch_not_active", "Only an active sequential generation can be cancelled.", 409)
            self._cancel.set()
            return self.envelope()

    def batch(self, identifier):
        with self.lock:
            result = copy.deepcopy(self._batch(identifier))
            try:
                self._guard(self._plan(result["plan_id"]), result); result["source_current"] = True
            except DomainError:
                result["source_current"] = False
            result["counts"] = {status: sum(item["status"] == status for item in result["items"]) for status in sorted(ITEM_STATES)}
            result["completed_count"] = sum(item["status"] not in ACTIVE for item in result["items"])
            result["required_node_count"] = len(result["items"])
            return result

    def plan(self, identifier):
        with self.lock:
            return copy.deepcopy(self._plan(identifier))

    def envelope(self):
        with self.lock:
            batches = [self.batch(batch["id"]) for batch in self._state["batches"]]
            active = next((batch["id"] for batch in reversed(batches) if batch["execution_status"] in ACTIVE), None)
            return {"generation_batches": {"batches": batches, "active_batch_id": active,
                    "execution_submissions": submission_view(self), "submission_protocol_version": PROTOCOL_VERSION,
                    "latest_batch_id": batches[-1]["id"] if batches else None, "storage_error": copy.deepcopy(self._storage_error),
                    "repair_sources": self.repair_sources(), "netlist_repair_sources": self.netlist_repair_sources()}}

    def close(self):
        self._closed = True
        self._cancel.set()
        # The provider worker closes its connection; there is no auto-resume.
