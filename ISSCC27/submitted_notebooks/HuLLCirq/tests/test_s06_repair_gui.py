"""S06 failure-to-RTL draft bridge; isolated software fixtures, never circuit proof."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT


PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const localSource=fs.readFileSync('src/gui/workflow.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class LocalWorkflow','class LocalWorkflow');
vm.runInContext('{'+localSource+'\nglobalThis.LocalWorkflow=LocalWorkflow;}',sandbox);
vm.runInContext('{'+fs.readFileSync('src/gui/flow_guidance.js','utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+'\nglobalThis.resolve=resolveStageGuidance;}',sandbox);
const candidate={...failed,id:'candidate',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',finished_at:'2026-10-14T00:00:00Z',rtl:'module qa_control; endmodule',rtl_sha256:'original-rtl-hash',input_hash:'original-input-hash'};
const synthesis={id:'synthesis',node_id:'node-a',stage_id:'local_synthesis',candidate_id:candidate.id,execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',rtl_sha256:candidate.rtl_sha256,input_hash:candidate.input_hash,netlist:'original netlist',netlist_sha256:'original-netlist-hash'};
const run={id:'failed-S06',node_id:'node-a',stage_id:'local_netlist_simulation',candidate_id:candidate.id,revision_id:'revision-a',requested_revision_id:'revision-a',input_hash:candidate.input_hash,rtl_sha256:candidate.rtl_sha256,prior_run_id:synthesis.id,netlist_sha256:synthesis.netlist_sha256,vector_hash:'original-vector-hash',testbench_sha256:'original-testbench-hash',execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',finished_at:'2026-10-14T01:00:00Z',checks:{executed:true,stdout:'Starting simulation\nHULLCIRQ_FAIL cycle=3 signal=output_data expected=12 actual=14\nrest of saved log\n',stderr:''},diagnostics:[{code:'behavior_mismatch',severity:'error',message:'Original contract trace mismatch'}]};
project.stage='local_netlist_simulation';
project.envelope.workflow.push({id:'local_synthesis',implemented:true},{id:'local_netlist_simulation',implemented:true});
project.envelope.generation={submission_protocol_version:"node-submission-v1",implemented:true,jobs:[candidate],nodes:[{node_id:'node-a',accepted_job_id:candidate.id,latest_job_id:candidate.id}]};
project.envelope.workflow_runs=[synthesis,run];
const prepared=[];
const local=new sandbox.LocalWorkflow({project:()=>project,prepareRepair:(...args)=>{prepared.push(args);return true;},toast:message=>notices.push(message),request:()=>assert.fail('Draft preparation must not mutate records or send model/tool requests')});
local.nodeId='node-a';local.runs=[synthesis,run];
const restore=()=>{Object.assign(project,{dirty:false,conflict:null,busy:false,readOnly:false,postlayoutRunning:false,lvsRunning:false,stage:'local_netlist_simulation'});project.envelope.workspace_identity.read_only=false;project.envelope.revision.id='revision-a';project.envelope.generation={submission_protocol_version:"node-submission-v1",implemented:true,jobs:[candidate],nodes:[{node_id:'node-a',accepted_job_id:candidate.id,latest_job_id:candidate.id}]};local.runs=[synthesis,run];local.runId=null;local.busy=false;local.storageError=null;delete project.envelope.global_generation;delete project.envelope.physical_workflow;};
"""


class S06RepairGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated client checks.")
        result = subprocess.run([node, "-e", CLIENT + SETUP + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_failed_evidence_prepares_a_draft_without_mutation_or_execution(self):
        self.client(r"""
const before=JSON.stringify([candidate,synthesis,run]);
assert.equal(local.repairGate(),'');assert.equal(local.prepareRepair(run,'Keep original FIFO ordering.'),true);
assert.equal(prepared.length,1);assert.equal(prepared[0][0],candidate);
const instruction=prepared[0][1];
for(const source of ['failed-S06','candidate','revision-a','original-input-hash','original-rtl-hash','synthesis','original-netlist-hash','original-vector-hash','original-testbench-hash','HULLCIRQ_FAIL cycle=3 signal=output_data expected=12 actual=14','behavior_mismatch','Keep original FIFO ordering.']) assert.ok(instruction.includes(source),source);
assert.match(instruction,/Preserve the saved specification.*original verification inputs/);
assert.match(instruction,/bounded excerpts.*Complete checks/s);assert.match(instruction,/S05 synthesis and S06 verification must be rerun/);
assert.equal(JSON.stringify([candidate,synthesis,run]),before);assert.equal(requests.length,0);
""")

    def test_guard_rejects_readonly_unsaved_active_historical_and_changed_sources(self):
        self.client(r"""
const changes=[()=>project.readOnly=true,()=>project.envelope.workspace_identity.read_only=true,()=>project.dirty=true,()=>project.conflict='external',()=>project.busy=true,()=>local.busy=true,()=>project.postlayoutRunning=true,()=>project.lvsRunning=true,()=>project.envelope.global_generation={submission_protocol_version:"node-submission-v1",jobs:[{execution_status:'Running'}]},()=>project.envelope.physical_workflow={runs:[{execution_status:'Queued'}]},()=>local.storageError={message:'disk'},()=>project.envelope.generation.jobs.push({...candidate,id:'active',execution_status:'Running'}),()=>local.runs.push({...synthesis,id:'active-S05',execution_status:'Running'}),()=>{local.runs.push({...run,id:'newer-failure'});local.runId=run.id;},()=>local.runs=[synthesis,{...run,freshness:'Stale'}],()=>local.runs=[synthesis,{...run,finished_at:null}],()=>local.runs=[synthesis,{...run,validation_status:'Passed'}],()=>project.envelope.generation.nodes[0].latest_job_id='newer-candidate',()=>project.envelope.generation.jobs=[{...candidate,review_status:'Awaiting Review'}],()=>local.runs=[synthesis,{...run,rtl_sha256:'changed'}],()=>local.runs=[synthesis,{...run,input_hash:'changed'}],()=>local.runs=[synthesis,{...run,vector_hash:null}],()=>local.runs=[synthesis,{...run,requested_revision_id:'older'}],()=>local.runs=[synthesis,{...run,revision_id:'older'}],()=>local.runs=[synthesis,{...run,prior_run_id:'other-S05'}],()=>local.runs=[synthesis,{...run,netlist_sha256:'changed'}],()=>local.runs=[synthesis,{...synthesis,id:'newer-S05'},run],()=>local.runs=[{...synthesis,review_status:'Awaiting Review'},run]];
for(const change of changes){restore();change();const selected=local.selected();assert.notEqual(local.repairGate(selected),'');assert.equal(local.prepareRepair(selected),false);}
assert.equal(prepared.length,0);assert.equal(requests.length,0);
""")

    def test_instruction_is_bounded_and_missing_fail_line_does_not_invent_counterexample(self):
        self.client(r"""
const changed={...run,checks:{stdout:'Compiler error only'},diagnostics:Array.from({length:20},(_,i)=>({code:'diagnostic-'+i,message:'日'.repeat(2000)}))};
const instruction=local.repairInstruction(changed,'人'.repeat(12000));
assert.ok(Buffer.byteLength(instruction,'utf8')<32768);assert.match(instruction,/No HULLCIRQ_FAIL line was recorded/);assert.doesNotMatch(instruction,/HULLCIRQ_FAIL cycle=/);assert.doesNotMatch(instruction,/diagnostic-8:/);assert.match(instruction,/bounded excerpts/);
""")

    def test_failed_s06_guidance_points_to_explicit_repair_control(self):
        self.client(r"""
const context={stage:project.stage,record:run,implemented:true,nodeId:local.nodeId,prerequisite:'local_synthesis',repairAvailable:!local.repairGate(),failureExcerpt:local.firstFailure(run)};
const guide=sandbox.resolve(context);assert.equal(guide.primary.kind,'inspect');assert.equal(guide.secondary.kind,'control');assert.equal(guide.secondary.testId,'workflow-prepare-repair');assert.notEqual(guide.secondary.stage,'local_synthesis');
assert.match(guide.summary,/HULLCIRQ_FAIL cycle=3 signal=output_data expected=12 actual=14/);assert.doesNotMatch(guide.summary,/Original contract trace mismatch/);
const historical=sandbox.resolve({...context,historical:true});assert.equal(historical.primary.kind,'latest');assert.notEqual(historical.secondary.testId,'workflow-prepare-repair');
""")

    def test_first_recorded_failure_is_visible_and_shared_with_repair_without_inferring_cause(self):
        self.client(r"""
const original=JSON.stringify(run);
const resultHost=el('div',{},el('div',{'data-testid':'workflow-result'}));local.host=resultHost;local.renderResult();
const shown=resultHost.querySelector('[data-testid="workflow-first-failure"]');
assert.ok(shown);assert.match(text(shown),/First recorded simulation failure.*HULLCIRQ_FAIL cycle=3 signal=output_data expected=12 actual=14/);
assert.equal(local.firstFailure(run),'HULLCIRQ_FAIL cycle=3 signal=output_data expected=12 actual=14');
assert.ok(local.repairInstruction(run).includes(local.firstFailure(run)));assert.equal(JSON.stringify(run),original);assert.equal(requests.length,0);
const changed={...run,checks:{stdout:'setup log\r\nHULLCIRQ_FAIL raw=<img onerror=bad()> '+ 'x'.repeat(2000)+'\r\nHULLCIRQ_FAIL second-line'}};
const excerpt=local.firstFailure(changed);assert.equal(excerpt.length,1200);assert.ok(excerpt.includes('<img onerror=bad()>'));assert.doesNotMatch(excerpt,/second-line/);
assert.equal(local.firstFailure({...run,checks:{stdout:'Compiler error only'}}),'');
local.runs=[synthesis,{...run,validation_status:'Passed'}];local.renderResult();assert.equal(resultHost.querySelector('[data-testid="workflow-first-failure"]'),null);
""")

    def test_rendered_action_carries_optional_note_and_blocks_after_source_changes(self):
        self.client(r"""
const review=new DOMDouble('div');local.renderReview(review);
const button=review.querySelector('[data-testid="workflow-prepare-repair"]');assert.equal(button.disabled,false);
review.querySelector('[data-testid="workflow-feedback"]').value='Preserve FIFO sequence.';button.onclick();assert.match(prepared[0][1],/Preserve FIFO sequence/);
project.dirty=true;local.renderReview(review);assert.equal(review.querySelector('[data-testid="workflow-prepare-repair"]').disabled,true);
""")

    def test_actual_app_bridge_uses_existing_s04_preview_flow_and_rechecks_current_source(self):
        self.client(r"""
workspace.generation=project.envelope.generation;workspace.selectedJobId=candidate.id;
const navigated=[];Object.assign(sandbox,{state:{envelope:project.envelope,busy:false,externalRevision:null},readOnly:()=>project.readOnly,dirty:()=>project.dirty,executionInputDirty:()=>project.dirty,flushActiveField:()=>{},generation:workspace,toast:message=>notices.push(message),syncChrome:()=>{},navigateNode:(stage,nodeId)=>{navigated.push([stage,nodeId]);project.stage=stage;workspace.nodeId=nodeId;workspace.render(host);}});
const app=fs.readFileSync('src/gui/app.js','utf8');vm.runInContext(app.slice(app.indexOf('function prepareWorkflowRepair('),app.indexOf('\nfunction mergeGenerationEnvelope('))+'\nglobalThis.bridge=prepareWorkflowRepair;',sandbox);
local.callbacks.prepareRepair=sandbox.bridge;
assert.equal(local.prepareRepair(run,'Correct from original inputs.'),true);assert.deepEqual(navigated,[['local_rtl_generation','node-a']]);assert.equal(workspace.operation,'repair');assert.equal(workspace.baseJobId,candidate.id);assert.match(workspace.instruction,/failed-S06/);assert.equal(workspace.preview,null);assert.equal(workspace.previewStale,true);assert.match(workspace.previewGate(),/Preview the exact context/);assert.equal(requests.length,0);
project.dirty=true;const before=workspace.instruction;assert.equal(sandbox.bridge(candidate,'must not replace draft'),false);assert.equal(workspace.instruction,before);assert.equal(navigated.length,1);
""")


if __name__ == '__main__':
    unittest.main()
