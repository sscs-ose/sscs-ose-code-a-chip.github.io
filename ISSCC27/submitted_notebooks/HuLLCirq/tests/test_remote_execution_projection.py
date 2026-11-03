"""Browser-only remote completion reconciliation; no APIs, EDA or saved writes."""
import shutil
import subprocess
import unittest
from test_execution_state import CLIENT, PROJECT


SETUP=r"""
const early='2026-10-31T00:00:00Z',boundary='2026-10-31T01:00:00Z',later='2026-10-31T02:00:00Z';
const old=stages.slice(3).map(s=>pass('old-'+s,s,{created_at:early}));
tracker.receive({workflow_runs:old});
const token=start('specifications'),cause=pass('new-definition','specifications',{created_at:boundary});
tracker.success(token,{runs:[cause]});
const current=stages.slice(3).map(s=>pass('new-'+s,s,{created_at:later}));
const full=()=>({runs:[cause],workflow_runs:structuredClone(current),workflow:stages.map((s,i)=>pass(s,s,{latest_run_id:i<3?i===2?cause.id:'definition-'+i:'new-'+s}))});
"""


class RemoteExecutionProjectionTests(unittest.TestCase):
    def client(self,body):
        node=shutil.which('node')
        if not node:self.skipTest('Installed Node required; no dependency installation.')
        script=CLIENT+SETUP+body
        result=subprocess.run([node,'-e',script],cwd=PROJECT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_new_remote_adopted_records_restore_all_stages_without_start_or_cache_clear(self):
        self.client(r"""
const response=full(),before=JSON.stringify(response);tracker.receive(response);
for(const s of stages.slice(3))assert.equal(tracker.overlay(s).status,'Complete',s);
assert.equal(JSON.stringify(response),before);assert.equal(tracker.serial,1);
""")

    def test_persisted_invalidation_reconciles_after_reload_without_reset(self):
        self.client(r"""
const stale=storage.get(tracker.scopeKey),other=new Tracker(options);other.setScope(tracker.scopeKey);
assert.equal(other.overlay('layout').status,'Not run');other.receive(full());
for(const s of stages.slice(3))assert.equal(other.overlay(s).status,'Complete',s);
assert.ok(stale.includes('An earlier stage was started again'));assert.equal(other.serial,1);
""")

    def test_new_awaiting_review_result_is_review_required_never_complete(self):
        self.client(r"""
const response=full();response.workflow_runs.at(-1).review_status='Awaiting Review';response.workflow.at(-1).review_status='Awaiting Review';tracker.receive(response);
assert.equal(tracker.overlay('post_layout_verification').status,'Review required');
""")

    def test_old_baseline_and_different_historical_ids_do_not_advance(self):
        self.client(r"""
for(const kind of ['baseline','historical','not-latest','stale','no-authoritative','unaccepted-prerequisite']){
 const t=new Tracker();t.setScope('negative-'+kind);t.receive({workflow_runs:old});const tok=t.begin({kind:'execute',stageId:'specifications'});t.success(tok,{runs:[cause]});const response=full();
 const row=response.workflow_runs.find(r=>r.stage_id==='local_rtl_generation'),summary=response.workflow.find(r=>r.id==='local_rtl_generation');
 if(kind==='baseline'){row.id='old-local_rtl_generation';summary.latest_run_id=row.id;}
 if(kind==='historical'){row.id='different-old-id';row.created_at=early;summary.latest_run_id=row.id;}
 if(kind==='not-latest')row.id='different-history-id';
 if(kind==='stale')row.freshness='Stale';
 if(kind==='no-authoritative')delete response.workflow;
 if(kind==='unaccepted-prerequisite')response.workflow[1].review_status='Awaiting Review';
 t.receive(response);assert.equal(t.overlay('local_rtl_generation').status,'Not run',kind);assert.equal(t.overlay('layout').status,'Not run',kind);
}
""")

    def test_active_unknown_and_failed_upstream_requests_remain_blocking(self):
        self.client(r"""
for(const state of ['Running','unknown','Failed']){
 const t=new Tracker();t.setScope('blocked-'+state);const tok=t.begin({kind:'execute',stageId:'specifications'});
 if(state!=='Running')t.failure(tok,state==='unknown'?new Error('connection lost'):{status:409,message:'Rejected'});
 // Pin this unresolved cause, so unrelated passive records cannot resolve it.
 t.entries.specifications.recordIds=['owned-unresolved'];t.receive(full());
 assert.equal(t.overlay('layout').status,'Not run',state);
}
""")

    def test_remote_corrected_profile_replaces_pinned_stale_lvs_after_reload(self):
        self.client(r"""
const t=new Tracker(options);t.setScope('proxy-stale-v2');
const tok=t.begin({kind:'execute',stageId:'lvs'}),v2=pass('original-v2','lvs',{created_at:boundary,finished_at:'2026-10-31T01:30:00Z'});
t.success(tok,{lvs_workflow:{runs:[v2]}});
const response=full(),v7=response.workflow_runs.find(r=>r.stage_id==='lvs');
response.workflow_runs.push({...v2,freshness:'Stale'});t.receive(response);
assert.equal(t.overlay('lvs').status,'Complete');assert.equal(t.overlay('lvs').recordId,v7.id);
// Existing pre-fix browser state had already baselined the unseen v7 ID.
Object.assign(t.entries.lvs,{status:'Not run',invalidated:true,recordId:v2.id,recordIds:[v2.id],baseline:[v2.id,v7.id]});t.persist();
const reopened=new Tracker(options);reopened.setScope(t.scopeKey);reopened.receive(response);
assert.equal(reopened.overlay('lvs').status,'Complete');assert.equal(reopened.overlay('lvs').recordId,v7.id);
""")

    def test_corrected_profile_cannot_promote_same_historical_nonlatest_or_stale_evidence(self):
        self.client(r"""
for(const kind of ['same-id','historical','not-latest','stale','prerequisite','uncertain']){
 const t=new Tracker();t.setScope('v7-negative-'+kind);const tok=t.begin({kind:'execute',stageId:'lvs'});
 const v2=pass('original-v2','lvs',{created_at:boundary,finished_at:'2026-10-31T01:30:00Z'});t.success(tok,{lvs_workflow:{runs:[v2]}});
 const response=full(),v7=response.workflow_runs.find(r=>r.stage_id==='lvs'),summary=response.workflow.find(r=>r.id==='lvs');response.workflow_runs.push({...v2,freshness:'Stale'});
 if(kind==='same-id'){v7.id=v2.id;summary.latest_run_id=v2.id;}
 if(kind==='historical')v7.created_at=early;
 if(kind==='not-latest')v7.id='not-the-latest';
 if(kind==='stale')v7.freshness='Stale';
 if(kind==='prerequisite')response.workflow.find(r=>r.id==='drc').review_status='Awaiting Review';
 if(kind==='uncertain'){t.entries.drc={status:'Failed',reconnectRequired:true,recordIds:['unknown-own-drc']};}
 t.receive(response);assert.notEqual(t.overlay('lvs').status,'Complete',kind);
}
""")
