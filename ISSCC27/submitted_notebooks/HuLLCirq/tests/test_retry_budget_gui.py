"""Real ESM rendering and action checks; no model or EDA requests are sent."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_repair_prompt_console_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]


class RetryBudgetGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated ESM checks.")
        result = subprocess.run(
            [node, "--experimental-vm-modules", "-e", CLIENT +
             "\n(async()=>{\n" + body +
             "\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_blocked_base_estimate_never_claims_a_complete_output_ceiling(self):
        self.client(r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js');
const ui=new GenerationBatchWorkspace(callbacks);
ui.plan={revision_id:'revision-a',profile_revision_id:'profile-a',mode:'synthesis_repair',ready_to_start:false,
 profile:{...project.envelope.llm.profile,max_output_tokens:3000},
 first_request_context:{estimated_input_tokens:13097},items:[{node_id:'fifo',node_name:'Output FIFO',status:'Blocked',reason:'Contract plus ledger exceeds context.'}]};
ui.planSource=ui.sourceIdentity();
const before=JSON.stringify(ui.plan),view=ui.renderPlan(),budget=test(view,'generation-batch-budget').textContent;
assert.match(budget,/Saved base input 13,097/);assert.match(budget,/Complete provider input including conversation was not recorded/);
assert.doesNotMatch(budget,/maximum output.*3,287/);assert.equal(test(view,'generation-batch-start').disabled,true);
const {resolveStageGuidance}=await module('flow_guidance.js');
const guide=resolveStageGuidance({stage:'local_rtl_generation',nodeName:'Job control',generationBatchGuidance:ui.guidance()});
assert.equal(guide.scope,'Request queue: Output FIFO');assert.doesNotMatch(guide.scope,/Job control/);
assert.equal(JSON.stringify(ui.plan),before);assert.equal(requests.length,0);
""")

    def test_complete_budget_includes_retained_context_and_is_visible_per_node(self):
        self.client(r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js'),ui=new GenerationBatchWorkspace(callbacks);
const contextBudget={base_input_estimated_tokens:13097,ledger_input_estimated_tokens:120,retained_history_input_estimated_tokens:20,
 provider_input_estimated_tokens:13237,max_output_tokens:3000,context_window:16384,maximum_output_tokens:3147,total_estimated_tokens:16237,fits:true};
ui.plan={revision_id:'revision-a',profile_revision_id:'profile-a',mode:'synthesis_repair',ready_to_start:true,
 profile:{...project.envelope.llm.profile,max_output_tokens:3000},
 first_request_context:{provider_input_estimated_tokens:13237,messages:[{role:'user',content:'Complete original contract and preserved repair RTL.'}]},
 items:[{node_id:'fifo',node_name:'Output FIFO',status:'Queued',context_budget:contextBudget,source_recovery:{kind:'no_rtl_transport_failure_v1',base_job_id:'base-fifo',source_workflow_run_id:'s05-fifo',failed_job_ids:['failed-fifo']}}]};
ui.planSource=ui.sourceIdentity();const before=JSON.stringify(ui.plan),view=ui.renderPlan();
for(const id of ['generation-batch-budget','generation-batch-budget-fifo']){
 const value=test(view,id).textContent;assert.match(value,/13,237.*3,000 = 16,237 \/ context 16,384/);
 assert.match(value,/maximum output for this request 3,147/);assert.match(value,/conversation references 120.*retained turns 20/);
 assert.doesNotMatch(value,/maximum output.*3,287/);
}
assert.equal(test(view,'generation-batch-start').disabled,false);assert.equal(ui.guidance().primary.label,'Start repair batch');
assert.match(view.textContent,/Connection\/transport retry · original RTL and S05 source retained/);
assert.equal(JSON.stringify(ui.plan),before);assert.equal(requests.length,0);
""")

    def test_transport_failure_uses_only_authorized_prior_source_and_previews_all_together(self):
        self.client(r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js'),ui=new GenerationBatchWorkspace(callbacks);
project.design.nodes.push({id:'node-b',name:'Output FIFO'});
const base=(id,node)=>({id,node_id:node,rtl:'module saved; endmodule',freshness:'Current',execution_status:'Completed',review_status:'Accepted',finished_at:'saved'});
const failed=(id,node,baseId)=>({id,node_id:node,base_job_id:baseId,rtl:null,freshness:'Current',execution_status:'Failed',error:{category:'connection_error'}});
project.envelope.generation={jobs:[base('base-a','node-a'),failed('failed-a','node-a','base-a'),base('base-b','node-b'),failed('failed-b','node-b','base-b')],
 nodes:[{node_id:'node-a',latest_job_id:'failed-a',accepted_job_id:'base-a'},{node_id:'node-b',latest_job_id:'failed-b',accepted_job_id:'base-b'}]};
project.envelope.workflow_runs=['a','b'].map(key=>({id:`s05-${key}`,node_id:`node-${key}`,candidate_id:`base-${key}`,stage_id:'local_synthesis',execution_status:'Completed',validation_status:'Failed',freshness:'Current',finished_at:'saved',checks:{executed:true}}));
project.envelope.generation_batches={batches:[],repair_sources:['a','b'].map(key=>({node_id:`node-${key}`,latest_job_id:`failed-${key}`,base_job_id:`base-${key}`,source_workflow_run_id:`s05-${key}`,recovery:{kind:'no_rtl_transport_failure_v1',failed_job_ids:[`failed-${key}`]}}))};
ui.receive(project.envelope);assert.equal(ui.failedSynthesis().length,2);assert.equal(ui.accepted('node-a'),false);
const before=JSON.stringify(project.envelope),host=new DOMNode();ui.renderGeneration(host);
assert.match(test(host,'workflow-repair-transport-node-a').textContent,/returned no RTL/);
assert.match(test(host,'workflow-batch-repair-status').textContent,/2 current failed nodes/);
ui.plan={revision_id:'revision-a',profile_revision_id:'profile-a',mode:'synthesis_repair',ready_to_start:false,items:[{node_id:'node-b',node_name:'Output FIFO',status:'Blocked'}]};ui.planSource=ui.sourceIdentity();
const guide=ui.guidance();assert.equal(guide.primary.label,'Preview all 2 repair retries');assert.match(guide.summary,/original RTL and S05 diagnostics are preserved/);
const previews=[];ui.callbacks.request=async(route,body)=>{previews.push([route,body]);return{...ui.plan,ready_to_start:true,items:project.envelope.generation_batches.repair_sources.map(source=>({node_id:source.node_id,base_job_id:source.base_job_id,expected_latest_job_id:source.latest_job_id,status:'Queued'}))};};
await guide.primary.action();assert.equal(previews.length,1);assert.equal(previews[0][0],'generation/batches/preview');
assert.deepEqual(Array.from(previews[0][1].node_ids),['node-a','node-b']);assert.equal('retry_batch_id' in previews[0][1],false);
assert.equal(ui.planCurrent(),true);assert.equal(ui.guidance().scope,'Request queue: 2 nodes');
assert.equal(JSON.stringify(project.envelope),before);assert.equal(requests.length,0);
project.envelope.generation.nodes[0].latest_job_id='new-rtl';assert.equal(ui.planCurrent(),false);assert.equal(ui.failedSynthesis().length,1);
""")

    def test_later_base_budget_is_distinct_from_a_packed_request_and_analysis_keeps_identity(self):
        self.client(r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js'),ui=new GenerationBatchWorkspace(callbacks);
ui.plan={profile:{max_output_tokens:3000,context_window:16384},items:[]};
const item={node_id:'later',context_budget:{scope:'base_contract',provider_input_estimated_tokens:13097,max_output_tokens:3000,context_window:16384,total_estimated_tokens:16097,maximum_output_tokens:3287}};
assert.match(ui.itemBudget(item),/Base input 13,097.*Later conversation is packed/);assert.doesNotMatch(ui.itemBudget(item),/maximum output/);
project.envelope.generation={jobs:[{id:'base',node_id:'node-a',rtl:'module saved; endmodule',freshness:'Current'}],nodes:[{node_id:'node-a',latest_job_id:'failed',accepted_job_id:'base'}]};
project.envelope.workflow_runs=[{id:'s05',node_id:'node-a',candidate_id:'base',stage_id:'local_synthesis',execution_status:'Completed',validation_status:'Failed',finished_at:'saved',freshness:'Current',checks:{executed:true}}];
project.envelope.generation_batches={repair_sources:[{node_id:'node-a',latest_job_id:'failed',base_job_id:'base',source_workflow_run_id:'s05',recovery:{kind:'no_rtl_transport_failure_v1'}}]};
const analysis={source:{node_id:'node-a',candidate_id:'base',run_id:'s05'},profile_revision_id:'profile-a'};
assert.equal(ui.analysisCurrent(analysis),true);assert.equal(ui.analysisCurrent({...analysis,source:{...analysis.source,run_id:'old-s05'}}),false);
project.envelope.generation.nodes[0].latest_job_id='newer';assert.equal(ui.analysisCurrent(analysis),false);assert.equal(requests.length,0);
""")

    def test_no_frontend_fallback_from_an_unapproved_or_mismatched_repair_source(self):
        self.client(r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js'),ui=new GenerationBatchWorkspace(callbacks);
project.envelope.generation={jobs:[{id:'base',node_id:'node-a',rtl:'module saved; endmodule',freshness:'Current'}],nodes:[{node_id:'node-a',latest_job_id:'no-rtl-failed',accepted_job_id:'base'}]};
project.envelope.workflow_runs=[{id:'s05',node_id:'node-a',stage_id:'local_synthesis',candidate_id:'base',freshness:'Current',finished_at:'saved',execution_status:'Completed',validation_status:'Failed',checks:{executed:true}}];
const valid={node_id:'node-a',latest_job_id:'no-rtl-failed',base_job_id:'base',source_workflow_run_id:'s05',recovery:{kind:'no_rtl_transport_failure_v1'}};
for(const invalid of [null,{...valid,latest_job_id:'earlier-request'},{...valid,base_job_id:'other-base'},{...valid,source_workflow_run_id:'other-run'},{...valid,recovery:{kind:'unqualified'}}]){
 project.envelope.generation_batches={repair_sources:invalid?[invalid]:[]};assert.equal(ui.failedSynthesis().length,0);
}
project.envelope.generation_batches={repair_sources:[valid]};assert.equal(ui.failedSynthesis().length,1);
assert.equal(ui.accepted('node-a'),false);assert.equal(requests.length,0);
""")


if __name__ == '__main__':
    unittest.main()
