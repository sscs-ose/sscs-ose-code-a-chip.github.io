"""Isolated event-review DOM/API doubles; no live project or simulator."""
import unittest
import test_postlayout_workflow_gui as existing


class SavedEventDiagnosticClientTests(unittest.TestCase):
    run_client = existing.PostlayoutClientTests.run_client

    def test_event_scope_uses_saved_summary_without_previous_diagnostic_numbers(self):
        self.run_client(r"""
flow.data.verification_supported=false; flow.data.execution_scope='saved_event_diagnostic_review'; flow.refresh();
assert.equal(flow.diagnostic(),true); assert.equal(flow.eventDiagnostic(),true); assert.equal(flow.preflight(),false);
assert.equal(find('postlayout-workflow-run').textContent,'Validate saved event diagnostic');
const run=record(); run.execution_scope='saved_event_diagnostic_review'; run.validation_status='Unsupported';
run.checks={executed:true,execution_started_by_this_review:false,review_mode:run.execution_scope,
  summary:{software_qa_fixture:true,change_callbacks:17,conditional_paths:'SOFTWARE QA pending',native_diagnostics_note:'SOFTWARE QA exact saved native note'}};
install(run);
assert.equal(text(find('postlayout-workflow-native-diagnostics')),'SOFTWARE QA exact saved native note');
assert.match(text(find('postlayout-workflow-summary')),/"change_callbacks": 17/);
assert.match(text(find('postlayout-workflow-summary')),/SOFTWARE QA pending/);
assert.equal(text(find('postlayout-workflow-result')).includes('557,480'),false);
assert.equal(text(find('postlayout-workflow-native-diagnostics')).includes('1,991'),false);
delete run.checks.summary.native_diagnostics_note; flow.refresh();
assert.match(text(find('postlayout-workflow-native-diagnostics')),/conditional-path-report/);
assert.equal(text(find('postlayout-workflow-native-diagnostics')).includes('1,991'),false);
assert.match(text(find('postlayout-workflow-diagnostic-execution')),/"execution_started_by_this_review": false/);
""")

    def test_event_review_cannot_adopt_even_if_a_status_is_inconsistent(self):
        self.run_client(r"""
flow.data.execution_scope='saved_event_diagnostic_review'; flow.data.verification_supported=false;
const run=record(); run.execution_scope=flow.data.execution_scope; run.validation_status='Passed'; install(run);
project.envelope.review_policy={mode:'accept_on_pass',user_authorized:true};
const review=new DOMDouble('aside'); flow.renderReview(review);
assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
assert.equal(flow.pendingPolicy(),false); await flow.review(run,'accepted',''); assert.equal(requests.length,0);
assert.match(toasts.at(-1),/remain Unsupported/);
run.validation_status='Unsupported'; await flow.start(); assert.equal(requests.length,1);
assert.match(toasts.at(-1),/no new simulator process is launched/);
""")

    def test_all_eight_event_artifacts_are_downloadable_and_hash_verified(self):
        self.run_client(r"""
const run=record(); run.execution_scope='saved_event_diagnostic_review';
responseBytes=new TextEncoder().encode('SOFTWARE QA ONLY\t01xz\n');
const ids=['event-transcript','event-manifest','event-summary','event-audit-report','conditional-path-report','native-delay-readback','native-delay-manifest','functional-provenance'];
run.artifacts=ids.map(id=>({id,bytes:responseBytes.length,sha256:hash(responseBytes),content_type:'text/plain; charset=utf-8',url:`/api/artifacts/postlayout-workflow/${run.id}/${id}`}));
install(run); assert.equal(flow.artifacts(run).length,8);
for(const item of run.artifacts) {
  assert.ok(find('postlayout-workflow-download-'+item.id)); assert.ok(find('postlayout-workflow-view-'+item.id));
  await flow.viewFile(run,item); assert.match(flow.fileView.text,/SOFTWARE QA ONLY/);
}
assert.equal(flow.fileExtension(run,{id:'event-transcript'}),'tsv');
assert.equal(flow.fileExtension(run,{id:'native-delay-readback'}),'tsv');
const calls=fetches.length; await flow.viewFile(run,{...run.artifacts[0],url:'https://invalid.example/raw'}); assert.equal(fetches.length,calls);
await flow.viewFile(run,{...run.artifacts[0],sha256:'changed'}); assert.equal(flow.fileView,null); assert.match(notices.at(-1)[0],/hash and size/);
""")

    def test_historical_modes_do_not_inherit_the_current_event_description(self):
        self.run_client(r"""
flow.data.execution_scope='saved_event_diagnostic_review'; flow.data.verification_supported=false;
const old=record('old-software-qa'); old.execution_scope='saved_dynamic_diagnostic_review'; old.validation_status='Unsupported';
const event=record('event-software-qa'); event.execution_scope='saved_event_diagnostic_review'; event.validation_status='Unsupported';
event.checks.summary={native_diagnostics_note:'SOFTWARE QA event native note'};
flow.data.runs=[old,event]; flow.runId=old.id; flow.refresh();
assert.equal(find('postlayout-workflow-run').textContent,'Validate saved event diagnostic');
assert.match(text(find('postlayout-workflow-native-diagnostics')),/1,991 ignored TIMINGCHECK/);
flow.runId=event.id; flow.refresh(); assert.equal(text(find('postlayout-workflow-native-diagnostics')),'SOFTWARE QA event native note');
""")

    def test_global_settings_event_description_has_no_inherited_numeric_outcomes(self):
        self.run_client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8'), start=app.indexOf('function renderSettings(host) {'), end=app.indexOf('\nfunction conceptCard()',start);
const state={design:{settings:{},project:{name:'SOFTWARE QA ONLY'}},envelope:{postlayout_workflow:{implemented:true},lvs_workflow:{implemented:true}}};
const settingsContext={state,el,workspaceEnabled:false,field:()=>el('div'),badge:label=>el('span',{text:label}),section:(title,description,children)=>el('section',{},children),
  postlayoutFlow:{preflight:()=>false,diagnostic:()=>true,eventDiagnostic:()=>true},mutate(){},adoption:{render(){}},generation:{renderProvider(){}},conceptCard:()=>el('div')};
vm.createContext(settingsContext); vm.runInContext(app.slice(start,end)+'\nglobalThis.renderSettings=renderSettings;',settingsContext);
const settingsHost=new DOMDouble('main'); settingsContext.renderSettings(settingsHost);
const environment=text(settingsHost.querySelector('[data-testid="eda-settings-environment"]'));
assert.match(environment,/saved S14 event diagnostic API/); assert.match(environment,/starts no new simulator/);
assert.match(environment,/conditional-path, native-delay and functional provenance reports/);
assert.match(environment,/Dynamic S14 verification is not implemented by this adapter/);
assert.match(environment,/this diagnostic cannot complete S14/);
assert.equal(environment.includes('all 16 expected outputs'),false);
assert.equal(environment.includes('557,480'),false);
""")


if __name__ == '__main__': unittest.main()
