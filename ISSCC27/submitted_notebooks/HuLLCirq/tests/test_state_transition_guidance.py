"""All shared Next step branches; software scenarios are not circuit evidence."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
ACCEPTED = dict(id="current", execution_status="Completed", validation_status="Passed",
                review_status="Accepted", freshness="Current")
BASE = dict(stage="layout", implemented=True, prerequisite="global_netlist_simulation",
            runLabel="Run physical layout", runTestId="physical-workflow-run")


def scenario(decision_id, stage=None, **fields):
    context = {**BASE, **fields}
    if stage:
        context["stage"] = stage
        stage_controls = {
            "local_synthesis": ("local_rtl_generation", "Run synthesis for all nodes", "workflow-batch-run"),
            "local_netlist_simulation": ("local_synthesis", "Run netlist verification", "workflow-run"),
            "node_implementation_specs": ("local_netlist_simulation", "Derive and verify specification", "implementation-spec-run"),
            "global_synthesis": ("global_rtl_generation", "Run synthesis", "global-workflow-run"),
            "post_layout_verification": ("lvs", "Run post-layout verification", "postlayout-workflow-run"),
        }
        if stage in stage_controls:
            context["prerequisite"], context["runLabel"], context["runTestId"] = stage_controls[stage]
    return dict(id=decision_id, context=context)


SCENARIOS = [
    scenario("execution_running", executionOverlay=dict(status="Running")),
    scenario("execution_reconnect", executionOverlay=dict(status="Failed", reconnectRequired=True)),
    scenario("execution_invalidated", executionOverlay=dict(status="Not run", invalidated=True)),
    scenario("read_only", readOnly=True),
    scenario("conflict", conflict=True),
    scenario("invalid_input", invalidInput="Correct the saved verification JSON."),
    scenario("dirty", dirty=True),
    scenario("generation_batch", "local_rtl_generation", generationBatchGuidance=dict(
        title="Inspect the running batch", summary="Saved progress is retained.",
        primary=dict(label="View generation batch", kind="inspect", target="stage-content"))),
    scenario("reconnect", reconnect="physical-workflow-reconnect"),
    scenario("active_other", activeOperation=dict(stage="local_synthesis", nodeId="node-a")),
    scenario("active_current", busy=True),
    scenario("local_generation", "local_rtl_generation", localGuidance=dict(
        title="Preview node RTL", summary="Inspect the request first.",
        primary=dict(label="Context Preview", kind="control", testId="context-preview-button"))),
    scenario("input_prerequisite", "specifications", missingInputStage="graph_editor"),
    scenario("input_empty_graph", "graph_editor", emptyGraph=True),
    scenario("input_stale", "global_settings", record={**ACCEPTED, "freshness": "Stale"}),
    scenario("input_failed", "graph_editor", record={**ACCEPTED, "validation_status": "Failed"}),
    scenario("input_accepted", "specifications", record=ACCEPTED),
    scenario("input_review", "global_settings", record={**ACCEPTED, "review_status": "Awaiting Review"}),
    scenario("input_verify", "global_settings"),
    scenario("integration_unsupported", "global_synthesis", integrationUnsupported="Unsupported integration for this design."),
    scenario("s06_batch", "local_netlist_simulation", netlistSummary=dict(total=3, accepted=1, runnable=2, blocked=0, failed=0)),
    scenario("s06_checker", "local_netlist_simulation", blocker=dict(kind="implementation_required", message="Missing checker.")),
    scenario("s06_inputs", "local_netlist_simulation", blocker=dict(kind="input_required", message="Missing verification input.")),
    scenario("s06_configuration", "local_netlist_simulation", blocker=dict(kind="configuration_required", message="Configure the simulator.")),
    scenario("s06_prerequisite", "local_netlist_simulation", blocker=dict(kind="synthesis_required", message="Current S05 required.")),
    scenario("s06_unavailable", "local_netlist_simulation", blocker=dict(kind="verification_unavailable", message="Verification unavailable.")),
    scenario("unimplemented", implemented=False),
    scenario("history", record=ACCEPTED, historical=True),
    scenario("source_history", record=ACCEPTED, recordCurrent=False),
    scenario("stale", record={**ACCEPTED, "freshness": "Stale"}),
    scenario("review_changes", record={**ACCEPTED, "review_status": "Changes Requested"}),
    scenario("s05_bulk_repair", "local_synthesis", synthesisRepairCount=2,
             synthesisSummary=dict(total=3, accepted=1)),
    scenario("failed", record={**ACCEPTED, "validation_status": "Failed"}),
    scenario("s05_complete", "local_synthesis", synthesisSummary=dict(total=3, accepted=3)),
    scenario("s05_failed_node", "local_synthesis", synthesisSummary=dict(total=3, accepted=2,
             firstFailed=dict(id="node-a", name="Failed node"))),
    scenario("s05_sources", "local_synthesis", synthesisSummary=dict(total=3, accepted=2,
             firstIncomplete=dict(id="node-a", name="Pending node")), synthesisBatchGate="A current RTL source is required."),
    scenario("s05_pending", "local_synthesis", synthesisSummary=dict(total=3, accepted=2)),
    scenario("accepted_gate", record=ACCEPTED, gate="Current required source is missing."),
    scenario("completion_blocked", "post_layout_verification", record=ACCEPTED,
             completionBlocked="Saved diagnostic review cannot complete dynamic verification."),
    scenario("complete", "post_layout_verification", record=ACCEPTED),
    scenario("node_next", "node_implementation_specs", record=ACCEPTED,
             nextNode=dict(id="node-a", name="Remaining node")),
    scenario("continue_blocked", record=ACCEPTED, continueBlocked="Next stage is not ready."),
    scenario("accepted", record=ACCEPTED),
    scenario("review_pass", record={**ACCEPTED, "review_status": "Awaiting Review"}),
    scenario("prerequisite", gate="Current accepted source is missing."),
    scenario("run"),
    scenario("global_preview", "global_rtl_generation"),
    scenario("global_generate", "global_rtl_generation", previewReady=True),
]

SCENARIOS.append(scenario("cancelled", record={**ACCEPTED, "execution_status":"Cancelled", "validation_status":"Not Checked", "review_status":"Awaiting Review"}))

CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const sandbox={};vm.createContext(sandbox);vm.runInContext('{'+fs.readFileSync('src/gui/availability.js','utf8').replace(/export /g,'')+'\nglobalThis.availabilityReason=availabilityReason;}',sandbox);
vm.runInContext(fs.readFileSync('src/gui/flow_guidance.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+
 '\nthis.resolve=resolveStageGuidance;this.decisions=GUIDANCE_DECISIONS;',sandbox);
const cases=JSON.parse(process.argv[1]);
const visited=new Set();
for(const item of cases){
 const resolved=sandbox.resolve(item.context);
 assert.equal(resolved.decisionId,item.id,JSON.stringify({item,resolved}));
 assert.ok(resolved.primary?.label,JSON.stringify(resolved));
 if(resolved.primary.kind==='control')assert.ok(resolved.primary.testId);
 if(resolved.primary.kind==='navigate')assert.ok(resolved.primary.stage);
 visited.add(item.id);
 item.expected=JSON.parse(JSON.stringify(resolved));
}
assert.deepEqual([...visited].sort(),[...sandbox.decisions].sort());
console.log(JSON.stringify({scope:'Isolated software guidance scenarios; no model or EDA execution',
 status:'Passed',decisions:[...visited],scenarios:cases},null,2));
"""


class StateTransitionGuidanceTests(unittest.TestCase):
    def run_client(self, cases=SCENARIOS, script=CLIENT):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node required for isolated state transition checks.")
        result = subprocess.run([node, "-e", script, json.dumps(cases)], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_every_shared_decision_has_a_resolvable_action(self):
        result = self.run_client()
        self.assertEqual(len(result["decisions"]), 49)

    def test_earlier_source_even_if_labeled_current_cannot_advance_or_repair(self):
        script = CLIENT[:CLIENT.index("const cases=")] + r"""
for(const stage of ['local_synthesis','local_netlist_simulation','node_implementation_specs']){
 const r=sandbox.resolve({stage,recordCurrent:false,record:{execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current'},synthesisRepairCount:1,synthesisSummary:{total:11,accepted:11}});
 assert.equal(r.decisionId,'source_history');assert.equal(r.primary.kind,'latest');
 assert.notEqual(r.tone,'success');
}
console.log('{}');
"""
        self.run_client([], script)

    def test_batch_preview_does_not_override_another_running_stage(self):
        script = CLIENT[:CLIENT.index("const cases=")] + r"""
const r=sandbox.resolve({stage:'local_rtl_generation',activeOperation:{stage:'local_synthesis',nodeId:'node-a'},generationBatchGuidance:{title:'Start stale preview',primary:{kind:'control',testId:'generate-node'}}});
assert.equal(r.decisionId,'active_other');assert.equal(r.primary.stage,'local_synthesis');
assert.equal(r.primary.nodeId,'node-a');console.log('{}');
"""
        self.run_client([], script)


if __name__ == "__main__":
    unittest.main()
