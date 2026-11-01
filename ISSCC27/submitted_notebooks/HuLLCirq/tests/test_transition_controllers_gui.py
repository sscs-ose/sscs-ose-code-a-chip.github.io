"""Current-source local controller transitions; no model or EDA execution."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_repair_prompt_console_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const {LocalWorkflow}=await module('workflow.js'),{GenerationBatchWorkspace}=await module('generation_batch.js'),{GenerationWorkspace}=await module('generation.js');
project.stage='local_synthesis';project.envelope.workflow.push({id:'local_synthesis',implemented:true},{id:'local_netlist_simulation',implemented:true},{id:'node_implementation_specs',implemented:true});
const navigations=[];callbacks.navigate=(...args)=>navigations.push(args);callbacks.chrome=()=>{};
const candidate=(id='rtl-a',node_id='node-a')=>({id,node_id,revision_id:'revision-a',input_hash:'input-'+node_id,rtl_sha256:'sha-'+id,rtl:'module qa_control; endmodule',execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',finished_at:'saved',checks:{interface:{validation_status:'Passed'}}});
const synthesized=(source,id='s05-'+source.id,passed=true)=>({id,node_id:source.node_id,stage_id:'local_synthesis',candidate_id:source.id,revision_id:source.revision_id,requested_revision_id:'revision-a',input_hash:source.input_hash,rtl_sha256:source.rtl_sha256,netlist:passed?'module mapped; endmodule':null,netlist_sha256:'net-'+id,execution_status:'Completed',validation_status:passed?'Passed':'Failed',review_status:passed?'Accepted':'Awaiting Review',freshness:'Current',finished_at:'saved',checks:{executed:true,stdout:passed?'PASS':'ERROR: multiple conflicting drivers'},diagnostics:[]});
const old=candidate('rtl-old'),current=candidate('rtl-current'),oldFailed=synthesized(old,'s05-old',false),currentPass=synthesized(current);
function adopt(jobs){project.envelope.generation={jobs,nodes:jobs.map(job=>({node_id:job.node_id,latest_job_id:job.id,accepted_job_id:job.id,freshness:'Current',review_status:'Accepted'}))};}
adopt([current]);const local=new LocalWorkflow(callbacks);local.nodeId='node-a';local.runs=[oldFailed,currentPass];project.envelope.workflow_runs=local.runs;
const simulation=(source,prior,id='s06-'+source.id)=>({...synthesized(source,id),stage_id:'local_netlist_simulation',prior_run_id:prior.id,netlist_sha256:prior.netlist_sha256});
"""


class TransitionControllersGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node required for GUI controller tests')
        result = subprocess.run([node, '--experimental-vm-modules', '-e', CLIENT + '\n(async()=>{\n' + SETUP + body + '\nassert.equal(requests.length,0);})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'], cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_second_s05_visit_follows_new_source_and_pass(self):
        self.client(r"""
local.runs=[oldFailed];assert.equal(local.selected(),undefined);assert.equal(local.runCurrent(oldFailed),false);
local.runId=oldFailed.id;local.runPinned=false;local.receive({...project.envelope,workflow_runs:[oldFailed,currentPass]});assert.equal(local.selected().id,currentPass.id);assert.equal(local.runId,null);assert.equal(local.runCurrent(currentPass),true);
const review=new DOMNode();local.renderReview(review);assert.equal(test(review,'workflow-continue').disabled,false);assert.equal(test(review,'workflow-review-prepare-repair').disabled,true);
""")

    def test_deliberate_history_can_be_inspected_but_not_advanced(self):
        self.client(r"""
local.runId=oldFailed.id;local.runPinned=true;local.receive({...project.envelope,workflow_runs:local.runs});assert.equal(local.selected().id,oldFailed.id);
const host=new DOMNode(),result=new DOMNode();result.setAttribute('data-testid','workflow-result');host.append(result);local.host=host;local.renderResult();assert.match(test(host,'workflow-historical-source').textContent,/earlier sources/);assert.match(test(host,'workflow-run-status').textContent,/Earlier source/);
const review=new DOMNode();local.renderReview(review);for(const id of ['workflow-accept','workflow-continue','workflow-request-changes','workflow-review-prepare-repair'])assert.equal(test(review,id).disabled,true,id);
local.runId=null;local.runPinned=false;assert.equal(local.selected().id,currentPass.id);
""")

    def test_old_s06_pass_does_not_verify_repaired_rtl(self):
        self.client(r"""
project.stage='local_netlist_simulation';const oldPass=synthesized(old),oldSimulation=simulation(old,oldPass);local.runs=[oldPass,oldSimulation,currentPass];assert.equal(local.selected(),undefined);assert.equal(local.runCurrent(oldSimulation),false);assert.equal(local.prior().id,currentPass.id);assert.equal(local.gate(),'');
const review=new DOMNode();local.renderReview(review);assert.equal(test(review,'workflow-continue'),null);assert.match(review.textContent,/Run this saved node/);
""")

    def test_s06_requires_exact_current_accepted_s05_netlist(self):
        self.client(r"""
project.stage='local_netlist_simulation';const prior=synthesized(current,'s05-earlier'),earlier=simulation(current,prior,'s06-earlier');local.runs=[prior,earlier,currentPass];assert.equal(local.runCurrent(earlier),false);assert.equal(local.selected(),undefined);
const fresh=simulation(current,currentPass);local.runs.push(fresh);assert.equal(local.currentRun().id,fresh.id);assert.equal(local.latestForCurrentSource().id,fresh.id);const review=new DOMNode();local.renderReview(review);assert.equal(test(review,'workflow-continue').disabled,false);
""")

    def test_mismatched_lineage_cannot_advance(self):
        self.client(r"""
assert.equal(local.runCurrent(currentPass),true);for(const [key,value] of [['revision_id','revision-old'],['input_hash','other-input'],['rtl_sha256','other-rtl'],['freshness','Stale']])assert.equal(local.runCurrent({...currentPass,[key]:value}),false,key);
project.envelope.revision.id='graph-position-only-revision';assert.equal(local.runCurrent(currentPass),true,'A nonsemantic save preserves current source evidence');
""")

    def test_old_batch_inspect_opens_current_source_and_history_is_kept(self):
        self.client(r"""
local.batches=[{id:'batch-old',execution_status:'Completed',validation_status:'Failed',items:[{node_id:'node-a',run_id:oldFailed.id,status:'Failed'}]}];local.batchId='batch-old';const host=new DOMNode(),batchHost=new DOMNode(),historyHost=new DOMNode();batchHost.setAttribute('data-testid','workflow-batch');historyHost.setAttribute('data-testid','workflow-history');host.append(batchHost,historyHost);local.host=host;local.renderBatch();const inspect=test(host,'workflow-batch-inspect-node-a');assert.ok(inspect);inspect.click();assert.equal(local.selected().id,currentPass.id);
local.renderHistory();const oldButton=test(host,'workflow-history-'+oldFailed.id);assert.ok(oldButton);oldButton.click();assert.equal(local.selected().id,oldFailed.id);assert.equal(local.runPinned,true);
""")

    def test_workspace_switch_resets_history_pin(self):
        self.client(r"""
local.receive({...project.envelope,workflow_runs:local.runs});local.runId=oldFailed.id;local.runPinned=true;project.envelope.workspace_identity.session_id='different-session';local.receive({...project.envelope,workflow_runs:local.runs});assert.equal(local.runId,null);assert.equal(local.runPinned,false);assert.equal(local.selected().id,currentPass.id);
""")

    def test_completed_s04_batch_respects_current_s05_completion(self):
        self.client(r"""
project.stage='local_rtl_generation';const batches=new GenerationBatchWorkspace(callbacks);batches.batches=[{id:'finished',source_current:true,execution_status:'Completed',items:[{node_id:'node-a',job_id:current.id,status:'Accepted'}]}];const guide=batches.guidance();assert.equal(guide.title,'S04 and S05 are complete for the current RTL');assert.equal(guide.primary.label,'Continue to Netlist Simulation');guide.primary.action();assert.deepEqual(navigations,[['local_netlist_simulation']]);
""")

    def test_batch_history_selection_does_not_replay_an_old_failure(self):
        self.client(r"""
project.stage='local_rtl_generation';const batches=new GenerationBatchWorkspace(callbacks);batches.batches=[{id:'old-batch',source_current:true,execution_status:'Completed',items:[{node_id:'node-a',job_id:old.id,status:'Failed'}]},{id:'new-batch',source_current:true,execution_status:'Completed',items:[{node_id:'node-a',job_id:current.id,status:'Accepted'}]}];batches.batchId='old-batch';assert.equal(batches.selectedBatch().id,'old-batch');assert.equal(batches.guidance().primary.label,'Continue to Netlist Simulation');
""")

    def test_one_superseded_node_does_not_hide_another_unresolved_request(self):
        self.client(r"""
project.stage='local_rtl_generation';project.design.nodes.push({id:'node-b',name:'Still missing',module_name:'qa_missing'});const batches=new GenerationBatchWorkspace(callbacks);project.envelope.generation.jobs.push(old);batches.batches=[{id:'part-old',source_current:true,execution_status:'Completed',items:[{node_id:'node-a',job_id:old.id,status:'Failed'},{node_id:'node-b',job_id:null,status:'Failed'}]}];assert.equal(batches.superseded(batches.batches[0]),true);assert.equal(batches.remaining(batches.batches[0]).length,1);assert.equal(batches.guidance().primary.label,'Preview remaining requests');
""")

    def test_completed_subset_does_not_claim_all_rtl_ready(self):
        self.client(r"""
project.stage='local_rtl_generation';project.design.nodes.push({id:'node-b',name:'Missing',module_name:'qa_missing'});const batches=new GenerationBatchWorkspace(callbacks);batches.batches=[{id:'subset',source_current:true,execution_status:'Completed',items:[{node_id:'node-a',job_id:current.id,status:'Accepted'}]}];assert.equal(batches.guidance(),null);
""")

    def test_s04_historical_guide_returns_to_latest_without_generation(self):
        self.client(r"""
project.stage='local_rtl_generation';const generation=new GenerationWorkspace(callbacks);project.envelope.generation.jobs.unshift(old);generation.generation=project.envelope.generation;generation.llm=project.envelope.llm;generation.nodeId='node-a';generation.selectedJobId=old.id;const guide=generation.guidance();assert.equal(guide.title,'You are viewing an earlier RTL request');generation.renderJobList=()=>{};generation.renderResult=()=>{};generation.renderReview=()=>{};guide.primary.action();assert.equal(generation.selectedJobId,current.id);assert.equal(generation.guidance().primary.label,'Continue this node to S05');
""")

    def test_remaining_nodes_require_latest_candidate_acceptance(self):
        self.client(r"""
project.design.nodes.push({id:'node-b',name:'New RTL pending',module_name:'qa_b'});const acceptedB=candidate('accepted-b','node-b'),newB={...candidate('new-b','node-b'),review_status:'Awaiting Review'};project.envelope.generation.jobs.push(acceptedB,newB);project.envelope.generation.nodes.push({node_id:'node-b',accepted_job_id:acceptedB.id,latest_job_id:newB.id,review_status:'Accepted',freshness:'Current'});const generation=new GenerationWorkspace(callbacks);generation.generation=project.envelope.generation;generation.nodeId='node-a';assert.equal(generation.nextUnfinishedNode().id,'node-b');
""")

    def test_stale_unsent_preview_does_not_override_current_s04_s05_completion(self):
        self.client(r"""
project.stage='local_rtl_generation';const batches=new GenerationBatchWorkspace(callbacks);batches.plan={plan_id:'old-plan',mode:'synthesis_repair',revision_id:'revision-a',profile_revision_id:'profile-a',ready_to_start:true,items:[{node_id:'node-a',expected_latest_job_id:old.id,instruction:'Old saved correction',status:'Queued'}]};batches.planSource=batches.sourceIdentity();const before=JSON.stringify(batches.plan),guide=batches.guidance();assert.equal(guide.primary.label,'Continue to Netlist Simulation');assert.equal(guide.secondary.label,'Inspect saved preview');guide.primary.action();assert.deepEqual(navigations,[['local_netlist_simulation']]);let focused=false;batches.focus=()=>{focused=true};guide.secondary.action();assert.equal(focused,true);assert.equal(JSON.stringify(batches.plan),before);
const rendered=batches.renderPlan();assert.equal(test(rendered,'generation-batch-start').disabled,true);assert.ok(test(rendered,'generation-batch-rebuild'));assert.equal(JSON.stringify(batches.plan),before);
""")

    def test_stale_unsent_preview_routes_current_rtl_to_pending_s05(self):
        self.client(r"""
project.stage='local_rtl_generation';project.envelope.workflow_runs=[oldFailed];const batches=new GenerationBatchWorkspace(callbacks);batches.plan={plan_id:'old-plan',mode:'synthesis_repair',revision_id:'revision-a',profile_revision_id:'profile-a',ready_to_start:true,items:[{node_id:'node-a',expected_latest_job_id:old.id,instruction:'Old saved correction',status:'Queued'}]};batches.planSource=batches.sourceIdentity();const before=JSON.stringify(batches.plan),guide=batches.guidance();assert.equal(guide.primary.label,'Open Local Synthesis');assert.equal(guide.secondary.label,'Inspect saved preview');guide.primary.action();assert.deepEqual(navigations,[['local_synthesis']]);assert.equal(JSON.stringify(batches.plan),before);
""")

    def test_fresh_explicit_preview_keeps_start_even_when_old_work_is_complete(self):
        self.client(r"""
project.stage='local_rtl_generation';const batches=new GenerationBatchWorkspace(callbacks);batches.plan={plan_id:'fresh-plan',mode:'generate',revision_id:'revision-a',profile_revision_id:'profile-a',ready_to_start:true,items:[{node_id:'node-a',expected_latest_job_id:current.id,instruction:'Explicit new generation',status:'Queued'}]};batches.planSource=batches.sourceIdentity();assert.equal(batches.planCurrent(),true);assert.equal(batches.guidance().primary.label,'Start generation batch');assert.equal(batches.guidance().secondary.label,'Read request instructions');assert.equal(test(batches.renderPlan(),'generation-batch-start').disabled,false);
""")


if __name__ == '__main__':
    unittest.main()
