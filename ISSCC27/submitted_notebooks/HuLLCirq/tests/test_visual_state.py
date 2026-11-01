"""Isolated display decisions; no LLM, EDA, project mutation, or network calls."""
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const sandbox={URL};vm.createContext(sandbox);
const source=fs.readFileSync('src/gui/visual_state.js','utf8');
vm.runInContext(source.replace(/export /g,'')+'\nthis.stage=stageVisualState;this.connection=connectionVisualState;',sandbox);
const stage=sandbox.stage,connection=sandbox.connection;
const accepted={execution_status:'Completed',validation_status:'Passed',review_status:'Accepted',freshness:'Current',implemented:true};
const profile={execution_location:'Local',api_type:'chat_completions',base_url:'http://127.0.0.1:11435/v1',model:'qwen3:8b'};
const probe={status:'Connected',selected_model_available:true,profile_revision_id:'profile-current'};
const provider={profile,profileRevisionId:'profile-current',probe};
"""


class VisualStateTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated GUI checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n" + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_complete_requires_current_acceptance_and_all_checks(self):
        self.run_client(r"""
assert.equal(stage(accepted).kind,'complete');
for(const patch of [{review_status:'Awaiting Review'},{validation_status:'Not Checked'},{execution_status:'Not Run'},{freshness:'Stale'},{freshness:undefined}]) {
 assert.notEqual(stage({...accepted,...patch}).kind,'complete');
}
assert.equal(stage({...accepted,review_status:'Awaiting Review'}).label,'Review required');
assert.equal(stage({...accepted,validation_status:'Not Checked'}).label,'Not run');
""")

    def test_failures_and_changes_are_visible_before_partial_counts(self):
        self.run_client(r"""
for(const patch of [{execution_status:'Failed'},{validation_status:'Failed'}]) {
 const value=stage({...accepted,...patch,accepted_node_count:8,required_node_count:11});
 assert.equal(value.kind,'error');assert.equal(value.label,'Failed');
}
assert.equal(stage({...accepted,review_status:'Changes Requested'}).kind,'error');
assert.equal(stage({...accepted,review_status:'Request Changes'}).label,'Failed');
""")

    def test_active_operation_is_distinct_from_accepted_old_results(self):
        self.run_client(r"""
for(const execution_status of ['Running','Queued','Starting','Stopping','Cancelling']) {
 const value=stage({...accepted,execution_status});
 assert.equal(value.kind,'working');assert.equal(value.label,'Running');
}
for(const execution_status of ['Cancelled','Interrupted']) assert.equal(stage({...accepted,execution_status}).label,'Failed');
""")

    def test_dirty_stale_and_unknown_freshness_never_look_complete(self):
        self.run_client(r"""
assert.equal(stage(accepted,{dirty:true}).label,'Not run');
assert.match(stage(accepted,{dirty:true}).detail,/Unsaved changes/);
assert.equal(stage({...accepted,freshness:'Stale'}).label,'Not run');
assert.match(stage({...accepted,freshness:'Stale'}).detail,/Earlier evidence is retained/);
assert.equal(stage({...accepted,freshness:undefined}).label,'Not run');
assert.equal(stage({...accepted,freshness:'Unknown'}).kind,'pending');
""")

    def test_partial_adoptions_do_not_complete_whole_stage(self):
        self.run_client(r"""
assert.equal(stage({...accepted,accepted_node_count:1,required_node_count:11}).label,'Not run');
assert.match(stage({...accepted,accepted_node_count:1,required_node_count:11}).detail,/1\/11 nodes adopted/);
assert.equal(stage({...accepted,accepted_node_count:10,required_node_count:11}).kind,'pending');
assert.equal(stage({...accepted,accepted_node_count:11,required_node_count:11}).kind,'complete');
assert.equal(stage(accepted,{partial:{accepted:2,total:11}}).kind,'pending');
assert.equal(stage(accepted,{partial:true}).kind,'pending');
assert.equal(stage({execution_status:'Not Run',accepted_node_count:0,required_node_count:11}).kind,'pending');
for(const accepted_node_count of [undefined,null,-1,12,NaN])
 assert.equal(stage({...accepted,accepted_node_count,required_node_count:11}).label,'Not run');
assert.equal(stage({...accepted,review_required:true}).label,'Review required');
""")

    def test_blocked_is_distinct_from_not_started_and_completed(self):
        self.run_client(r"""
assert.equal(stage(null).kind,'pending');
assert.equal(stage({implemented:false}).kind,'pending');
assert.equal(stage({implemented:true,ready:false}).label,'Not run');
assert.equal(stage({validation_status:'Unsupported'}).kind,'pending');
const blocked=stage({execution_status:'Not Run'},{blockedReason:{message:'Synthesis is required.'}});
assert.equal(blocked.kind,'pending');assert.equal(blocked.detail,'Synthesis is required.');
assert.equal(stage(accepted,{blockedReason:'A previous node still needs work.'}).kind,'complete');
""")

    def test_only_five_primary_states_and_unrun_is_never_awaiting_review(self):
        self.run_client(r"""
const cases=[
 [{execution_status:'Not Run',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current'},'Not run'],
 [{...accepted,execution_status:'Queued'},'Running'],
 [accepted,'Complete'],
 [{...accepted,review_status:'Awaiting Review'},'Review required'],
 [{...accepted,validation_status:'Failed'},'Failed'],
];
assert.deepEqual(cases.map(([input,expected])=>{const result=stage(input);assert.equal(result.label,expected);assert.equal(result.status,expected);return result.label;}),
 ['Not run','Running','Complete','Review required','Failed']);
assert.equal(stage({...accepted,execution_status:'Not Run',review_status:'Awaiting Review'}).label,'Not run');
const staleFailure=stage({...accepted,execution_status:'Failed',validation_status:'Failed',freshness:'Stale'});
assert.equal(staleFailure.label,'Not run');assert.match(staleFailure.detail,/Earlier evidence/);
""")

    def test_click_overlays_override_old_results_without_mutating_evidence(self):
        self.run_client(r"""
const original=JSON.stringify(accepted);
for(const status of ['Not run','Running','Complete','Review required','Failed']) {
 const value=stage(accepted,{overlay:{status,detail:'Current operation'}});
 assert.equal(value.label,status);assert.equal(value.detail,'Current operation');
}
assert.equal(stage(accepted,{overlay:{invalidated:true}}).label,'Not run');
assert.equal(stage({...accepted,validation_status:'Failed'},{overlay:{status:'Running'}}).label,'Running');
assert.equal(stage(accepted,{overlay:{status:'Failed',reconnectRequired:true,detail:'Connection lost. Reconnect.'}}).label,'Failed');
assert.equal(JSON.stringify(accepted),original);
""")

    def test_current_connected_probe_requires_model_discovery(self):
        self.run_client(r"""
assert.equal(connection(provider).kind,'complete');assert.equal(connection(provider).label,'Connected');
assert.notEqual(connection({...provider,probe:{...probe,selected_model_available:undefined}}).kind,'complete');
assert.equal(connection({...provider,probe:{...probe,selected_model_available:false}}).kind,'error');
assert.equal(connection({...provider,probe:{...probe,profile_revision_id:'old'}}).kind,'attention');
assert.equal(connection({...provider,probe:{...probe,profile_revision_id:undefined}}).kind,'attention');
assert.equal(connection({...provider,profileDirty:true}).label,'Unsaved settings');
""")

    def test_connection_missing_checking_failure_and_readonly(self):
        self.run_client(r"""
assert.equal(connection({}).kind,'pending');assert.equal(connection({...provider,probe:null}).kind,'attention');
assert.equal(connection({...provider,busy:true}).kind,'working');
assert.equal(connection({...provider,probe:{...probe,status:'Failed',error:{message:'Connection refused.'}}}).detail,'Connection refused.');
assert.equal(connection({...provider,probe:{...probe,status:'Cancelled'}}).kind,'attention');
assert.equal(connection({...provider,readOnly:true}).kind,'pending');
assert.equal(connection({...provider,readOnly:true,busy:true}).label,'Recorded only');
""")

    def test_matching_local_runtime_overrides_old_successful_probe(self):
        self.run_client(r"""
for(const state of ['Failed','Unavailable']) assert.equal(connection({...provider,runtime:{state,endpoint:profile.base_url}}).kind,'error');
assert.equal(connection({...provider,runtime:{state:'Stopped',endpoint:'http://localhost:11435/v1/'}}).label,'Offline');
assert.equal(connection({...provider,runtimeError:'Status request failed.'}).kind,'error');
for(const state of ['Starting','Stopping','Checking']) assert.equal(connection({...provider,runtime:{state,endpoint:profile.base_url}}).kind,'working');
assert.equal(connection({...provider,runtime:{state:'Running',endpoint:profile.base_url},probe:null}).kind,'attention');
""")

    def test_unrelated_local_runtime_does_not_override_network_or_custom_api(self):
        self.run_client(r"""
for(const profilePatch of [{execution_location:'Network',base_url:'https://api.example.com/v1'},{base_url:'http://localhost:9000/v1'},{base_url:'http://localhost:11435/other'}]) {
 const value=connection({...provider,profile:{...profile,...profilePatch},runtime:{state:'Stopped',endpoint:profile.base_url},runtimeError:'Unrelated local startup error.'});
 assert.equal(value.kind,'complete');
}
""")

    def test_classifiers_are_pure_and_all_states_have_noncolor_labels(self):
        self.run_client(r"""
const input={...accepted,accepted_node_count:8,required_node_count:11},before=JSON.stringify(input);
stage(input);assert.equal(JSON.stringify(input),before);
const original=JSON.stringify(provider);connection(provider);assert.equal(JSON.stringify(provider),original);
for(const value of [stage(accepted),stage({...accepted,execution_status:'Running'}),stage({...accepted,validation_status:'Failed'}),stage(null),stage({implemented:false}),stage(accepted,{dirty:true}),connection(provider)]) {
 assert.ok(['complete','working','attention','error','blocked','pending'].includes(value.kind));
 assert.ok(value.label.length);assert.ok(value.detail.length);assert.ok(value.symbol.length);
}
""")

    def test_fourteen_original_icons_have_distinct_geometry_and_safe_svg_attributes(self):
        self.run_client(r"""
const iconSandbox={svg:(tag,attributes={},...children)=>({tag,attributes,children:children.flat(Infinity)})};vm.createContext(iconSandbox);
const icons=fs.readFileSync('src/gui/icons.js','utf8').replace(/^import[^\n]*\n/gm,'').replace(/export /g,'');
vm.runInContext(icons+'\nthis.stageIcon=stageIcon;this.statusIcon=statusIcon;this.ids=Object.keys(STAGE_SHAPES);',iconSandbox);
assert.equal(iconSandbox.ids.length,14);
const geometry=new Set();
for(const id of iconSandbox.ids) {
 const icon=iconSandbox.stageIcon(id);assert.equal(icon.tag,'svg');assert.equal(icon.attributes.viewBox,'0 0 24 24');
 assert.equal(icon.attributes['aria-hidden'],'true');assert.equal(icon.attributes.focusable,'false');assert.equal(icon.attributes.stroke,'currentColor');
 assert.equal(icon.attributes['stroke-width'],2);assert.equal(icon.attributes['data-icon'],id);
 assert.ok(icon.children.length>0);assert.ok(icon.children.every(child=>['path','rect','circle'].includes(child.tag)));
 geometry.add(JSON.stringify(icon.children));
}
assert.equal(geometry.size,14);
assert.equal(iconSandbox.stageIcon('layout',{class:'custom'}).attributes.class,'custom');
for(const kind of ['complete','working','attention','error','blocked','pending']) assert.ok(iconSandbox.statusIcon(kind).children.length>0);
assert.ok(iconSandbox.stageIcon('unknown').children.length>0);
""")


if __name__ == '__main__':
    unittest.main()
