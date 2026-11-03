"""Immediate stage display and read-only reconnection. No HTTP, LLM, EDA or stores."""
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const sandbox={};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('src/gui/execution_state.js','utf8').replace(/export /g,'')+'\nthis.Tracker=ExecutionStateTracker;this.action=executionAction;this.stages=STAGE_ORDER;',sandbox);
const {Tracker,action,stages}=sandbox;const storage=new Map();let writes=0;
const options={readStorage:key=>storage.get(key),writeStorage:(key,value)=>{writes++;storage.set(key,JSON.stringify(value));}};
const tracker=new Tracker(options);tracker.setScope('workspace/project/system/semantic-a');
const pass=(id,stage,extra={})=>({id,stage_id:stage,execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',...extra});
const start=stage=>tracker.begin({kind:'execute',stageId:stage});
const stage='local_synthesis',next='local_netlist_simulation';
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
"""


class ExecutionStateTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is needed for isolated execution display checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body +
                                 "\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=PROJECT, capture_output=True, text=True,
                                encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_actual_execution_routes_cover_all_fourteen_stages(self):
        self.client(r"""
const routes=[['validate',{stage_id:stages[0]}],['validate',{stage_id:stages[1]}],['validate',{stage_id:stages[2]}],
 ['generation/start',{node_id:'n'}],['workflow/start',{stage_id:stages[4]}],['workflow/start',{stage_id:stages[5]}],
 ['implementation-specs/start',{}],['global-generation/start',{}],['global-workflow/runs',{stage:stages[8]}],
 ['global-workflow/runs',{stage:stages[9]}],['physical-workflow/runs',{}],['drc-workflow/runs',{}],
 ['lvs-workflow/runs',{}],['postlayout-workflow/runs',{}]];
assert.equal(routes.length,14);routes.forEach(([path,body],i)=>assert.equal(action(path,body).stageId,stages[i]));
assert.equal(action('/api/workflow/batches/start/',{}).stageId,stage);
assert.equal(action('workflow/batches/start',{stage_id:next}).stageId,next);
assert.equal(action('generation/batches/start',{}).stageId,stages[3]);
assert.equal(action('physical-workflow/runs/id/revalidate',{}).stageId,'layout');
""")

    def test_previews_reads_settings_analysis_and_cancel_do_not_invalidate(self):
        self.client(r"""
for(const route of ['project','bootstrap','save','import','llm/profile','llm/probe','workspace/local-runtime/start',
 'generation/context','generation/review','generation/cancel','generation/batches/preview','generation/batches/id/cancel',
 'workflow/cancel','workflow/review','workflow/batches/id/cancel','repair-analysis/start','repair-analysis/preview',
 'global-generation/context','drc-workflow/runs/id/cancel','postlayout-workflow/runs/id/review'])assert.equal(action(route,{}),null,route);
assert.equal(action('generation/start'),null);assert.equal(action('validate',{stage_id:'made-up'}),null);
assert.equal(writes,0);assert.equal(tracker.overlay(stage),null);
""")

    def test_click_is_running_before_deferred_response_and_all_later_stages_not_run(self):
        self.client(r"""
const saved={runs:stages.map((id,i)=>pass('old-'+i,id))};const before=JSON.stringify(saved);tracker.receive(saved);
const pending=deferred();const token=start(stages[0]);
const completion=pending.promise.then(result=>tracker.success(token,result));
assert.equal(tracker.overlay(stages[0]).status,'Running');
for(const id of stages.slice(1))assert.equal(tracker.overlay(id).status,'Not run',id);
assert.equal(JSON.stringify(saved),before);pending.resolve({runs:[pass('new',stages[0])]});await completion;
assert.equal(tracker.overlay(stages[0]).status,'Complete');for(const id of stages.slice(1))assert.equal(tracker.overlay(id).status,'Not run');
""")

    def test_each_stage_click_invalidates_only_its_later_stages(self):
        self.client(r"""
for(let index=0;index<stages.length;index++) {
 tracker.reset();tracker.receive({runs:stages.map((id,i)=>pass('baseline-'+i,id))});
 const token=start(stages[index]);assert.equal(tracker.overlay(stages[index]).status,'Running');
 for(let before=0;before<index;before++)assert.equal(tracker.overlay(stages[before]),null);
 for(let later=index+1;later<stages.length;later++)assert.equal(tracker.overlay(stages[later]).status,'Not run');
 tracker.success(token,{runs:[pass('execution-'+index,stages[index])]});assert.equal(tracker.overlay(stages[index]).status,'Complete');
}
""")

    def test_old_poll_cannot_restore_invalidated_downstream_even_if_old_status_changes(self):
        self.client(r"""
tracker.receive({runs:[pass('old',next)]});start(stage);
tracker.receive({runs:[pass('old',next,{execution_status:'Running'})]});assert.equal(tracker.overlay(next).status,'Not run');
tracker.receive({runs:[pass('old',next),pass('late-earlier-request',next)]});assert.equal(tracker.overlay(next).status,'Not run');
const token=start(next);tracker.success(token,{runs:[pass('new-explicit',next)]});assert.equal(tracker.overlay(next).status,'Complete');
assert.equal(tracker.overlay(stage).status,'Running');
""")

    def test_manual_review_and_automatic_adoption_are_distinct(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{runs:[pass('new',stage,{review_status:'Awaiting Review'})]});
assert.equal(tracker.overlay(stage).status,'Review required');assert.equal(tracker.overlay(stage).review_status,'Awaiting Review');
tracker.receive({runs:[pass('new',stage)]});assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_accepted_own_result_becomes_failed_when_review_requests_changes(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{workflow_runs:[pass('own',stage)]});
for(const decision of ['Changes Requested','Request Changes','Returned','Rejected']) {
 const envelope={workflow_runs:[pass('own',stage,{review_status:decision})],workflow_reviews:[{run_id:'own',decision:'return_to_stage',note:'Fix reset timing before another synthesis.'}]};
 tracker.receive(envelope);assert.equal(tracker.overlay(stage).status,'Failed');
 assert.equal(tracker.overlay(stage).review_status,decision);assert.equal(tracker.overlay(stage).validation_status,'Passed');
 assert.match(tracker.overlay(stage).detail,/Fix reset timing/);assert.equal(tracker.overlay(stage).reconnectRequired,false);
}
""")

    def test_terminal_own_result_becoming_stale_is_not_run_with_evidence_preserved(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{runs:[pass('own',stage)]});
const stale={runs:[pass('own',stage,{freshness:'Stale'})]},before=JSON.stringify(stale);tracker.receive(stale);
assert.equal(tracker.overlay(stage).status,'Not run');assert.equal(tracker.overlay(stage).invalidated,true);
assert.equal(tracker.overlay(stage).review_status,'Awaiting Review');assert.equal(JSON.stringify(stale),before);
tracker.receive({runs:[pass('own',stage)]});assert.equal(tracker.overlay(stage).status,'Not run');
const retry=start(stage);tracker.success(retry,{runs:[pass('new',stage)]});assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_old_stale_records_do_not_replace_pending_or_unknown_failure(self):
        self.client(r"""
tracker.receive({runs:[pass('old',stage,{freshness:'Stale'})]});const token=start(stage);
tracker.receive({runs:[pass('old',stage,{freshness:'Stale'})]});assert.equal(tracker.overlay(stage).status,'Running');
tracker.failure(token,new Error('Unknown request outcome'));tracker.receive({runs:[pass('old',stage,{freshness:'Stale'})]});
assert.equal(tracker.overlay(stage).status,'Failed');assert.equal(tracker.overlay(stage).reconnectRequired,true);
const nextToken=start(stage);tracker.success(nextToken,{runs:[pass('own',stage,{execution_status:'Running'})]});
tracker.observeFailure(new Error('Progress unavailable'),stage);tracker.receive({runs:[pass('own',stage,{freshness:'Stale'})]});
assert.equal(tracker.overlay(stage).status,'Failed');assert.equal(tracker.overlay(stage).reconnectRequired,true);
""")

    def test_failed_validation_cancelled_and_interrupted_do_not_become_complete(self):
        self.client(r"""
for(const change of [{validation_status:'Failed'},{validation_status:'Unsupported'},{execution_status:'Failed'},
 {execution_status:'Cancelled'},{execution_status:'Interrupted'}]) {
 const token=start(stage);tracker.success(token,{runs:[pass('case-'+JSON.stringify(change),stage,change)]});
 assert.equal(tracker.overlay(stage).status,'Failed');assert.equal(tracker.overlay(stage).reconnectRequired,false);
}
""")

    def test_fast_server_rejection_is_immediately_failed(self):
        self.client(r"""
const token=start(stage);const error=Object.assign(new Error('Invalid current source'),{status:409});
tracker.failure(token,error);assert.equal(tracker.overlay(stage).status,'Failed');assert.equal(tracker.overlay(stage).reconnectRequired,false);
assert.match(tracker.overlay(stage).detail,/Invalid current source/);assert.equal(tracker.overlay(next).status,'Not run');
""")

    def test_unknown_timeout_reads_backend_without_resending_and_recovers(self):
        self.client(r"""
tracker.receive({runs:[pass('old',stage)]});const token=start(stage);tracker.failure(token,new Error('Network timeout'));
assert.equal(tracker.overlay(stage).status,'Failed');assert.equal(tracker.overlay(stage).reconnectRequired,true);
tracker.receive({runs:[pass('old',stage)]});assert.equal(tracker.overlay(stage).reconnectRequired,true);
tracker.receive({runs:[pass('new',stage,{execution_status:'Running',review_status:'Awaiting Review'})]});
assert.equal(tracker.overlay(stage).status,'Running');assert.equal(tracker.overlay(stage).reconnectRequired,false);
tracker.receive({runs:[pass('new',stage)]});assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_failed_read_stops_running_claim_and_reconnects_exact_saved_record(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{runs:[pass('own',stage,{execution_status:'Running'})]});
assert.equal(tracker.observeFailure(new Error('Progress service offline'),stage),true);
assert.equal(tracker.overlay(stage).status,'Failed');assert.equal(tracker.overlay(stage).reconnectRequired,true);
tracker.receive({runs:[pass('unrelated',stage)]});assert.equal(tracker.overlay(stage).reconnectRequired,true);
tracker.receive({runs:[pass('own',stage,{execution_status:'Running'})]});assert.equal(tracker.overlay(stage).status,'Running');
tracker.receive({runs:[pass('own',stage)]});assert.equal(tracker.overlay(stage).status,'Complete');
assert.equal(tracker.observeFailure(new Error('Later read failed'),stage),false);assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_project_read_failure_marks_active_observations_only(self):
        self.client(r"""
tracker.receive({runs:[pass('a','local_rtl_generation',{execution_status:'Running'}),pass('b',stage,{execution_status:'Running'})]});
const token=start('layout');tracker.success(token,{runs:[pass('layout-done','layout')]});
tracker.observeFailure(new Error('Project GET failed'));
assert.equal(tracker.overlay('local_rtl_generation').status,'Failed');assert.equal(tracker.overlay(stage).status,'Failed');
assert.equal(tracker.overlay('layout').status,'Complete');assert.equal(tracker.overlay('drc').status,'Not run');
""")

    def test_unknown_success_is_not_fabricated_completion(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{});assert.equal(tracker.overlay(stage).status,'Failed');
assert.equal(tracker.overlay(stage).reconnectRequired,true);assert.match(tracker.overlay(stage).detail,/Reconnect/);
""")

    def test_reload_keeps_invalidation_and_waits_for_recorded_progress(self):
        self.client(r"""
tracker.receive({runs:[pass('old-next',next)]});const token=start(stage);const restored=new Tracker(options);restored.setScope(tracker.scopeKey);
assert.equal(restored.overlay(stage).status,'Failed');assert.equal(restored.overlay(stage).reconnectRequired,true);
assert.equal(restored.overlay(next).status,'Not run');restored.receive({runs:[pass('old-next',next),pass('live',stage,{execution_status:'Running'})]});
assert.equal(restored.overlay(stage).status,'Running');assert.equal(restored.overlay(next).status,'Not run');
restored.receive({runs:[pass('live',stage)]});assert.equal(restored.overlay(stage).status,'Complete');
""")

    def test_project_and_semantic_revision_isolation_ignore_out_of_order_responses(self):
        self.client(r"""
const scope=tracker.scopeKey;const token=start(stage);tracker.setScope('workspace/another-project/system/semantic-a');
assert.equal(tracker.success(token,{runs:[pass('wrong-project',stage)]}),false);assert.equal(tracker.failure(token,new Error('old')),false);
assert.equal(tracker.receive({runs:[pass('wrong-project',stage)]},scope),false);assert.equal(tracker.overlay(stage),null);
tracker.setScope('workspace/project/system/semantic-b');assert.equal(tracker.overlay(stage),null);
tracker.setScope(scope);assert.equal(tracker.overlay(stage).reconnectRequired,true);
""")

    def test_newer_action_supersedes_old_completion_same_stage(self):
        self.client(r"""
const first=start(stage),second=start(stage);assert.equal(tracker.success(first,{runs:[pass('old-result',stage)]}),false);
assert.equal(tracker.overlay(stage).status,'Running');tracker.success(second,{runs:[pass('new-result',stage)]});
assert.equal(tracker.overlay(stage).recordId,'new-result');assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_terminal_record_does_not_regress_on_late_running_poll(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{runs:[pass('new',stage)]});
tracker.receive({runs:[pass('new',stage,{execution_status:'Running'})]});assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_late_unrelated_record_cannot_replace_pinned_current_attempt(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{runs:[pass('current',stage)]});
tracker.receive({runs:[pass('other-old-request',stage,{execution_status:'Running'})]});
assert.equal(tracker.overlay(stage).recordId,'current');assert.equal(tracker.overlay(stage).status,'Complete');
tracker.receive({runs:[pass('other-old-request',stage,{validation_status:'Failed'})]});
assert.equal(tracker.overlay(stage).recordId,'current');assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_new_batch_stays_running_while_individual_item_finished(self):
        self.client(r"""
const token=tracker.begin(action('workflow/batches/start',{stage_id:next,request_id:'r'}));
const item=pass('item',next),batch={id:'batch',stage_id:next,execution_status:'Running',validation_status:'Not Checked',items:[{run_id:'item'}]};
tracker.success(token,{workflow_runs:[item],workflow_batches:[batch]});assert.equal(tracker.overlay(next).status,'Running');
tracker.receive({workflow_runs:[item],workflow_batches:[{...batch,execution_status:'Completed',validation_status:'Passed'}]});
assert.equal(tracker.overlay(next).status,'Complete');assert.equal(tracker.overlay(next).recordId,'batch');
""")

    def test_generation_batch_object_and_manual_batch_review(self):
        self.client(r"""
const token=tracker.begin(action('generation/batches/start',{}));
const job=pass('j','local_rtl_generation',{review_status:'Awaiting Review'});
const batch={id:'batch',execution_status:'Completed',validation_status:'Passed',items:[{job_id:'j'}]};
tracker.success(token,{generation:{jobs:[job]},generation_batches:{batches:[batch]}});
assert.equal(tracker.overlay('local_rtl_generation').status,'Review required');
""")

    def test_stage_specific_groups_and_summary_fallback(self):
        self.client(r"""
for(const [key,id] of [['physical_workflow','layout'],['drc_workflow','drc'],['lvs_workflow','lvs'],['postlayout_workflow','post_layout_verification']]) {
 const token=start(id);tracker.success(token,{[key]:{runs:[pass('new-'+id,id)]}});assert.equal(tracker.overlay(id).status,'Complete');
}
const token=start('graph_editor');tracker.success(token,{workflow:[{...pass('graph_editor','graph_editor'),latest_run_id:'graph-run'}]});
assert.equal(tracker.overlay('graph_editor').recordId,'graph-run');
""")

    def test_same_job_verification_is_execution_without_new_record_identity(self):
        self.client(r"""
const job=pass('job','local_rtl_generation');tracker.receive({generation:{jobs:[job]}});
const token=tracker.begin(action('generation/verify',{job_id:'job'}));tracker.success(token,{generation:{jobs:[job]}});
assert.equal(tracker.overlay('local_rtl_generation').status,'Complete');
""")

    def test_narrow_single_record_poll_recovers_known_record(self):
        self.client(r"""
const token=start(stage);tracker.success(token,{workflow_runs:[pass('new',stage,{execution_status:'Running'})]});
tracker.receive({...pass('new',stage),stage_id:undefined});assert.equal(tracker.overlay(stage).status,'Complete');
""")

    def test_storage_failure_and_corruption_do_not_prevent_execution(self):
        self.client(r"""
const broken=new Tracker({readStorage:()=>'{bad',writeStorage:()=>{throw Error('full');}});broken.setScope('scope');
const token=broken.begin({kind:'execute',stageId:stage});assert.equal(broken.overlay(stage).status,'Running');
broken.success(token,{runs:[pass('new',stage)]});assert.equal(broken.overlay(stage).status,'Complete');
""")

    def test_ledger_never_persists_prompt_rtl_or_mutates_evidence(self):
        self.client(r"""
const token=start(stage);const envelope={runs:[pass('new',stage,{rtl:'SECRET_RTL',context:{prompt:'SECRET_PROMPT'}})]};
const original=JSON.stringify(envelope);tracker.success(token,envelope);assert.equal(JSON.stringify(envelope),original);
const saved=storage.get(tracker.scopeKey);assert.ok(!saved.includes('SECRET_RTL'));assert.ok(!saved.includes('SECRET_PROMPT'));
tracker.reset();assert.equal(tracker.overlay(stage),null);
""")


if __name__ == "__main__":
    unittest.main()
