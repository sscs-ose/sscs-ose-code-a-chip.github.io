"""Isolated controller checks for repeated GUI preparation, no live EDA."""
import unittest
import test_generic_physical_repair_gui as earlier


class GenericPhysicalRetryGuiTests(unittest.TestCase):
    def client(self, body, prefix):
        earlier.GenericPhysicalRepairGuiTests.client(self, body, prefix)

    def test_s11_next_generic_prepare_is_explicit_ids_only_with_all_guards(self):
        self.client(r"""
const run=failure();run.runtime_configuration.profile={profile_version:'hullcirq-sky130-generic-closure-v1'};
run.checks.status='Completed';run.checks.implementation_kind='fresh_generic_standard_electrical_closure';
run.checks.upstream_technology_mapping_reused=false;run.checks.technology_mapping_executed=true;
project.envelope.physical_repair_session=genericStatus;install(run);const original=JSON.stringify(run);
assert.equal(flow.genericRepairEligible(run),true);assert.equal(find('physical-workflow-prepare-repair').disabled,false);
assert.match(text(find('physical-workflow-repair-card')),/five percentage points less core utilization/);
for(const key of ['readOnly','dirty','busy','conflict']){project[key]=true;flow.refresh();assert.equal(find('physical-workflow-prepare-repair').disabled,true);await flow.prepareFixedRepair(run);project[key]=false;}
assert.equal(requests.length,0);flow.refresh();
responder=async(route,body)=>{assert.equal(route,'physical-workflow/repair-profile');assert.deepEqual(normalized(body),{failed_layout_id:run.id,revision_id:'software-qa-revision'});return{...project.envelope,physical_repair_session:{...genericStatus,profile_version:'hullcirq-sky130-generic-closure-v2',session_schema:'hullcirq-gui-generic-physical-retry-session-v2',retry_attempt:1,core_utilization:30},physical_workflow:{...flow.data,runs:[{...run,freshness:'Stale'}]}};};
await flow.prepareFixedRepair(run);assert.equal(requests.length,1);assert.equal(JSON.stringify(run),original);
assert.equal(find('physical-workflow-prepare-repair'),null);assert.ok(requests.every(r=>!r.route.endsWith('/runs')&&!r.route.endsWith('/review')));
""", earlier.REPAIR_CLIENT + earlier.GENERIC)

    def test_s14_existing_generic_profile_can_prepare_again_without_auto_run(self):
        self.client(r"""
project.envelope.physical_repair_session={...genericStatus,profile_version:'hullcirq-sky130-generic-closure-v2',session_schema:'hullcirq-gui-generic-physical-retry-session-v2',retry_attempt:2};
flow.refresh();assert.equal(flow.physicalRepairEligible(run),true);assert.equal(flow.physicalRepairGate(run),'');
assert.equal(find('postlayout-physical-repair-prepare').disabled,false);
assert.match(text(find('postlayout-physical-repair-card')),/five percentage points lower core utilization/);
responder=async(route,body)=>{assert.equal(route,'postlayout-workflow/physical-repair-profile');return{...project.envelope,postlayout_workflow:{...flow.data,runs:[{...run,freshness:'Stale'}]}};};
await flow.preparePhysicalRepair(run);assert.equal(requests.length,1);assert.deepEqual(normalized(requests[0].body),{failed_s14_id:run.id,revision_id:'software-qa-revision'});
assert.ok(requests.every(r=>!r.route.endsWith('/runs')&&!r.route.endsWith('/review')));
""", earlier.CLIENT + earlier.S14)

    def test_false_native_or_mixed_failure_does_not_expose_retry(self):
        self.client(r"""
const run=failure();run.runtime_configuration.profile={profile_version:'hullcirq-sky130-generic-closure-v2'};
run.checks.status='Completed';run.checks.implementation_kind='fresh_generic_standard_electrical_closure';run.checks.upstream_technology_mapping_reused=false;run.checks.technology_mapping_executed=true;
project.envelope.physical_repair_session={...genericStatus,profile_version:'hullcirq-sky130-generic-closure-v2',session_schema:'hullcirq-gui-generic-physical-retry-session-v2'};install(run);
for(const [obj,key,value] of [[run,'freshness','Stale'],[run.checks,'technology_mapping_executed',false],[run.checks,'software_qa_fixture',true],[run.checks.checks.timing,'validation_status','Failed'],[run.checks,'commands',[]]]){const old=obj[key];obj[key]=value;assert.equal(flow.genericRepairEligible(run),false);await flow.prepareFixedRepair(run);obj[key]=old;}
assert.equal(requests.length,0);
""", earlier.REPAIR_CLIENT + earlier.GENERIC)

    def test_unknown_s14_preparation_outcome_blocks_resend_and_execution_until_refresh(self):
        self.client(r"""
project.envelope.physical_repair_session=genericStatus;flow.refresh();
responder=async()=>{throw Error('connection-lost-software-fixture');};
await flow.preparePhysicalRepair(run);assert.equal(requests.length,1);assert.match(flow.pollError,/without resending/);
await flow.preparePhysicalRepair(run);await flow.start();assert.equal(requests.length,1);
responder=async(route)=>{assert.equal(route,'project');return project.envelope;};
await flow.refreshSaved();assert.equal(requests.length,2);assert.equal(flow.pollError,null);assert.equal(flow.physicalRepairGate(run),'');
""", earlier.CLIENT + earlier.S14)


if __name__ == '__main__': unittest.main()
