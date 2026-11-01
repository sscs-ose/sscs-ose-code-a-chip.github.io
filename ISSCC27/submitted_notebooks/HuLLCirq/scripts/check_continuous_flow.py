"""Continue a saved, adopted node candidate using its original verification.

This CLI does not import replacement per-stage stimulus or grant a review
policy. Configure that policy in the GUI before requesting automatic adoption.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from hullcirq.domain import DomainError
from hullcirq.generation import GenerationManager
from hullcirq.store import ProjectStore
from hullcirq.workflow import WorkflowManager


def main():
    parser = argparse.ArgumentParser(description="Run generic synthesis and/or the original frozen netlist verification.")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--compiler-config", type=Path, required=True)
    parser.add_argument("--synthesizer-config", type=Path, required=True)
    parser.add_argument("--stage", choices=("local_synthesis", "local_netlist_simulation", "both"), default="both")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    compiler = json.loads(args.compiler_config.read_text(encoding="utf-8-sig"))
    synthesizer = json.loads(args.synthesizer_config.read_text(encoding="utf-8-sig"))
    store = ProjectStore(args.data_dir)
    generation = GenerationManager(store, compiler)
    workflow = WorkflowManager(store, generation, compiler, synthesizer)
    evidence = []
    try:
        candidate = generation.job(args.candidate_id)
        stages = ("local_synthesis", "local_netlist_simulation") if args.stage == "both" else (args.stage,)
        for stage in stages:
            state = workflow.start(stage, candidate["node_id"], candidate["id"], store.envelope()["revision"]["id"])
            run_id = state["workflow_runs"][-1]["id"]
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                run = workflow.run(run_id)
                worker = workflow._worker
                if run["finished_at"] and worker is not None and not worker.is_alive():
                    break
                time.sleep(0.1)
            else:
                workflow.cancel(run_id)
                raise DomainError("workflow_timeout", "Continuous flow timed out; partial durable evidence is retained.")
            evidence.append(run)
            print(json.dumps({"run_id": run_id, "stage_id": stage, "execution_status": run["execution_status"],
                              "validation_status": run["validation_status"], "review_status": run["review_status"],
                              "vector_hash": run["vector_hash"], "testbench_sha256": run["testbench_sha256"]}))
            if run["validation_status"] != "Passed" or run["review_status"] != "Accepted":
                print("The next stage requires a Passed, adopted result. Review it in the GUI or configure an explicitly authorized policy.", file=sys.stderr)
                return 2
        return 0
    except DomainError as error:
        print(json.dumps({"error": {"code": error.code, "message": error.message}}), file=sys.stderr)
        return 2
    finally:
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        workflow.close()
        generation.close()


if __name__ == "__main__":
    raise SystemExit(main())
