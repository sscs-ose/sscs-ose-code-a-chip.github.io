"""S05 failure recovery uses saved source/logs; isolated UI QA, not circuit proof."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT


PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const localSource=fs.readFileSync('src/gui/workflow.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class LocalWorkflow','class LocalWorkflow');
vm.runInContext('{'+localSource+'\nglobalThis.LocalWorkflow=LocalWorkflow;}',sandbox);
const candidate={...failed,id:'candidate',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',finished_at:'2026-10-14T00:00:00Z',rtl:'module qa_control; endmodule',rtl_sha256:'original-rtl-hash',input_hash:'original-input-hash'};
const run={id:'failed-S05',node_id:'node-a',stage_id:'local_synthesis',candidate_id:candidate.id,revision_id:'revision-a',requested_revision_id:'revision-a',input_hash:candidate.input_hash,rtl_sha256:candidate.rtl_sha256,netlist:null,netlist_sha256:null,vector_hash:null,testbench_sha256:null,execution_status:'Completed',validation_status:'Failed',review_status:'Awaiting Review',freshness:'Current',finished_at:'2026-10-14T01:00:00Z',tool_configuration:{kind:'native',executable:'yosys'},checks:{executed:true,exit_code:1,tool_version:'Yosys QA fixture version',commands:[{command:['yosys','-Q','-p','read_verilog candidate.v; synth -top qa_control'],status:'Completed',exit_code:1}],stdout:'Yosys starts\nReading saved candidate.v\n',stderr:'candidate.v:12: ERROR: Unsupported process in qa_control.\n'},diagnostics:[{code:'synthesis_failed',severity:'error',message:'Generic synthesis did not produce the requested netlist; inspect the tool log.'}]};
project.stage='local_synthesis';
project.envelope.workflow.push({id:'local_synthesis',implemented:true},{id:'local_netlist_simulation',implemented:true});
project.envelope.generation={submission_protocol_version:"node-submission-v1",implemented:true,jobs:[candidate],nodes:[{node_id:'node-a',accepted_job_id:candidate.id,latest_job_id:candidate.id}]};
project.envelope.workflow_runs=[run];
const prepared=[];
const local=new sandbox.LocalWorkflow({project:()=>project,prepareRepair:(...args)=>{prepared.push(args);return true;},toast:message=>notices.push(message),request:()=>assert.fail('Preparing a draft must not mutate records or send model/tool requests')});
local.nodeId='node-a';local.runs=[run];
const restore=()=>{Object.assign(project,{dirty:false,conflict:null,busy:false,readOnly:false,postlayoutRunning:false,lvsRunning:false,stage:'local_synthesis'});project.envelope.workspace_identity.read_only=false;project.envelope.revision.id='revision-a';project.envelope.generation={submission_protocol_version:"node-submission-v1",implemented:true,jobs:[candidate],nodes:[{node_id:'node-a',accepted_job_id:candidate.id,latest_job_id:candidate.id}]};local.runs=[run];local.runId=null;local.busy=false;local.storageError=null;delete local.activeBatch;delete project.envelope.global_generation;delete project.envelope.physical_workflow;};
"""


class S05RepairGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated client checks.")
        result = subprocess.run([node, "-e", CLIENT + SETUP + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_exact_failed_synthesis_prepares_draft_without_netlist_or_verification_hashes(self):
        self.client(r"""
const before=JSON.stringify([candidate,run]);
assert.equal(local.repairGate(),'');assert.equal(local.prepareRepair(run,'Keep the reset and public interface.'),true);
assert.equal(prepared.length,1);assert.equal(prepared[0][0],candidate);
const instruction=prepared[0][1];
for(const source of ['failed-S05','candidate','revision-a','original-input-hash','original-rtl-hash','Yosys QA fixture version','candidate.v:12: ERROR: Unsupported process in qa_control.','Reading saved candidate.v','synthesis_failed','Keep the reset and public interface.','read_verilog candidate.v; synth -top qa_control'])assert.ok(instruction.includes(source),source);
assert.match(instruction,/Preserve the saved specification and external interface/);
assert.match(instruction,/Prepare Context Preview, then explicitly send Repair node RTL/);
assert.match(instruction,/S05 synthesis again; S06 verifies circuit behavior/);
assert.doesNotMatch(instruction,/Accepted S05 run|Original vectors SHA-256|testbench SHA-256|netlist SHA-256/);
assert.equal(JSON.stringify([candidate,run]),before);assert.equal(requests.length,0);
""")

    def test_stale_foreign_active_and_changed_sources_never_prepare_repair(self):
        self.client(r"""
const changes=[()=>project.readOnly=true,()=>project.envelope.workspace_identity.read_only=true,()=>project.dirty=true,()=>project.conflict='external',()=>project.busy=true,()=>local.busy=true,()=>project.postlayoutRunning=true,()=>project.lvsRunning=true,()=>local.activeBatch=()=>({execution_status:'Running'}),()=>project.envelope.global_generation={submission_protocol_version:"node-submission-v1",jobs:[{execution_status:'Running'}]},()=>project.envelope.physical_workflow={runs:[{execution_status:'Queued'}]},()=>local.storageError={message:'disk'},()=>project.envelope.generation.storage_error={message:'disk'},()=>project.envelope.generation.jobs.push({...candidate,id:'active',execution_status:'Running'}),()=>local.runs.push({...run,id:'active-S05',execution_status:'Running'}),()=>{local.runs.push({...run,id:'newer-failure'});local.runId=run.id;},()=>local.runs=[{...run,freshness:'Stale'}],()=>local.runs=[{...run,finished_at:null}],()=>local.runs=[{...run,validation_status:'Passed'}],()=>project.envelope.generation.nodes[0].latest_job_id='newer-candidate',()=>project.envelope.generation.jobs=[{...candidate,review_status:'Awaiting Review'}],()=>local.runs=[{...run,rtl_sha256:'changed'}],()=>local.runs=[{...run,input_hash:'changed'}],()=>local.runs=[{...run,input_hash:null}],()=>local.runs=[{...run,requested_revision_id:'older'}],()=>local.runs=[{...run,revision_id:'older'}],()=>local.runs=[{...run,candidate_id:'other'}],()=>local.runs=[{...run,node_id:'node-b'}],()=>local.runs=[{...run,stage_id:'local_netlist_simulation'}]];
for(const change of changes){restore();change();const selected=local.selected();assert.notEqual(local.repairGate(selected),'');assert.equal(local.prepareRepair(selected),false);}
assert.equal(prepared.length,0);assert.equal(requests.length,0);
""")

    def test_setup_errors_require_tool_recovery_and_timeout_does_not_assert_rtl_defect(self):
        self.client(r"""
const setup={...run,execution_status:'Failed',validation_status:'Not Checked',error:{code:'invalid_synthesizer',message:'Invalid trusted tool path'},checks:{}};
local.runs=[setup];assert.match(local.repairGate(),/trusted Yosys setup/);assert.equal(local.prepareRepair(setup),false);
assert.match(local.synthesisRecoveryHint(setup),/setup was rejected.*configuration.*rerun S05/);
const unavailable={...run,validation_status:'Unsupported',checks:{executed:false},diagnostics:[{code:'synthesizer_unavailable',message:'Configure trusted Yosys.'}]};
local.runs=[unavailable];assert.ok(local.repairGate());assert.equal(local.prepareRepair(unavailable),false);
const timeout={...run,checks:{...run.checks,commands:[{status:'Timeout',exit_code:null,command:['yosys']}],stdout:'partial synthesis log',stderr:''}};
local.runs=[timeout];assert.equal(local.repairGate(),'');
assert.match(local.synthesisRecoveryHint(timeout),/timed out.*tool setup.*rerun; repair RTL only if/);
assert.match(local.repairInstruction(timeout),/does not prove an RTL defect/);
assert.match(local.repairInstruction(timeout),/"status":"Timeout"/);assert.equal(requests.length,0);
""")

    def test_visible_error_control_carries_optional_note_and_retains_full_logs(self):
        self.client(r"""
const before=JSON.stringify(run),resultHost=el('div',{},el('div',{'data-testid':'workflow-result'}));
local.host=resultHost;local.renderResult();
const recovery=resultHost.querySelector('[data-testid="workflow-synthesis-recovery"]');assert.ok(recovery);
assert.match(text(recovery),/Recover synthesis.*Inspect the saved Yosys error/);
assert.match(text(resultHost.querySelector('[data-testid="workflow-synthesis-first-failure"]')),/candidate.v:12: ERROR/);
assert.match(text(resultHost.querySelector('[data-testid="workflow-checks"]')),/Reading saved candidate.v/);
const repair=resultHost.querySelector('[data-testid="workflow-prepare-repair"]');assert.equal(repair.disabled,false);
resultHost.querySelector('[data-testid="workflow-synthesis-repair-note"]').value='Use a synthesizable reset process.';repair.onclick();
assert.match(prepared[0][1],/Use a synthesizable reset process/);assert.equal(JSON.stringify(run),before);assert.equal(requests.length,0);
const review=new DOMDouble('div');local.renderReview(review);assert.ok(review.querySelector('[data-testid="workflow-review-prepare-repair"]'));assert.equal(review.querySelector('[data-testid="workflow-prepare-repair"]'),null);
project.dirty=true;local.renderResult();assert.equal(resultHost.querySelector('[data-testid="workflow-prepare-repair"]').disabled,true);
restore();local.runs=[{...run,validation_status:'Passed'}];local.renderResult();assert.equal(resultHost.querySelector('[data-testid="workflow-synthesis-recovery"]'),null);
""")

    def test_actual_app_bridge_opens_existing_s04_repair_preview_without_execution(self):
        self.client(r"""
workspace.generation=project.envelope.generation;workspace.selectedJobId=candidate.id;
const navigated=[];Object.assign(sandbox,{state:{envelope:project.envelope,busy:false,externalRevision:null},readOnly:()=>project.readOnly,dirty:()=>project.dirty,executionInputDirty:()=>project.dirty,flushActiveField:()=>{},generation:workspace,toast:message=>notices.push(message),syncChrome:()=>{},navigateNode:(stage,nodeId)=>{navigated.push([stage,nodeId]);project.stage=stage;workspace.nodeId=nodeId;workspace.render(host);}});
const app=fs.readFileSync('src/gui/app.js','utf8');vm.runInContext(app.slice(app.indexOf('function prepareWorkflowRepair('),app.indexOf('\nfunction mergeGenerationEnvelope('))+'\nglobalThis.bridge=prepareWorkflowRepair;',sandbox);
local.callbacks.prepareRepair=sandbox.bridge;
assert.equal(local.prepareRepair(run,'Resolve the actual Yosys error.'),true);assert.deepEqual(navigated,[['local_rtl_generation','node-a']]);
assert.equal(workspace.operation,'repair');assert.equal(workspace.baseJobId,candidate.id);assert.match(workspace.instruction,/failed-S05/);assert.match(workspace.instruction,/candidate.v:12: ERROR/);
assert.equal(workspace.preview,null);assert.equal(workspace.previewStale,true);assert.match(workspace.previewGate(),/Preview the exact context/);assert.equal(requests.length,0);
project.dirty=true;const before=workspace.instruction;assert.equal(sandbox.bridge(candidate,'must not replace draft'),false);assert.equal(workspace.instruction,before);assert.equal(navigated.length,1);
""")

    def test_prompt_and_log_excerpts_are_bounded_without_inventing_error(self):
        self.client(r"""
const oversized={...run,checks:{...run.checks,stdout:'日'.repeat(30000),stderr:'人'.repeat(30000)},diagnostics:Array.from({length:20},(_,i)=>({code:'diagnostic-'+i,message:'文'.repeat(2000)}))};
const instruction=local.repairInstruction(oversized,'注'.repeat(12000));assert.ok(Buffer.byteLength(instruction,'utf8')<32768);assert.ok(instruction.length<=7900);assert.doesNotMatch(instruction,/diagnostic-6:/);assert.match(instruction,/bounded excerpts/);assert.match(instruction,/This repair draft does not establish a pass/);
assert.equal(local.firstSynthesisFailure({...run,checks:{stdout:'start\nERROR: first\nERROR: second',stderr:''}}),'ERROR: first');
assert.equal(local.firstSynthesisFailure({...run,checks:{stdout:'',stderr:''},error:null}),'');
assert.equal(local.firstSynthesisFailure({...run,checks:{stdout:'working\nstill working',stderr:''},error:null}),'working\nstill working');
assert.doesNotMatch(local.synthesisRecoveryHint(run),/RTL is defective|circuit behavior failed/);assert.equal(requests.length,0);
""")


    def test_recorded_environment_and_unknown_unchecked_errors_retry_same_rtl_without_repair(self):
        self.client(r"""
for(const error of [{code:'workflow_environment_error',next_action:'retry_same_RTL',message:'Storage preparation failed',execution_phase:'prepare_synthesis_inputs'},
                    {code:'workflow_error',message:'Tool execution or durable workflow recording failed.'}]) {
 const setup={...run,execution_status:'Failed',validation_status:'Not Checked',error,checks:{}};
 const before=JSON.stringify([candidate,setup]);local.runs=[setup];local.batchGate=()=>'';
 assert.match(local.repairGate(setup),/same saved RTL/);assert.equal(local.prepareRepair(setup),false);
 assert.match(local.synthesisRecoveryHint(setup),/same saved RTL/);
 if(error.code==='workflow_error')assert.match(local.synthesisRecoveryHint(setup),/cause is not established/);
 const resultHost=el('div',{},el('div',{'data-testid':'workflow-result'}));local.host=resultHost;local.renderResult();
 assert.equal(resultHost.querySelector('[data-testid="workflow-prepare-repair"]'),null);
 assert.equal(resultHost.querySelector('[data-testid="workflow-synthesis-repair-note"]'),null);
 const retry=resultHost.querySelector('[data-testid="workflow-retry-same-rtl"]');assert.ok(retry);assert.equal(retry.disabled,false);
 let retries=0;local.startBatch=()=>retries++;retry.onclick();assert.equal(retries,1);
 assert.equal(JSON.stringify([candidate,setup]),before);assert.equal(prepared.length,0);assert.equal(requests.length,0);
}
// A generic exception with actual recorded checks is not reclassified.
const observed={...run,execution_status:'Failed',validation_status:'Not Checked',error:{code:'workflow_error'},checks:{executed:true,stderr:'ERROR: saved synthesis check'}};
local.runs=[observed];assert.equal(local.repairGate(observed),'');assert.doesNotMatch(local.synthesisRecoveryHint(observed),/cause is not established/);
// Explicit environment code without its exact recovery marker does not match.
local.runs=[{...run,error:{code:'workflow_environment_error'},checks:{executed:true}}];assert.equal(local.repairGate(),'');
""")


if __name__ == '__main__':
    unittest.main()
