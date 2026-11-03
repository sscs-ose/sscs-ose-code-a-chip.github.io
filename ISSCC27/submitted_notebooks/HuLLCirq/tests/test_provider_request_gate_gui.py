"""Known-negative model discovery and pending-test guards; no live requests."""
import shutil
import subprocess
import unittest

from test_generation_batch_gui import CLIENT, SETUP, PROJECT
from test_local_runtime_gui import CLIENT as RUNTIME_CLIENT

GUARDS = r"""
batchUI.callbacks.providerGate=()=>workspace.providerRequestGate();
const globalSource=fs.readFileSync('src/gui/global_generation.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class GlobalGeneration','class GlobalGeneration');
vm.runInContext('{'+globalSource+'\nglobalThis.GlobalGeneration=GlobalGeneration;}',sandbox);
const globalUI=new sandbox.GlobalGeneration({project:()=>project,request:(...args)=>{requests.push(args);return responder(...args);},providerGate:()=>workspace.providerRequestGate(),notify:message=>notices.push(message),toast(){},envelope(){}});
globalUI.data={ready:true,jobs:[],reviews:[]};globalUI.preview={context_id:'global-preview'};
workspace.preview={revision_id:'revision-a',node_id:'node-a',profile_revision_id:'profile-a',context_id:'single-preview',estimated_input_tokens:100};workspace.previewStale=false;
batchUI.plan=plan;batchUI.planSource=batchUI.sourceIdentity();batchUI.refresh();
"""


class ProviderRequestGateTests(unittest.TestCase):
    def client(self, body, prefix=CLIENT + SETUP + GUARDS):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated provider-request fixtures.')
        result = subprocess.run([node, '-e', prefix + '\n(async()=>{\n' + body +
                                 '\n})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_known_current_model_unavailable_blocks_single_batch_analysis_and_s08(self):
        self.client(r"""
workspace.llm.probe={profile_revision_id:'profile-a',selected_model_available:false,status:'Failed',error:{code:'model_unavailable'}};
responder=()=>assert.fail('Known missing model must not send a new request');
assert.match(workspace.providerRequestGate(),/selected model is unavailable/);assert.match(workspace.generationGate(),/selected model is unavailable/);assert.match(batchUI.startGate(),/selected model is unavailable/);assert.match(globalUI.gate(),/selected model is unavailable/);
assert.equal(workspace.verificationGate({...failed,rtl:'SOFTWARE QA ONLY',saved_rtl_verification:{available:true}}),'','Model discovery must not block a supported saved-RTL check that sends no model request');
await workspace.startGeneration();await batchUI.start();batchUI.analysisPreview={ready_to_start:true};await batchUI.startAnalysis();await globalUI.start();await globalUI.prepare();
assert.equal(requests.length,0);assert.equal(workspace.preview.context_id,'single-preview');assert.equal(batchUI.plan.plan_id,'plan-a');
""")

    def test_untested_stale_or_other_connection_failure_adds_no_new_probe_requirement(self):
        self.client(r"""
for(const probe of [null,{profile_revision_id:'earlier-profile',selected_model_available:false,status:'Failed'},{profile_revision_id:'profile-a',selected_model_available:true,status:'Connected'},{profile_revision_id:'profile-a',status:'Failed',error:{code:'connection_refused'}},{selected_model_available:false}]){
 workspace.llm.probe=probe;assert.equal(workspace.providerRequestGate(),'');assert.equal(workspace.generationGate(),'');assert.equal(batchUI.gate(),'');assert.equal(globalUI.gate(),'');
}
assert.equal(requests.length,0);
""")

    def test_pending_explicit_probe_disables_batch_and_single_then_current_success_releases(self):
        self.client(r"""
const wait=deferred(),updates=[];workspace.callbacks.batch=()=>batchUI;workspace.callbacks.providerStateChanged=()=>updates.push(workspace.profileBusy);
responder=(route,body)=>{assert.equal(route,'llm/probe');assert.equal(body.profile_revision_id,'profile-a');return wait.promise;};
const pending=workspace.probe();assert.equal(workspace.profileBusy,true);assert.match(workspace.providerRequestGate(),/connection test to finish/);assert.match(batchUI.startGate(),/connection test to finish/);assert.match(globalUI.gate(),/connection test to finish/);assert.equal(batchTest('generation-batch-start').disabled,true);assert.ok(updates.includes(true));
await workspace.startGeneration();await batchUI.start();await globalUI.start();assert.equal(requests.length,1);
wait.resolve({llm:{...workspace.llm,probe:{profile_revision_id:'profile-a',selected_model_available:true,status:'Connected'}}});await pending;
assert.equal(workspace.profileBusy,false);assert.equal(workspace.providerRequestGate(),'');assert.equal(batchTest('generation-batch-start').disabled,false);assert.ok(updates.includes(false));assert.equal(requests.length,1);
""")

    def test_delayed_probe_from_other_project_drops_response_and_error(self):
        self.client(r"""
for(const reject of [false,true]){
 const wait=deferred();responder=()=>wait.promise;const previous=adopted.length,noticeCount=notices.length,pending=workspace.probe();
 project.envelope.workspace_identity={...project.envelope.workspace_identity,session_id:reject?'new-session-c':'new-session-b'};
 workspace.receive({llm:{...workspace.llm,probe:null}});
 if(reject)wait.reject(Error('OLD_CONTEXT_ERROR'));else wait.resolve({llm:{...workspace.llm,probe:{profile_revision_id:'profile-a',selected_model_available:false,status:'Failed'}}});
 await pending;assert.equal(adopted.length,previous);assert.equal(notices.length,noticeCount);assert.equal(workspace.llm.probe,null);assert.equal(workspace.profileBusy,false);
}
""")

    def test_delayed_probe_for_changed_profile_does_not_replace_current_probe(self):
        self.client(r"""
const wait=deferred();responder=()=>wait.promise;const pending=workspace.probe();workspace.llm={...workspace.llm,profile_revision_id:'profile-new',probe:null};
wait.resolve({llm:{...workspace.llm,profile_revision_id:'profile-a',probe:{profile_revision_id:'profile-a',selected_model_available:false,status:'Failed'}}});await pending;
assert.equal(adopted.length,0);assert.equal(workspace.llm.profile_revision_id,'profile-new');assert.equal(workspace.llm.probe,null);assert.equal(workspace.providerRequestGate(),'');
""")

    def test_local_server_help_does_not_claim_supported_model_names_are_installed(self):
        self.client(r"""
const host=mount();await tick();assert.match(text(host),/does not establish that either model is installed/);assert.match(text(host),/actual model list/);assert.doesNotMatch(text(host),/Start the prepared qwen3/);
assert.equal(requests.length,1);assert.equal(requests[0][0],'workspace/local-runtime');assert.equal(workspace.llm.probe,null);
""", prefix=RUNTIME_CLIENT)

    def test_real_application_wires_same_provider_guard_for_batch_and_global(self):
        self.client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8');assert.equal((app.match(/providerGate: \(\) => executionSubmissions\?\.gate\(\) \|\| generation.providerRequestGate\(\)/g)||[]).length,2);assert.match(app,/providerStateChanged: \(\) => \{ globalGeneration.refresh\(\); syncChrome\(\); \}/);assert.equal(requests.length,0);
""")

    def test_s07_scope_is_project_neutral_without_expanding_claims(self):
        self.client(r"""
const source=fs.readFileSync('src/gui/implementation_specs.js','utf8');assert.match(source,/does not establish whole-system behavior or physical timing/);assert.doesNotMatch(source,/full NPU|full-NPU/);assert.match(source,/Finite-cycle, zero-delay generic-netlist evidence only/);assert.equal(requests.length,0);
""")


if __name__ == '__main__':
    unittest.main()
