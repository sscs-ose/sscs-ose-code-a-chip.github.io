"""Visible source-bound repair problems; isolated ESM events, no model or EDA."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_repair_prompt_console_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js');
const ui=new GenerationBatchWorkspace(callbacks),host=new DOMNode();
const nodes=[{id:'node-a',name:'Operand buffer'},{id:'node-b',name:'Output FIFO'}];
project.design.nodes=nodes;
project.envelope.generation={jobs:nodes.map((node,index)=>({id:'candidate-'+index,node_id:node.id,rtl:'module saved; endmodule',rtl_sha256:'hash-'+index,freshness:'Current',review_status:'Accepted',execution_status:'Completed',finished_at:'saved'})),nodes:nodes.map((node,index)=>({node_id:node.id,latest_job_id:'candidate-'+index,accepted_job_id:'candidate-'+index}))};
project.envelope.workflow_runs=nodes.map((node,index)=>({id:'s05-'+index,node_id:node.id,candidate_id:'candidate-'+index,rtl_sha256:'hash-'+index,stage_id:'local_synthesis',freshness:'Current',execution_status:'Completed',validation_status:'Failed',finished_at:'saved',checks:{executed:true,stderr:index?'candidate.v:23: ERROR: syntax error, unexpected OP_CAST':'candidate.v:26: ERROR: Invalid array access.'}}));
const items=nodes.map((node,index)=>({node_id:node.id,node_name:node.name,operation:'repair',status:'Blocked',expected_latest_job_id:'candidate-'+index,base_job_id:'candidate-'+index,source_workflow_run_id:'s05-'+index,
 repair_guidance:{source:{node_id:node.id,candidate_id:'candidate-'+index,run_id:'s05-'+index,revision_id:'revision-a'},same_plan_repeated:true,analysis_required:false,analysis_reviewed:false,additional_instruction:'',repeat_status:{outcome:'unchanged'},evidence:{full_record_url:'/api/workflow/runs/s05-'+index}},
 repair_explanation:{version:'test-display',source:{node_id:node.id,candidate_id:'candidate-'+index,run_id:'s05-'+index,revision_id:'revision-a',rtl_sha256:'hash-'+index},comparison:{outcome:'unchanged'},issues:[{diagnostic:{raw_message:project.envelope.workflow_runs[index].checks.stderr,line:index?23:26,source:index?"fifo_data <= '{default:0};":"bank_a <= '0;"},code_context:[{line:index?22:25,text:'if (rst) begin',is_target:false},{line:index?23:26,text:index?"fifo_data <= '{default:0};":"bank_a <= '0;",is_target:true}],explanation:'The source assigns an entire unpacked array.',actions:[index?'Remove the unsupported fifo_data whole-array write.':'Remove the unsupported bank_a whole-array write.'],preserve:['Saved reset semantics.'],assumptions:[],confidence:'confirmed'}],previous_instruction:{text:'Previous saved instruction '+index,job_id:'candidate-'+index,base_job_id:'previous-'+index,run_id:'s05-'+index,diff:''},diagnostic_comparison:{remaining:['same diagnosed source'],newly_reported:[],not_reported:[],limits:'Lexical diagnostic comparison only.'}}}));
ui.plan={revision_id:'revision-a',profile_revision_id:'profile-a',mode:'synthesis_repair',ready_to_start:false,gate_reason:'The same repair plan left the problem unresolved.',profile:project.envelope.llm.profile,items};
ui.planSource=ui.sourceIdentity();ui.generationHost=host;ui.renderGeneration(host);
"""


class RepairProblemGuiTests(unittest.TestCase):
    def client(self, body, setup=SETUP):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated ESM action checks.")
        result = subprocess.run(
            [node, "--experimental-vm-modules", "-e", CLIENT +
             "\n(async()=>{\n" + setup + body +
             "\nassert.equal(requests.length,0);})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_unresolved_problems_are_visible_before_instruction_with_two_separate_sources(self):
        self.client(r"""
const panel=test(host,'repair-unresolved-problems'),input=test(host,'workflow-batch-repair-instruction');assert.ok(panel);assert.ok(input);
assert.equal(host.querySelectorAll('details').some(details=>details.contains(panel)),false);
const order=descendants(host);assert.ok(order.indexOf(panel)<order.indexOf(input));
const buffer=test(panel,'repair-problem-node-a'),fifo=test(panel,'repair-problem-node-b');
assert.match(buffer.textContent,/candidate.v:26: ERROR: Invalid array access/);assert.match(buffer.textContent,/bank_a/);assert.doesNotMatch(buffer.textContent,/fifo_data/);
assert.match(fifo.textContent,/candidate.v:23: ERROR: syntax error, unexpected OP_CAST/);assert.match(fifo.textContent,/fifo_data/);assert.doesNotMatch(fifo.textContent,/bank_a/);
assert.match(test(buffer,'repair-problem-node-a-source-0').textContent,/> 26 \| bank_a <= '0;/);
assert.match(test(buffer,'repair-problem-node-a-comparison').textContent,/identical RTL.*requested changes were not applied/);
assert.match(test(buffer,'repair-problem-node-a-actions-0').textContent,/bank_a whole-array write/);
assert.match(test(fifo,'repair-problem-node-b-diff').textContent,/No differences/);
assert.equal(test(panel,'repair-problem-node-a-stale'),null);assert.equal(test(panel,'repair-problem-node-b-stale'),null);
""")

    def test_repeated_gate_focuses_real_problem_panel_and_does_not_execute_or_change_sources(self):
        self.client(r"""
const before=JSON.stringify({plan:ui.plan,envelope:project.envelope}),guide=ui.guidance();
assert.equal(guide.primary.label,'Inspect unresolved problems');assert.match(guide.summary,/Operand buffer:.*Invalid array access.*Output FIFO:.*OP_CAST/);assert.match(guide.summary,/not a new synthesis error/);
guide.primary.action();const panel=test(host,'repair-unresolved-problems');assert.equal(panel.focusCount,1);assert.equal(panel.scrollCount,1);
guide.secondary.action();assert.equal(test(host,'workflow-batch-repair-instruction').focusCount,1);
test(host,'repair-problem-node-a-edit').click();assert.equal(test(host,'workflow-batch-repair-instruction').focusCount,2);
test(host,'repair-problem-node-a-read').click();assert.equal(test(host,'generation-batch-readable-request').focusCount,1);
assert.equal(test(host,'generation-batch-start').disabled,true);assert.equal(test(host,'generation-batch-provider-settings'),null);
assert.match(test(host,'generation-batch-budget').textContent,/No request prepared: review unresolved problems/);
assert.doesNotMatch(test(host,'generation-batch-budget').textContent,/context window|maximum output|Saved base input/);
await ui.start();assert.equal(JSON.stringify({plan:ui.plan,envelope:project.envelope}),before);
""")

    def test_controls_are_outside_checkbox_labels_and_previous_current_inspection_is_read_only(self):
        self.client(r"""
for(const label of host.querySelectorAll('label'))assert.equal(label.querySelectorAll('button').length,0);
const inspected=[];ui.callbacks.inspect=(...args)=>inspected.push(args);ui.renderGeneration(host);
test(host,'repair-problem-node-a-previous').click();test(host,'repair-problem-node-a-current').click();
assert.deepEqual(inspected,[['previous-0','node-a'],['candidate-0','node-a']]);assert.equal(ui.instruction,'');assert.equal(ui.busy,false);
""")

    def test_source_or_profile_changes_label_saved_facts_earlier_and_disable_analysis(self):
        self.client(r"""
for(const mutate of [()=>project.envelope.llm.profile_revision_id='profile-new',()=>project.envelope.generation.nodes[0].latest_job_id='new-rtl',()=>project.envelope.workflow_runs[0].id='new-s05']){
 project.envelope.llm.profile_revision_id='profile-a';project.envelope.generation.nodes[0].latest_job_id='candidate-0';project.envelope.workflow_runs[0].id='s05-0';mutate();ui.renderGeneration(host);
 assert.match(test(host,'repair-problem-node-a-stale').textContent,/Earlier preview/);assert.equal(test(host,'repair-problem-node-a-analyze').disabled,true);assert.equal(test(host,'repair-problem-node-a-edit').disabled,true);
}
project.envelope.llm.profile_revision_id='profile-a';project.envelope.generation.nodes[0].latest_job_id='candidate-0';project.envelope.workflow_runs[0].id='s05-0';items[0].repair_explanation.source.candidate_id='wrong-node-source';ui.renderGeneration(host);assert.ok(test(host,'repair-problem-node-a-stale'));assert.equal(test(host,'repair-problem-node-b-stale'),null);
""")

    def test_legacy_fallback_matches_actions_only_to_saved_diagnostic_anchor(self):
        self.client(r"""
delete items[0].repair_explanation;items[0].repair_guidance.evidence.actionable_diagnostics=[{line:26,source:"bank_a <= '0;",raw_message:'candidate.v:26: ERROR: Invalid array access.'}];
items[0].repair_guidance.changes=[{locations:[{line:26,source:"bank_a <= '0;"}],confidence:'confirmed',facts:['Saved source is a whole-array assignment.'],actions:['Remove bank_a reset write.'],preserve:['Preserve storage.']},{locations:[{line:99,source:'other <= 1;'}],facts:['Unrelated cause must remain separate.'],actions:['Unrelated action must not appear.']}];
items[0].repair_guidance.recent_attempts=[{instruction:'Old complete instruction',diff:'',base_job_id:'previous-0'}];ui.renderGeneration(host);
const panel=test(host,'repair-problem-node-a');assert.match(panel.textContent,/Saved source is a whole-array assignment/);assert.match(panel.textContent,/Remove bank_a reset write/);assert.doesNotMatch(test(panel,'repair-problem-node-a-issue-0').textContent,/Unrelated/);assert.match(test(panel,'repair-problem-node-a-unmatched-proposals').textContent,/association not established/);assert.match(test(panel,'repair-problem-node-a-source-0').textContent,/> 26/);assert.match(panel.textContent,/Earlier preview: source excerpts/);
""")

    def test_unknown_diagnostic_has_no_invented_location_cause_or_solution(self):
        self.client(r"""
delete items[0].repair_explanation;items[0].repair_guidance.evidence.actionable_diagnostics=[{raw_message:'ERROR: unknown vendor primitive <script>never execute</script>'}];items[0].repair_guidance.changes=[];
ui.renderGeneration(host);const panel=test(host,'repair-problem-node-a');assert.match(panel.textContent,/location not recorded/);assert.match(panel.textContent,/No source location was recorded/);assert.match(panel.textContent,/No qualified correction is available/);assert.equal(test(panel,'repair-problem-node-a-source-0'),null);
assert.equal(test(panel,'repair-problem-node-a-diagnostic-0').children.length,0);assert.match(test(panel,'repair-problem-node-a-diagnostic-0').textContent,/<script>/);assert.equal(test(panel,'repair-problem-node-a-analyze').disabled,false);
""")

    def test_changed_rtl_diagnostic_identity_and_not_reported_are_not_declared_resolved(self):
        self.client(r"""
items[0].repair_explanation.comparison.outcome='same_diagnostic';items[0].repair_explanation.diagnostic_comparison.not_reported=['Earlier error not seen'];items[0].repair_explanation.comparison.previous_rtl_url='javascript:evil()';items[0].repair_explanation.comparison.current_rtl_url='https://bad.example/';items[0].repair_guidance.evidence.full_record_url='/api/workflow/runs/s05-0';
ui.renderGeneration(host);const panel=test(host,'repair-problem-node-a');assert.match(test(panel,'repair-problem-node-a-comparison').textContent,/RTL changed.*same source-backed diagnostic remains/);assert.match(panel.textContent,/Not reported this time · does not prove resolution/);
assert.doesNotMatch(panel.textContent,/Earlier error.*resolved|all errors cleared/);const links=panel.querySelectorAll('a');assert.equal(links.length,1);assert.equal(links[0].getAttribute('rel'),'noopener');
""")

    def test_saved_record_links_use_active_workspace_session_and_block_unsafe_urls(self):
        self.client(r"""
const {setWorkspaceSession}=await module('workspace_transport.js');setWorkspaceSession('current session+exact');
items[0].repair_explanation.comparison.previous_rtl_url='/api/generation/jobs/previous-0';items[0].repair_explanation.comparison.current_rtl_url='/api/generation/jobs/candidate-0';
ui.renderGeneration(host);const links=test(host,'repair-problem-node-a').querySelectorAll('a');assert.equal(links.length,3);
for(const link of links){const address=new URL(link.href,'http://localhost:9999/');assert.equal(address.searchParams.get('session_id'),'current session+exact');assert.equal(address.origin,'http://localhost:9999');}
items[0].repair_explanation.comparison.previous_rtl_url='/api/\\\\bad.example/file';items[0].repair_explanation.comparison.current_rtl_url='/api/\ninvalid';ui.renderGeneration(host);assert.equal(test(host,'repair-problem-node-a').querySelectorAll('a').length,1);
""")

    def test_repeated_unchanged_manual_correction_keeps_the_inspection_gate(self):
        self.client(r"""
for(const item of items){item.repair_guidance.additional_instruction='Same previous manual correction';item.repair_guidance.manual_correction_revised=false;}
ui.renderGeneration(host);assert.equal(ui.guidance().primary.label,'Inspect unresolved problems');assert.match(test(host,'generation-batch-budget').textContent,/No request prepared/);assert.equal(test(host,'generation-batch-start').disabled,true);
""")

    def test_lineless_driver_diagnostic_uses_only_matching_saved_write_locations(self):
        self.client(r"""
delete items[0].repair_explanation;items[0].repair_guidance.evidence.actionable_diagnostics=[{target:'top.\\busy',raw_message:'Warning: multiple conflicting drivers for top.\\busy:'}];
items[0].repair_guidance.changes=[{rule_id:'conflicting_driver_ownership',confidence:'confirmed',facts:['Actual source writes busy from two owners.'],locations:[{line:43,source:'busy <= 1; '},{line:98,source:'assign busy = busy_reg;'}],actions:['Keep a single busy driver.']}];
ui.renderGeneration(host);const panel=test(host,'repair-problem-node-a'),issue=test(panel,'repair-problem-node-a-issue-0');assert.match(issue.textContent,/location not recorded/);assert.match(issue.textContent,/single busy driver/);assert.match(issue.textContent,/43 \| busy <= 1/);assert.match(issue.textContent,/98 \| assign busy/);assert.equal(test(issue,'repair-problem-node-a-source-0'),null);
""")

    def test_reviewed_model_cause_and_expected_result_remain_hypotheses(self):
        self.client(r"""
delete items[0].repair_explanation;items[0].repair_guidance.evidence.actionable_diagnostics=[{line:26,source:"bank_a <= '0;",raw_message:'candidate.v:26: ERROR: Invalid array access.'}];
items[0].repair_guidance.changes=[{rule_id:'model_assisted_analysis_v1',confidence:'hypothesis',facts:[],cause:'A whole-array write may be unsupported.',locations:[{line:26,source:"bank_a <= '0;"}],actions:['Inspect the declared object first.'],expected_result:'Invalid array access should no longer be reported.',assumptions:['Needs actual synthesis.']}];
ui.renderGeneration(host);const issue=test(host,'repair-problem-node-a-issue-0');assert.match(issue.textContent,/Model-proposed cause \(not validated\): A whole-array write/);assert.match(issue.textContent,/Expected diagnostic change · proposed, not verified/);assert.match(test(issue,'repair-problem-node-a-expected-0').textContent,/should no longer be reported/);assert.doesNotMatch(issue.textContent,/Source-backed cause|synthesis passed/);
""")

    def test_saved_problems_are_visible_without_request_preview_and_focus_without_post(self):
        self.client(r"""
project.envelope.generation_batches={repair_sources:items.map(item=>({node_id:item.node_id,base_job_id:item.base_job_id,latest_job_id:item.expected_latest_job_id,source_workflow_run_id:item.source_workflow_run_id,repair_explanation:item.repair_explanation}))};
project.envelope.workflow_nodes=items.map(item=>({node_id:item.node_id,stage_id:'local_synthesis',repair_status:{outcome:'unchanged',reconsideration_required:true,candidate_id:item.base_job_id,run_id:item.source_workflow_run_id}}));
ui.plan=null;ui.renderGeneration(host);const before=JSON.stringify(project.envelope),panel=test(host,'repair-unresolved-problems');assert.ok(panel);assert.match(panel.textContent,/bank_a/);assert.match(panel.textContent,/fifo_data/);assert.equal(test(host,'generation-batch-plan'),null);assert.equal(test(host,'repair-problem-node-a-stale'),null);
assert.equal(ui.guidance().primary.label,'Inspect unresolved problems');ui.guidance().primary.action();assert.equal(panel.focusCount,1);assert.equal(panel.scrollCount,1);
project.envelope.llm.profile_revision_id='different-provider';ui.renderGeneration(host);assert.equal(test(host,'repair-problem-node-a-stale'),null,'Saved tool errors do not become stale when provider settings change');assert.equal(test(host,'repair-problem-node-a-analyze').disabled,false);
project.envelope.llm.profile_revision_id='profile-a';assert.equal(JSON.stringify(project.envelope),before);assert.equal(ui.plan,null);
""")

    def test_planless_reading_rejects_wrong_saved_candidate_run_or_revision(self):
        self.client(r"""
const source={node_id:items[0].node_id,base_job_id:items[0].base_job_id,latest_job_id:items[0].expected_latest_job_id,source_workflow_run_id:items[0].source_workflow_run_id,repair_explanation:items[0].repair_explanation};project.envelope.generation_batches={repair_sources:[source]};ui.plan=null;
for(const mutate of [()=>source.latest_job_id='earlier-rtl',()=>source.base_job_id='foreign-candidate',()=>source.source_workflow_run_id='earlier-s05']){
 Object.assign(source,{base_job_id:'candidate-0',latest_job_id:'candidate-0',source_workflow_run_id:'s05-0'});mutate();ui.renderGeneration(host);assert.equal(test(host,'repair-unresolved-problems'),null);
}
Object.assign(source,{base_job_id:'candidate-0',latest_job_id:'candidate-0',source_workflow_run_id:'s05-0'});source.repair_explanation.source.revision_id='earlier-revision';ui.renderGeneration(host);assert.match(test(host,'repair-problem-node-a-stale').textContent,/Earlier preview/);assert.equal(test(host,'repair-problem-node-a-analyze').disabled,true);assert.equal(ui.plan,null);
""")


if __name__ == '__main__':
    unittest.main()
