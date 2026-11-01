"""Structured repair guidance and explicit analysis actions; isolated ESM fixtures only."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_repair_prompt_console_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SETUP = r"""
const {GenerationBatchWorkspace}=await module('generation_batch.js');
const navigations=[],captured=[];
let responder=async()=>{throw Error('Unexpected request')};
const batchUI=new GenerationBatchWorkspace({...callbacks,request:async(...args)=>{requests.push(args);return responder(...args);},envelope:value=>{captured.push(value);project.envelope=value;batchUI.receive(value);},navigate:(...args)=>navigations.push(args)});
const source={node_id:'node-a',revision_id:'revision-a',candidate_id:'candidate-a',rtl_sha256:'rtl-a',run_id:'s05-a',run_sha256:'run-a'};
const candidate={id:'candidate-a',node_id:'node-a',freshness:'Current',review_status:'Accepted',execution_status:'Completed',validation_status:'Passed',finished_at:'saved',rtl_sha256:'rtl-a',rtl:'module qa_control; endmodule'};
const failed={id:'s05-a',stage_id:'local_synthesis',node_id:'node-a',candidate_id:'candidate-a',freshness:'Current',execution_status:'Completed',validation_status:'Failed',finished_at:'saved',checks:{executed:true,stderr:'candidate.v:26: ERROR: Invalid array access'}};
project.envelope.generation={submission_protocol_version:"node-submission-v1",jobs:[candidate],nodes:[{node_id:'node-a',latest_job_id:'candidate-a',accepted_job_id:'candidate-a'}]};
project.envelope.workflow_runs=[failed];project.envelope.workflow_nodes=[];
const guidance={version:'s05-repair-guidance-v1',source,original_requirements:{node:{behavior:'Reset retains stored bytes. <script>literal</script>'},connected_edges:[{id:'edge-original'}],shared_constraints:{reset_kind:'synchronous_high'},sha256:'requirements-a'},evidence:{diagnostics:['Invalid array access'],full_record_url:'/api/workflow/runs/s05-a'},changes:[{rule_id:'array-reset-retention',confidence:'confirmed',facts:['Whole array assigned a scalar.'],locations:[{line:26,text:'bank_a <= 0;'}],actions:['Remove array reset writes.'],preserve:['Retain stored bytes on reset.'],assumptions:[]},{rule_id:'uncertain-cause',confidence:'hypothesis',facts:[],actions:['Inspect dependent behavior.'],assumptions:['Tool diagnosis alone does not prove behavior.']}],recent_attempts:[{job_id:'candidate-a',base_job_id:'base-a',diff:'--- before\n+++ after\n@@ full saved diff @@',instruction:'Previous complete instruction',outcome:'same_diagnostic',run_id:'s05-a'}],repeat_status:{outcome:'same_diagnostic',repeated:true,reconsideration_required:true},analysis_required:false,guidance_sha256:'guidance-a'};
const item={node_id:'node-a',node_name:'Job control',operation:'repair',status:'Queued',instruction:'Full saved correction',base_job_id:'candidate-a',source_workflow_run_id:'s05-a',repair_guidance:guidance,expected_latest_job_id:'candidate-a'};
const plan={plan_id:'plan-a',revision_id:'revision-a',profile_revision_id:'profile-a',mode:'synthesis_repair',ready_to_start:true,profile:project.envelope.llm.profile,items:[item],first_request_context:{messages:[{role:'user',content:'Exact repair request'}],estimated_input_tokens:5000}};
batchUI.receive(project.envelope);batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();const host=new DOMNode();batchUI.renderGeneration(host);
"""


class GeneralizedRepairGuiTests(unittest.TestCase):
    def client(self, body, setup=True):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated ESM controller checks.')
        script = CLIENT + '\n(async()=>{\n' + (SETUP if setup else '') + body + '\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});'
        result = subprocess.run([node, '--experimental-vm-modules', '-e', script], cwd=PROJECT,
                                capture_output=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_guidance_preserves_original_sources_full_history_and_fact_hypothesis_boundary(self):
        self.client(r"""
const before=JSON.stringify(plan),panel=test(host,'generation-batch-guidance-node-a');
assert.ok(panel);assert.match(panel.textContent,/Same problem remains.*Reconsider/);
assert.match(panel.textContent,/Rule-backed facts/);assert.match(panel.textContent,/Hypothesis · requires tool checks/);
assert.match(test(panel,'generation-batch-guidance-node-a-requirements').textContent,/Reset retains stored bytes.*<script>literal<\/script>/);
assert.match(test(panel,'generation-batch-guidance-node-a-attempts').textContent,/Previous complete instruction/);
assert.match(test(panel,'generation-batch-guidance-node-a-attempts').textContent,/full saved diff/);
assert.match(panel.textContent,/Remove array reset writes/);assert.equal(JSON.stringify(plan),before);assert.equal(requests.length,0);
""")

    def test_saved_job_displays_its_frozen_guidance_instead_of_current_preview(self):
        self.client(r"""
const {GenerationWorkspace}=await module('generation.js'),single=new GenerationWorkspace(callbacks);single.artifactTab='request';
single.preview={batch_context:{repair_guidance:{...guidance,guidance_sha256:'unsent-new-guidance'}}};
const job={id:'saved-repair',operation:'repair',instruction:'Actual saved repair',execution_status:'Completed',context:{messages:[{role:'user',content:'Actual saved request'}],batch_context:{repair_guidance:guidance}}};
const before=JSON.stringify(job),rendered=single.artifactView(job);assert.match(test(rendered,'generation-saved-guidance').textContent,/guidance-a/);assert.doesNotMatch(rendered.textContent,/unsent-new-guidance/);assert.equal(JSON.stringify(job),before);assert.equal(requests.length,0);
""")

    def test_current_repeat_status_changes_next_action_but_stale_status_does_not(self):
        self.client(r"""
batchUI.plan=null;project.envelope.workflow_nodes=[{node_id:'node-a',repair_status:{...guidance.repeat_status,candidate_id:'candidate-a',run_id:'s05-a'}}];
batchUI.refresh();assert.match(test(host,'workflow-repair-outcome-node-a').textContent,/Same problem remains.*Reconsider/);
assert.equal(batchUI.guidance().title,'Reconsider the repeated repair');assert.equal(batchUI.repairOutcomeSummary().count,1);assert.equal(requests.length,0);
project.envelope.workflow_nodes[0].repair_status.candidate_id='old-candidate';batchUI.refresh();assert.equal(batchUI.repairOutcomeSummary().count,0);assert.equal(test(host,'workflow-repair-outcome-node-a'),null);
assert.equal(batchUI.guidance().title,'Repair the RTL that failed S05');
""")

    def test_unknown_analysis_requires_preview_then_start_then_reviewed_apply(self):
        self.client(r"""
guidance.analysis_required=true;plan.ready_to_start=false;plan.gate_reason='Concrete guidance required';batchUI.refresh();
assert.equal(test(host,'generation-batch-start').disabled,true);assert.equal(batchUI.guidance().primary.label,'Preview guidance analysis');
const preview={context_id:'analysis-context',messages:[{role:'user',content:'Exact unsent analysis request'}],ready_to_start:true,source,profile_revision_id:'profile-a',estimated_input_tokens:1234};
responder=async(route,body)=>{assert.equal(route,'repair-analysis/preview');assert.equal(body.run_id,'s05-a');return preview;};
await batchUI.previewAnalysis(item);assert.equal(requests.length,1);assert.equal(batchUI.analysisPreview,preview);assert.match(test(host,'repair-analysis-preview').textContent,/Unsent analysis/);assert.equal(test(host,'repair-analysis-start').disabled,false);assert.equal(candidate.rtl,'module qa_control; endmodule');
const running={id:'analysis-a',execution_status:'Running',source,context_id:preview.context_id,profile_revision_id:'profile-a',request_id:'isolated-display-qa'};
responder=async(route,body)=>{assert.equal(route,'repair-analysis/start');assert.equal(body.context_id,preview.context_id);return running;};
await batchUI.startAnalysis();assert.equal(requests.length,2);assert.equal(project.envelope.repair_analysis.active_job_id,'analysis-a');assert.match(batchUI.gate(),/active operation/);assert.equal(test(host,'repair-analysis-apply').disabled,true);
const completed={...running,execution_status:'Completed',proposal:{changes:[{cause:'Candidate syntax',actions:['Use module-scope typed declaration.'],preserve:['Original interface']}]},raw_content:'FULL_RAW_MODEL_PROPOSAL',messages:preview.messages};
responder=async(route)=>route==='project'?{...project.envelope,repair_analysis:{jobs:[completed],active_job_id:null}}:completed;
await batchUI.pollAnalysis();assert.equal(requests.length,4);assert.equal(test(host,'repair-analysis-proposal').textContent,JSON.stringify(completed.proposal,null,2));assert.equal(test(host,'repair-analysis-raw-answer').textContent,'FULL_RAW_MODEL_PROPOSAL');assert.equal(test(host,'repair-analysis-saved-message-0').textContent,'Exact unsent analysis request');assert.equal(test(host,'repair-analysis-apply').disabled,false);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.analysis_job_ids['node-a'],'analysis-a');return {...plan,ready_to_start:true,items:[{...item,repair_guidance:{...guidance,analysis_required:false}}]};};
await batchUI.applyAnalysis(batchUI.selectedAnalysis());assert.equal(requests.length,5);assert.equal(test(host,'generation-batch-start').disabled,false);assert.equal(candidate.rtl,'module qa_control; endmodule');assert.equal(requests.some(([route])=>route==='generation/batches/start'),false);
""")

    def test_analysis_lost_response_reconnects_without_resubmission(self):
        self.client(r"""
const preview={context_id:'analysis-context',ready_to_start:true,source,profile_revision_id:'profile-a',messages:[]};batchUI.analysisPreview=preview;
responder=async()=>{throw Error('Response lost')};await batchUI.startAnalysis();assert.equal(requests.length,1);assert.equal(batchUI.analysisStartUncertain,true);await batchUI.startAnalysis();assert.equal(requests.length,1);assert.ok(test(host,'repair-analysis-reconnect'));
const saved={id:'analysis-recovered',execution_status:'Running',source,context_id:preview.context_id,request_id:'isolated-display-qa'};
const oldSameContext={...saved,id:'old-analysis-same-context',request_id:'different-request',execution_status:'Completed'};
responder=async route=>{assert.equal(route,'project');return {...project.envelope,repair_analysis:{jobs:[oldSameContext,saved],active_job_id:saved.id}};};
await batchUI.pollAnalysis(true);assert.equal(requests.length,2);assert.equal(batchUI.analysisStartUncertain,false);assert.equal(batchUI.analysisPreview,null);assert.equal(batchUI.selectedAnalysis().id,saved.id);assert.equal(candidate.rtl,'module qa_control; endmodule');
""")

    def test_analysis_capacity_preview_has_settings_rebuild_and_no_send_path(self):
        self.client(r"""
const preview={context_id:'oversized-analysis',messages:[{role:'user',content:'FULL_CURRENT_SOURCE'}],ready_to_start:false,source,profile_revision_id:'profile-a',estimated_input_tokens:15000,parameters:{max_tokens:1800},profile:{context_window:16384},context_budget:{scope:'packed_request',total_estimated_tokens:16800,maximum_output_tokens:1384},gate_reason:'Analysis input 15,000 + output 1,800 exceeds context 16,384; maximum output 1,384.',prompt_projection:'complete_current_source_history_refs_v2',source_evidence:{guidance:'FULL_ORIGINAL_HISTORY'}};
responder=async(route,body)=>{assert.equal(route,'repair-analysis/preview');assert.equal(body.run_id,'s05-a');return preview;};
await batchUI.previewAnalysis(item);assert.equal(requests.length,1);assert.equal(test(host,'repair-analysis-start').disabled,true);
assert.match(test(host,'repair-analysis-budget').textContent,/15,000.*1,800.*16,800.*16,384.*1,384/);
assert.match(test(host,'repair-analysis-source-evidence').textContent,/FULL_ORIGINAL_HISTORY/);
assert.equal(batchUI.guidance().primary.label,'Open LLM settings');batchUI.guidance().primary.action();assert.deepEqual(navigations.at(-1),['global_settings']);
await batchUI.startAnalysis();assert.equal(requests.length,1);assert.equal(candidate.rtl,'module qa_control; endmodule');
project.envelope.llm.profile_revision_id='profile-output-reduced';batchUI.refresh();assert.equal(batchUI.guidance().primary.label,'Rebuild analysis preview');
const fresh={...preview,context_id:'fresh-analysis',ready_to_start:true,profile_revision_id:'profile-output-reduced',parameters:{max_tokens:1000},context_budget:{...preview.context_budget,total_estimated_tokens:16000},gate_reason:null};
responder=async(route,body)=>{assert.equal(route,'repair-analysis/preview');return fresh;};await batchUI.rebuildAnalysisPreview();
assert.equal(requests.length,2);assert.equal(batchUI.analysisPreview,fresh);assert.equal(test(host,'repair-analysis-start').disabled,false);assert.equal(batchUI.guidance().primary.label,'Start guidance analysis');assert.equal(requests.some(([route])=>route==='repair-analysis/start'),false);
""")

    def test_netlist_repair_previews_all_failed_nodes_with_distinct_s06_evidence(self):
        self.client(r"""
project.envelope.workflow_runs=[];batchUI.plan=null;
const evidence={projection_version:'s06-netlist-repair-evidence-v1',source:{node_id:'node-a',candidate_id:'candidate-a',source_workflow_run_id:'s06-a',source_synthesis_run_id:'s05-passed-a',netlist_sha256:'exact-netlist'},first_failure:'FAIL cycle 2 result_valid expected 0 actual 1',frozen_plan:{sha256:'exact-s06-plan'}};
project.envelope.generation_batches={netlist_repair_sources:[{node_id:'node-a',latest_job_id:'candidate-a',base_job_id:'candidate-a',source_workflow_run_id:'s06-a',netlist_repair_evidence:evidence}]};batchUI.receive(project.envelope);batchUI.refresh();
assert.ok(test(host,'generation-netlist-recovery'));assert.match(test(host,'generation-netlist-recovery').textContent,/FAIL cycle 2/);assert.equal(batchUI.guidance().primary.label,'Preview repairs for 1 failed netlists');
const s06Plan={...plan,mode:'netlist_repair',ready_to_start:true,items:[{...item,repair_guidance:null,netlist_repair_evidence:evidence,source_workflow_run_id:'s06-a'}]};
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'netlist_repair');assert.deepEqual(body.node_ids,['node-a']);assert.equal(body.analysis_job_ids,undefined);return s06Plan;};
await batchUI.prepare('netlist_repair');assert.equal(requests.length,1);assert.deepEqual(navigations.at(-1),['local_rtl_generation']);assert.match(test(host,'generation-batch-plan').textContent,/S06 netlist repair queue/);assert.match(test(host,'netlist-repair-evidence-node-a').textContent,/exact-s06-plan/);assert.equal(test(host,'generation-batch-start').textContent,'Start repair batch');assert.equal(batchUI.guidance().primary.label,'Start repair batch');assert.equal(test(host,'generation-batch-analyze-node-a'),null);assert.equal(requests.some(([route])=>route==='generation/batches/start'),false);
project.envelope.generation.nodes[0].latest_job_id='new-candidate';batchUI.refresh();assert.equal(batchUI.failedNetlists().length,0);assert.equal(test(host,'generation-batch-start').disabled,true);
""")

    def test_s06_analysis_apply_keeps_netlist_mode_and_does_not_send_rtl(self):
        self.client(r"""
project.envelope.workflow_runs=[];batchUI.plan=null;
const s06Source={...source,run_id:'s06-a',stage_id:'local_netlist_simulation',source_synthesis_run_id:'s05-passed-a',netlist_sha256:'exact-netlist',verification_plan_sha256:'exact-plan'};
const evidence={projection_version:'s06-netlist-repair-evidence-v1',first_failure:'FAIL actual saved check',frozen_plan:{sha256:'exact-plan'}};
const savedSource={node_id:'node-a',base_job_id:'candidate-a',latest_job_id:'candidate-a',source_workflow_run_id:'s06-a',netlist_repair_evidence:evidence};
project.envelope.generation_batches={netlist_repair_sources:[savedSource]};batchUI.receive(project.envelope);batchUI.refresh();assert.ok(test(host,'netlist-repair-analyze-node-a'));
const s06Item={node_id:'node-a',base_job_id:'candidate-a',expected_latest_job_id:'candidate-a',source_workflow_run_id:'s06-a',netlist_repair_evidence:evidence};
const preview={context_id:'s06-analysis-preview',source:s06Source,profile_revision_id:'profile-a',ready_to_start:true,messages:[{role:'user',content:'FULL_S06_REQUEST'}],estimated_input_tokens:1000};
responder=async(route,body)=>{assert.equal(route,'repair-analysis/preview');assert.equal(body.run_id,'s06-a');return preview;};await batchUI.previewAnalysis(s06Item);assert.equal(requests.length,1);assert.match(test(host,'repair-analysis-preview').textContent,/S06 s06-a/);assert.equal(test(host,'repair-analysis-start').disabled,false);
const completed={id:'s06-analysis-completed',source:s06Source,profile_revision_id:'profile-a',execution_status:'Completed',proposal:{changes:[{cause:'Saved failure hypothesis'}]}};batchUI.analysisPreview=null;batchUI.saveAnalysis(completed);batchUI.refresh();assert.equal(test(host,'repair-analysis-apply').disabled,false);
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'netlist_repair');assert.equal(body.analysis_job_ids['node-a'],completed.id);return {...plan,mode:'netlist_repair',items:[{...item,repair_guidance:{...guidance,version:'s06-repair-guidance-v1',source:s06Source,analysis_required:false,analysis_reviewed:true},source_workflow_run_id:'s06-a',netlist_repair_evidence:evidence}]};};
await batchUI.applyAnalysis(completed);assert.equal(requests.length,2);assert.equal(batchUI.plan.mode,'netlist_repair');assert.equal(test(host,'generation-batch-start').textContent,'Start repair batch');assert.equal(requests.some(([route])=>route==='generation/batches/start'),false);
project.envelope.generation_batches.netlist_repair_sources[0].source_workflow_run_id='new-s06';batchUI.refresh();assert.equal(test(host,'repair-analysis-apply').disabled,true);
""")

    def test_explicit_new_analysis_preview_takes_focus_over_old_completed_result(self):
        self.client(r"""
const old={id:'older-completed-analysis',context_id:'old-context',execution_status:'Completed',source,profile_revision_id:'profile-a',proposal:{changes:[{cause:'Old hypothesis'}]},raw_content:'PRESERVED_OLD_ANSWER'};
batchUI.saveAnalysis(old);batchUI.publishAnalysis();batchUI.refresh();assert.ok(test(host,'repair-analysis-result'));const original=JSON.stringify(old);
const preview={context_id:'new-explicit-analysis',messages:[{role:'user',content:'NEW_EXACT_REQUEST'}],ready_to_start:true,source,profile_revision_id:'profile-a',estimated_input_tokens:1000};
responder=async(route)=>{assert.equal(route,'repair-analysis/preview');return preview;};await batchUI.previewAnalysis(item);
assert.equal(batchUI.analysisPreview,preview);assert.equal(batchUI.analysisJobId,null);assert.equal(test(host,'repair-analysis-result'),null);assert.equal(test(host,'repair-analysis-start').disabled,false);assert.equal(batchUI.guidance().primary.label,'Start guidance analysis');assert.ok(test(host,'repair-analysis-panel').focusCount>=1);assert.ok(test(host,'repair-analysis-history-older-completed-analysis'));
batchUI.saveAnalysis({...old});batchUI.receive({...project.envelope,repair_analysis:{jobs:[old],active_job_id:null}});assert.equal(batchUI.analysisJobId,null);assert.equal(test(host,'repair-analysis-result'),null);assert.equal(test(host,'repair-analysis-start').disabled,false);assert.equal(JSON.stringify(old),original);
batchUI.analysisPreview=null;batchUI.refresh();assert.ok(test(host,'repair-analysis-history-older-completed-analysis'));batchUI.analysisPreview=preview;batchUI.refresh();
const running={id:'new-analysis-running',context_id:preview.context_id,source,profile_revision_id:'profile-a',execution_status:'Running'};responder=async(route,body)=>{assert.equal(route,'repair-analysis/start');assert.equal(body.context_id,preview.context_id);return running;};await batchUI.startAnalysis();assert.equal(requests.length,2);assert.equal(batchUI.selectedAnalysis().id,running.id);assert.equal(batchUI.analysisPreview,null);assert.equal(batchUI.analysisJobs.find(job=>job.id===old.id).raw_content,'PRESERVED_OLD_ANSWER');
""")

    def test_edit_then_rebuild_retains_the_same_explicit_netlist_node_scope(self):
        self.client(r"""
project.envelope.workflow_runs=[];project.design.nodes.push({id:'node-b',name:'Other failed node',module_name:'qa_other'});project.envelope.generation.nodes.push({node_id:'node-b',latest_job_id:'candidate-b',accepted_job_id:'candidate-b'});project.envelope.generation.jobs.push({...candidate,id:'candidate-b',node_id:'node-b'});
const evidence={projection_version:'s06-netlist-repair-evidence-v2',first_failure:'HULLCIRQ_FAIL actual saved check',frozen_plan:{sha256:'exact-plan'}};
project.envelope.generation_batches={netlist_repair_sources:['a','b'].map(suffix=>({node_id:`node-${suffix}`,base_job_id:`candidate-${suffix}`,latest_job_id:`candidate-${suffix}`,source_workflow_run_id:`s06-${suffix}`,netlist_repair_evidence:evidence}))};batchUI.receive(project.envelope);batchUI.plan=null;
const blocked={...plan,plan_id:'blocked-s06-preview',mode:'netlist_repair',ready_to_start:false,gate_reason:'Context budget exceeded',items:[{...item,status:'Blocked',reason:'Input 14,510 plus output 2,000 exceeds context 16,384.',error:{code:'context_budget'},repair_guidance:null,netlist_repair_evidence:evidence,source_workflow_run_id:'s06-a'}]};
responder=async()=>blocked;batchUI.instruction='Original long manual instruction';await batchUI.prepare('netlist_repair',['node-a'],false);assert.equal(requests.length,1);const frozen=JSON.stringify(blocked),oldButton=test(host,'generation-batch-rebuild');assert.ok(oldButton);
const editor=test(host,'netlist-batch-repair-instruction');editor.value='Short corrected instruction';for(const handler of editor.listeners.input||[])handler({target:editor});assert.equal(batchUI.plan,null);assert.equal(batchUI.guidance().primary.label,'Rebuild repair preview');assert.equal(test(host,'generation-batch-start').disabled,true);
const rebuilt={...blocked,plan_id:'short-s06-preview',ready_to_start:true,gate_reason:null,items:[{...blocked.items[0],status:'Queued',reason:null,error:null,instruction:'Short corrected instruction'}]};
responder=async(route,body)=>{assert.equal(route,'generation/batches/preview');assert.equal(body.mode,'netlist_repair');assert.deepEqual([...body.node_ids],['node-a']);assert.equal(body.instruction,'Short corrected instruction');return rebuilt;};await oldButton.listeners.click[0]({target:oldButton});assert.equal(requests.length,2);assert.equal(batchUI.plan,rebuilt);assert.equal(test(host,'generation-batch-start').disabled,false);assert.equal(JSON.stringify(blocked),frozen);assert.equal(requests.some(([route])=>route==='generation/batches/start'),false);
batchUI.plan=null;project.envelope.revision.id='different-revision';await batchUI.rebuildPlan();assert.equal(requests.length,2);
project.envelope.revision.id='revision-a';project.envelope.workspace_identity.session_id='other-session';batchUI.receive(project.envelope);assert.equal(batchUI.previewSelection,null);await batchUI.rebuildPlan();assert.equal(requests.length,2);
""")

    def test_completed_netlist_repair_continues_exact_new_candidate_to_s05_before_other_s06_failures(self):
        self.client(r"""
const child={...candidate,id:'new-repaired-candidate',rtl:'module repaired; endmodule'};project.envelope.generation.jobs.push(child);project.envelope.generation.nodes[0].latest_job_id=child.id;project.envelope.generation.nodes[0].accepted_job_id=child.id;
project.design.nodes.push({id:'node-b',name:'Other failed node'});project.envelope.generation.nodes.push({node_id:'node-b',latest_job_id:'candidate-b',accepted_job_id:'candidate-b'});project.envelope.generation.jobs.push({...candidate,id:'candidate-b',node_id:'node-b'});
project.envelope.workflow_runs=[{...failed,id:'old-passed-synthesis',candidate_id:'candidate-a',validation_status:'Passed',review_status:'Accepted',netlist:'OLD_CANDIDATE_NETLIST'}];
const completedBatch={id:'finished-netlist-repair',mode:'netlist_repair',source_current:true,execution_status:'Completed',validation_status:'Passed',items:[{node_id:'node-a',operation:'repair',base_job_id:'candidate-a',job_id:child.id,status:'Passed'}]};
project.envelope.generation_batches={batches:[completedBatch],latest_batch_id:completedBatch.id,netlist_repair_sources:[{node_id:'node-b',latest_job_id:'candidate-b',base_job_id:'candidate-b',source_workflow_run_id:'s06-b',netlist_repair_evidence:{first_failure:'HULLCIRQ_FAIL other node'}}]};batchUI.plan=null;batchUI.receive(project.envelope);
assert.equal(batchUI.synthesisAccepted('node-a'),false);assert.equal(batchUI.failedNetlists().length,1);assert.equal(batchUI.guidance().title,'Continue the repaired RTL to S05');batchUI.guidance().primary.action();assert.deepEqual(navigations.at(-1),['local_synthesis','node-a']);
batchUI.plan={...plan,mode:'netlist_repair',items:[{node_id:'node-b',expected_latest_job_id:'candidate-b',operation:'repair',status:'Queued'}]};batchUI.planSource=batchUI.sourceIdentity();assert.equal(batchUI.guidance().primary.label,'Start repair batch');batchUI.plan=null;
project.envelope.workflow_runs.push({...failed,id:'exact-new-candidate-synthesis',candidate_id:child.id,validation_status:'Passed',review_status:'Accepted',netlist:'EXACT_NEW_CANDIDATE_NETLIST'});batchUI.refresh();assert.equal(batchUI.synthesisAccepted('node-a'),true);assert.equal(batchUI.guidance().title,'Repair the RTL that failed S06');
""")

    def test_remaining_netlist_guidance_scope_is_its_actual_nodes_not_the_last_single_node_batch(self):
        self.client(r"""
for(const suffix of ['b','c']){project.design.nodes.push({id:`node-${suffix}`,name:`Node ${suffix}`});project.envelope.generation.nodes.push({node_id:`node-${suffix}`,latest_job_id:`candidate-${suffix}`,accepted_job_id:`candidate-${suffix}`});project.envelope.generation.jobs.push({...candidate,id:`candidate-${suffix}`,node_id:`node-${suffix}`});}
project.envelope.workflow_runs=[{...failed,id:'exact-current-s05',validation_status:'Passed',review_status:'Accepted',netlist:'EXACT_CURRENT_NETLIST'}];
const done={id:'last-single-node-batch',mode:'netlist_repair',source_current:true,execution_status:'Completed',validation_status:'Passed',items:[{node_id:'node-a',node_name:'Job control',job_id:'candidate-a',status:'Passed'}]};
project.envelope.generation_batches={batches:[done],latest_batch_id:done.id,netlist_repair_sources:['a','b','c'].map(suffix=>({node_id:`node-${suffix}`,base_job_id:`candidate-${suffix}`,latest_job_id:`candidate-${suffix}`,source_workflow_run_id:`s06-${suffix}`}))};batchUI.plan=null;batchUI.receive(project.envelope);
assert.equal(batchUI.guidance().title,'Repair the RTL that failed S06');assert.equal(batchUI.guidance().scope,'Request queue: 3 nodes');
project.envelope.workflow_runs=[];batchUI.refresh();assert.equal(batchUI.guidance().title,'Continue the repaired RTL to S05');assert.equal(batchUI.guidance().scope,'Request queue: Job control');
batchUI.plan={...plan,mode:'netlist_repair',items:[{node_id:'node-b',node_name:'Node b',expected_latest_job_id:'candidate-b',operation:'repair',status:'Queued'}]};batchUI.planSource=batchUI.sourceIdentity();assert.equal(batchUI.guidance().primary.label,'Start repair batch');assert.equal(batchUI.guidance().scope,'Request queue: Node b');
""")

    def test_edited_multi_node_preview_scope_uses_the_remembered_selection(self):
        self.client(r"""
project.envelope.workflow_runs=[];for(const suffix of ['b','c']){project.design.nodes.push({id:`node-${suffix}`,name:`Node ${suffix}`});project.envelope.generation.nodes.push({node_id:`node-${suffix}`,latest_job_id:`candidate-${suffix}`,accepted_job_id:`candidate-${suffix}`});project.envelope.generation.jobs.push({...candidate,id:`candidate-${suffix}`,node_id:`node-${suffix}`});}
const evidence={projection_version:'s06-netlist-repair-evidence-v2',first_failure:'HULLCIRQ_FAIL recorded',frozen_plan:{sha256:'exact-plan'}};
const done={id:'earlier-one-node-batch',mode:'netlist_repair',source_current:true,execution_status:'Completed',validation_status:'Passed',items:[{node_id:'node-a',node_name:'Job control',job_id:'candidate-a',status:'Passed'}]};project.envelope.generation_batches={batches:[done],latest_batch_id:done.id,netlist_repair_sources:['a','b','c'].map(suffix=>({node_id:`node-${suffix}`,base_job_id:`candidate-${suffix}`,latest_job_id:`candidate-${suffix}`,source_workflow_run_id:`s06-${suffix}`,netlist_repair_evidence:evidence}))};batchUI.plan=null;batchUI.receive(project.envelope);
const allPlan={...plan,mode:'netlist_repair',items:['a','b','c'].map(suffix=>({node_id:`node-${suffix}`,node_name:suffix==='a'?'Job control':`Node ${suffix}`,expected_latest_job_id:`candidate-${suffix}`,operation:'repair',status:'Queued'}))};responder=async()=>allPlan;await batchUI.prepare('netlist_repair',['node-a','node-b','node-c'],false);
const editor=test(host,'netlist-batch-repair-instruction');editor.value='Revised shared correction';for(const handler of editor.listeners.input||[])handler({target:editor});assert.equal(batchUI.plan,null);assert.equal(batchUI.guidance().title,'Rebuild the edited request preview');assert.equal(batchUI.guidance().scope,'Request queue: 3 nodes');assert.match(batchUI.guidance().summary,/same 3 selected/);assert.equal(requests.length,1);
""")

    def test_stale_source_cannot_be_rebuilt_using_a_different_failed_candidate(self):
        self.client(r"""
batchUI.analysisPreview={context_id:'earlier-analysis',source,profile_revision_id:'profile-a',ready_to_start:false,messages:[]};project.envelope.generation.nodes[0].accepted_job_id='another-candidate';batchUI.refresh();
assert.equal(batchUI.guidance().primary.label,'Discard stale analysis preview');assert.equal(test(host,'repair-analysis-rebuild').disabled,true);await batchUI.rebuildAnalysisPreview();assert.equal(requests.length,0);
""")

    def test_analysis_stale_source_profile_readonly_and_active_gates_preserve_rtl(self):
        self.client(r"""
const completed={id:'analysis-completed',execution_status:'Completed',proposal:{changes:[]},source,profile_revision_id:'profile-a'};batchUI.saveAnalysis(completed);batchUI.refresh();
for(const change of [()=>project.envelope.workspace_identity.read_only=true,()=>project.dirty=true,()=>project.envelope.llm.profile_revision_id='profile-new',()=>project.envelope.generation.nodes[0].latest_job_id='new-candidate']) {
 project.envelope.workspace_identity.read_only=false;project.dirty=false;project.envelope.llm.profile_revision_id='profile-a';project.envelope.generation.nodes[0].latest_job_id='candidate-a';change();batchUI.refresh();assert.equal(test(host,'repair-analysis-apply').disabled,true);await batchUI.applyAnalysis(completed);assert.equal(requests.length,0);
}
project.envelope.workspace_identity.session_id='session-new';batchUI.receive(project.envelope);assert.equal(batchUI.analysisJobs.length,0);assert.equal(batchUI.analysisPreview,null);assert.equal(Object.keys(batchUI.analysisJobIds).length,0);assert.equal(candidate.rtl,'module qa_control; endmodule');
""")

    def test_late_analysis_preview_does_not_cross_project_session(self):
        self.client(r"""
let resolve;responder=()=>new Promise(done=>resolve=done);const pending=batchUI.previewAnalysis(item);project.envelope.workspace_identity.session_id='other-session';batchUI.receive(project.envelope);resolve({context_id:'late',source,ready_to_start:true});await pending;assert.equal(batchUI.analysisPreview,null);assert.equal(batchUI.busy,false);assert.equal(captured.length,0);assert.equal(requests.length,1);
""")

    def test_analysis_active_blocks_generation_synthesis_and_repair_routes(self):
        self.client(r"""
const {GenerationWorkspace}=await module('generation.js'),{LocalWorkflow}=await module('workflow.js');project.envelope.repair_analysis={active_job_id:'analysis-active'};
const single=new GenerationWorkspace(callbacks),local=new LocalWorkflow(callbacks);single.generation={submission_protocol_version:"node-submission-v1",...project.envelope.generation,implemented:true};local.nodeId='node-a';project.stage='local_synthesis';
assert.match(single.generationGate(),/guidance analysis is active/);assert.match(local.batchGate(),/guidance analysis is active/);assert.equal(local.blocker().kind,'active_operation');assert.match(local.repairGate(),/guidance analysis is active/);assert.equal(requests.length,0);
""")

    def test_s05_outcome_view_uses_matching_run_and_pass_still_requires_s06(self):
        self.client(r"""
const {LocalWorkflow}=await module('workflow.js');project.stage='local_synthesis';const passed={...failed,validation_status:'Passed',review_status:'Accepted',netlist:'actual netlist'};project.envelope.workflow_runs=[passed];project.envelope.workflow_nodes=[{node_id:'node-a',repair_status:{outcome:'passed',candidate_id:'candidate-a',run_id:'s05-a'}}];
const local=new LocalWorkflow(callbacks);local.nodeId='node-a';local.runs=[passed];local.runId='s05-a';const localHost=new DOMNode(),result=new DOMNode();result.setAttribute('data-testid','workflow-result');localHost.append(result);local.host=localHost;local.renderResult();assert.match(test(localHost,'workflow-repair-outcome').textContent,/Synthesis passed.*S06/);assert.match(test(localHost,'workflow-repair-outcome').textContent,/check circuit behavior/);
project.envelope.workflow_nodes[0].repair_status.run_id='earlier-run';local.renderResult();assert.equal(test(localHost,'workflow-repair-outcome'),null);assert.equal(requests.length,0);
""")

    def test_common_next_step_prioritizes_reconsideration_without_new_route(self):
        self.client(r"""
const {resolveStageGuidance}=await module('flow_guidance.js');const result=resolveStageGuidance({stage:'local_synthesis',synthesisRepairCount:1,synthesisRepairGuidance:{count:1,summary:'Job control: RTL unchanged'},synthesisSummary:{accepted:0,total:1}});
assert.equal(result.decisionId,'s05_bulk_repair');assert.equal(result.title,'Reconsider the repeated repair');assert.equal(result.primary.testId,'workflow-batch-repair-all');assert.match(result.summary,/RTL unchanged/);assert.equal(requests.length,0);
""")

    def test_repeated_plan_requires_revised_instruction_and_does_not_hide_budget_error(self):
        self.client(r"""
guidance.same_plan_repeated=true;plan.ready_to_start=false;plan.gate_reason='The same repair plan left the problem unresolved';item.status='Blocked';batchUI.refresh();
assert.equal(batchUI.guidance().primary.label,'Inspect unresolved problems');assert.equal(test(host,'generation-batch-start').disabled,true);await batchUI.start();assert.equal(requests.length,0);batchUI.guidance().primary.action();assert.equal(test(host,'repair-unresolved-problems').focusCount,1);batchUI.guidance().secondary.action();assert.equal(test(host,'workflow-batch-repair-instruction').focusCount,1);
guidance.additional_instruction='A revised explicit correction';plan.gate_reason='Estimated input plus output exceeds context window';batchUI.refresh();assert.equal(batchUI.guidance().title,'Input required · request not sent');assert.equal(batchUI.guidance().secondary.label,'Read request instructions');assert.equal(requests.length,0);
""")

    def test_diagnostics_changed_does_not_claim_previous_errors_are_all_cleared(self):
        self.client(r"""
const {repairOutcomeLabel}=await module('prompt_view.js');assert.equal(repairOutcomeLabel('new_diagnostic'),'Diagnostics changed · inspect remaining problems');assert.doesNotMatch(repairOutcomeLabel('new_diagnostic'),/cleared|resolved/);assert.equal(requests.length,0);
""")

    def test_cancel_analysis_preserves_saved_proposal_history_and_unblocks_after_saved_result(self):
        self.client(r"""
const running={id:'analysis-running',execution_status:'Running',source,context_id:'context-running'};batchUI.saveAnalysis(running);batchUI.publishAnalysis();batchUI.refresh();assert.ok(test(host,'repair-analysis-cancel'));assert.equal(test(host,'repair-analysis-apply').disabled,true);
responder=async(route,body)=>{assert.equal(route,'repair-analysis/cancel');assert.equal(body.job_id,running.id);return {...running,execution_status:'Cancelled',raw_content:'Partial analysis preserved',error:{code:'cancelled',message:'No guidance adopted'}};};
await batchUI.cancelAnalysis(running);assert.equal(requests.length,1);assert.equal(project.envelope.repair_analysis.active_job_id,null);assert.equal(batchUI.selectedAnalysis().execution_status,'Cancelled');assert.equal(test(host,'repair-analysis-raw-answer').textContent,'Partial analysis preserved');assert.equal(test(host,'repair-analysis-apply').disabled,true);assert.equal(candidate.rtl,'module qa_control; endmodule');assert.equal(batchUI.analysisJobs.length,1);
""")

    def test_analysis_poll_failure_recovers_readonly_without_resending_model_request(self):
        self.client(r"""
const running={id:'analysis-running',execution_status:'Running',source,context_id:'context-running'};batchUI.saveAnalysis(running);batchUI.publishAnalysis();responder=async()=>{throw Error('Disconnected')};await batchUI.pollAnalysis();assert.match(batchUI.analysisError,/not resent/);assert.ok(test(host,'repair-analysis-reconnect'));assert.equal(requests.length,1);
const completed={...running,execution_status:'Completed',proposal:{changes:[{actions:['Actual hypothesis']}]}};responder=async route=>route==='project'?{...project.envelope,repair_analysis:{jobs:[completed],active_job_id:null}}:completed;await batchUI.pollAnalysis(true);assert.equal(requests.length,3);assert.equal(batchUI.analysisError,null);assert.equal(batchUI.guidance().primary.label,'Review proposed guidance');assert.equal(requests.some(([route])=>route==='repair-analysis/start'),false);assert.equal(candidate.rtl,'module qa_control; endmodule');
""")


if __name__ == '__main__':
    unittest.main()
