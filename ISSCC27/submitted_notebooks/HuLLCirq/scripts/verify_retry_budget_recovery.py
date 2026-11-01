"""Read saved real evidence; preview only in an isolated copy, never infer RTL.

No provider, synthesis, review or live profile mutation is performed. The
isolated copy also proves that old v1 jobs and plans still load unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hullcirq.generation import GenerationManager
from hullcirq.generation_batches import GenerationBatchManager
from hullcirq.provider import estimate_message_input
from hullcirq.store import ProjectStore
from hullcirq.workflow import WorkflowManager


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / ".work/projects/npu_2x2_explicit/systems/system-7df07952c6b64696813d14ab19837af8")
    parser.add_argument("--output", type=Path, default=ROOT / "results/retry_budget_recovery/isolated_real_preview.json")
    args = parser.parse_args()
    files = sorted(args.source.glob("*.json"))
    before = {path.name: sha(path) for path in files}
    with tempfile.TemporaryDirectory(prefix="retry-budget-real-", dir=ROOT / ".work") as directory:
        target = Path(directory)
        for path in files:
            shutil.copy2(path, target / path.name)
        store = ProjectStore(target)
        generation = GenerationManager(store)
        workflow = WorkflowManager(store, generation)
        batches = GenerationBatchManager(store, generation, workflow)
        try:
            baseline = {path.name: sha(path) for path in target.glob("*.json")}
            profile = generation._require_profile()
            if profile["profile"]["max_output_tokens"] != 3000:
                changed = dict(profile["profile"], max_output_tokens=3000)
                generation.save_profile(changed, profile["revision_id"])
            revision = store.envelope()["revision"]["id"]
            sources = batches.repair_sources()
            fresh = batches.preview(revision, "synthesis_repair")
            batches._guard(fresh)
            latest = batches._state["batches"][-1]
            retry = batches.preview(revision, "synthesis_repair", retry_batch_id=latest["id"])
            batches._guard(retry)
            assert len(fresh["items"]) == 7 and all(item["status"] == "Queued" for item in fresh["items"])
            assert fresh["ready_to_start"] and retry["ready_to_start"]
            assert all(item.get("source_recovery") for item in fresh["items"])
            for plan in (fresh, retry):
                context = plan["first_request_context"]
                budget = context["context_budget"]
                assert budget["provider_input_estimated_tokens"] == estimate_message_input(context["messages"])
                assert budget["fits"] and budget["total_estimated_tokens"] <= budget["context_window"]
            # Freeze/reload new plans as well as all old v1 source records.
            frozen = json.loads(batches.path.read_text(encoding="utf-8"))
            reloaded_generation = GenerationManager(store)
            reloaded = GenerationBatchManager(store, reloaded_generation, workflow)
            assert reloaded._state == frozen
            reloaded.close(); reloaded_generation.close()
            unchanged = {name: baseline[name] == sha(target / name) for name in baseline if name != "generation_batches.json"}
            assert all(unchanged.values())
            result = {"scope": "isolated_copy_of_saved_real_evidence_preview_only",
                      "provider_requests": 0, "eda_executions": 0,
                      "source_generation_jobs": len(generation._state["jobs"]), "source_workflow_runs": len(workflow._state["runs"]),
                      "repair_sources": sources,
                      "fresh": {"ready_to_start": fresh["ready_to_start"], "policy": fresh["context_policy"],
                                "items": [{key: item.get(key) for key in ("node_id", "base_job_id", "expected_latest_job_id", "source_workflow_run_id", "source_recovery", "status", "context_budget")} for item in fresh["items"]]},
                      "retry": {"ready_to_start": retry["ready_to_start"], "source_batch_id": latest["id"],
                                "seed_job_ids": retry["seed_job_ids"], "context_budget": retry["first_request_context"]["context_budget"],
                                "packing": retry["first_request_context"]["batch_context"]["packing"]},
                      "isolated_nonpreview_stores_unchanged": unchanged, "legacy_and_new_plans_reload": "Passed"}
        finally:
            batches.close(); generation.close(); workflow.close()
    after = {path.name: sha(path) for path in files}
    assert before == after
    result["live_store_sha256_before"] = before
    result["live_store_byte_unchanged"] = before == after
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "fresh_ready": result["fresh"]["ready_to_start"], "retry_ready": result["retry"]["ready_to_start"], "retry_budget": result["retry"]["context_budget"], "live_stores_unchanged": True}, ensure_ascii=False))


if __name__ == "__main__":
    main()
