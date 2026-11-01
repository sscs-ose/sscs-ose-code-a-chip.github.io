"""Generic closure presentation/explicit preparation; no live GUI/API/EDA."""
import shutil
import subprocess
import unittest

from test_postlayout_workflow_gui import CLIENT, PROJECT
from test_physical_workflow_gui import REPAIR_CLIENT

GENERIC = r"""
const genericStatus={configured:true,bundle_present:true,error:null,session_schema:'hullcirq-gui-generic-physical-repair-session-v1',profile_version:'hullcirq-sky130-generic-closure-v1',repair_generation:1,implementation_kind:'fresh_generic_standard_electrical_closure',technology_mapping_reused:false,source_identity:{failed_s14_id:'generic-failed-s14'}};
"""
S14 = GENERIC + r"""
layout.verification_plan={kind:'generic_cycle_vectors',vector_count:8,interface:{clock:{period_ns:30}}};
function genericFailure(){return{...record('generic-failed-s14'),execution_scope:'post_route_functional_plus_sta',verification_supported:true,evidence_kind:'trusted_fixed_postlayout_execution',error:null,checks:{origin:'trusted_fixed_postlayout_adapter',execution_scope:'post_route_functional_plus_sta',status:'Completed',validation_status:'Failed',executed:true,exit_code:0,cleanup_unresolved:false,commands:Array.from({length:11},()=>({executed:true,status:'Completed',exit_code:0})),checks:Object.fromEntries(['source_identity','configuration','functional','parasitics','constraints','setup_hold','electrical'].map(name=>[name,{validation_status:name==='electrical'?'Failed':'Passed'}]))}};}
const run=genericFailure();install(run);
"""


class GenericPhysicalRepairGuiTests(unittest.TestCase):
    def client(self, body, prefix=CLIENT + S14):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated generic closure fixtures.')
        result = subprocess.run([node, '-e', prefix + '\n(async()=>{\n' + body +
                                 '\n})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generic_prepare_is_ids_only_and_never_starts_or_adopts_physical_execution(self):
        self.client(r"""
const before=JSON.stringify(run),plan=JSON.stringify(layout.verification_plan);assert.equal(flow.physicalRepairEligible(run),true);assert.equal(find('postlayout-physical-repair-prepare').disabled,false);
assert.match(text(find('postlayout-physical-repair-card')),/fresh mapping\/placement\/CTS\/routing closure/);assert.doesNotMatch(text(find('postlayout-physical-repair-card')),/50 ns/);
responder=async(route,body)=>{assert.equal(route,'postlayout-workflow/physical-repair-profile');return{...project.envelope,physical_repair_session:genericStatus,physical_workflow:{runs:[{...layout,freshness:'Stale'}],accepted_run_id:null},postlayout_workflow:{...flow.data,runs:[{...run,freshness:'Stale'}]}};};
await flow.preparePhysicalRepair(run);assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0].body),{failed_s14_id:run.id,revision_id:'software-qa-revision'});assert.equal(navigations.at(-1),'layout');
assert.equal(JSON.stringify(run),before);assert.equal(JSON.stringify(layout.verification_plan),plan);assert.equal(flow.selected().validation_status,'Failed');assert.equal(flow.selected().freshness,'Stale');
assert.equal(find('postlayout-physical-repair-prepare'),null);assert.ok(find('postlayout-physical-repair-layout'));assert.match(text(find('postlayout-physical-repair-card')),/fresh technology mapping/);assert.match(text(find('postlayout-physical-repair-card')),/not silently dropped/);assert.doesNotMatch(text(find('postlayout-physical-repair-card')),/50 ns/);
assert.ok(requests.every(request=>!request.route.endsWith('/runs')&&!request.route.endsWith('/review')));assert.match(toasts.at(-1),/No EDA was started/);
""")

    def test_generic_eligibility_keeps_all_exact_checks_and_readonly_dirty_active_guards(self):
        self.client(r"""
for(const [object,key,value] of [[run,'freshness','Stale'],[run,'execution_status','Failed'],[run,'verification_supported',false],[run,'error',{code:'error'}],[run.checks,'commands',run.checks.commands.slice(1)],[run.checks.checks.functional,'validation_status','Failed'],[run.checks.checks.electrical,'validation_status','Passed']]){const old=object[key];object[key]=value;assert.equal(flow.physicalRepairEligible(run),false);object[key]=old;}
for(const key of ['readOnly','dirty','busy','conflict']){project[key]=key==='conflict'?'newer':true;flow.refresh();assert.equal(find('postlayout-physical-repair-prepare').disabled,true);await flow.preparePhysicalRepair(run);project[key]=key==='conflict'?null:false;}
project.envelope.workspace_identity={read_only:true};assert.match(flow.physicalRepairGate(run),/read-only/);await flow.preparePhysicalRepair(run);project.envelope.workspace_identity={read_only:false};
flow.data.runs.push({...run,id:'active-other',execution_status:'Running'});assert.match(flow.physicalRepairGate(run),/active/);await flow.preparePhysicalRepair(run);assert.equal(requests.length,0);
""")

    def test_delayed_prepare_response_or_failure_from_prior_context_is_dropped(self):
        self.client(r"""
for(const rejected of [false,true]){const wait=deferred();responder=async()=>{await wait.promise;if(rejected)throw Error('OLD_CONTEXT_FAILURE');return{...project.envelope,physical_repair_session:genericStatus};};
 const old=project.envelope,noticeCount=notices.length,navigationCount=navigations.length,pending=flow.preparePhysicalRepair(run);project.envelope={...old,workspace_identity:{project_id:'other-project',system_id:'other-system'}};wait.resolve();await pending;
 assert.equal(project.envelope.physical_repair_session,old.physical_repair_session);assert.equal(notices.length,noticeCount);assert.equal(navigations.length,navigationCount);assert.equal(flow.busy,false);project.envelope=old;
}
""")

    def test_s11_generic_session_has_fresh_scope_and_no_npu_retry_or_implicit_execution(self):
        self.client(r"""
const run=failure();run.runtime_configuration.profile={profile_version:'hullcirq-sky130-generic-closure-v1',implementation_kind:'fresh_generic_standard_electrical_closure'};run.checks.implementation_kind='fresh_generic_standard_electrical_closure';run.checks.upstream_technology_mapping_reused=false;run.checks.technology_mapping_executed=true;
project.envelope.physical_repair_session=genericStatus;install(run);const original=JSON.stringify(run);
assert.equal(find('physical-workflow-repair-card').hidden,false);assert.equal(find('physical-workflow-prepare-repair'),null);assert.equal(flow.fixedRepairEligible(run),false);
const card=text(find('physical-workflow-repair-card'));assert.match(card,/Prepared generic physical closure/);assert.match(card,/fresh technology mapping, placement, CTS, routing/);assert.match(card,/Mixed placement only/);assert.doesNotMatch(card,/50 ns|NPU|pre-CTS checkpoint|post-global-route checkpoint/);
assert.match(find('physical-workflow-implementation').textContent,/fresh technology mapping/);assert.match(find('physical-workflow-implementation').textContent,/not a resumed predecessor checkpoint/);assert.equal(requests.length,0);
await flow.prepareFixedRepair(run);assert.equal(requests.length,0);flow.refresh();assert.equal(JSON.stringify(run),original);
// A separately clicked Run action, not preparing or viewing the card, starts S11.
responder=async()=>({...project.envelope,physical_workflow:{...flow.data,runs:[...flow.data.runs,{id:'new-generic-layout',execution_status:'Queued'}],latest_run_id:'new-generic-layout'}});
await flow.start();assert.equal(requests.length,1);assert.equal(requests[0].route,'physical-workflow/runs');
""", prefix=REPAIR_CLIENT + GENERIC)


if __name__ == '__main__':
    unittest.main()
