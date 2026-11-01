"""Isolated GUI fixtures; no circuit evidence, saved project or EDA execution."""
import unittest
import test_postlayout_workflow_gui as existing


class PostRouteCompletionClientTests(unittest.TestCase):
    run_client = existing.PostlayoutClientTests.run_client

    def test_method_and_completion_criteria_report_failed_checks_without_inventing_values(self):
        self.run_client(r"""
flow.data.execution_scope='post_route_functional_plus_sta'; flow.data.verification_supported=true; flow.refresh();
assert.equal(flow.postRoute(),true); assert.equal(flow.diagnostic(),false); assert.equal(flow.unsupported(),false);
assert.equal(find('postlayout-workflow-run').textContent,'Run post-layout verification');
assert.match(find('postlayout-workflow-intro').textContent,/Routed-netlist functional simulation \+ extracted STA/);
assert.match(find('postlayout-workflow-intro').textContent,/SDF delay simulation is not part of this method/);
assert.equal(text(find('postlayout-workflow-lineage')).includes('SDF SHA-256'),false);
const run=record(); run.execution_scope=flow.data.execution_scope; run.verification_supported=true;
run.checks.summary={method:'post_route_functional_plus_sta',functional_status:'Passed',sta_status:'Failed',
  completion_criteria:[{id:'electrical',label:'Electrical limits',status:'Failed',detail:'SOFTWARE QA: slew constraint failed'}],
  timing_summary:{corner_count:2,clock_period_ns:40,setup_violations:0,hold_violations:0,max_slew_violations:3},
  reason:'SOFTWARE QA: repair the reported electrical constraint'};
install(run);
assert.match(text(find('postlayout-workflow-completion-criteria')),/Electrical limits/);
assert.match(text(find('postlayout-workflow-completion-criteria')),/Failed/);
assert.match(text(find('postlayout-workflow-timing-summary')),/Max slew: 3/);
assert.match(text(find('postlayout-workflow-timing-summary')),/Max capacitance: Not reported/);
assert.match(text(find('postlayout-workflow-completion-reason')),/repair the reported electrical constraint/);
assert.equal(find('postlayout-workflow-summary').open,false);
const review=new DOMDouble('aside'); flow.renderReview(review);
assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
""")

    def test_actual_start_and_running_state_do_not_claim_an_intermediate_pass(self):
        self.run_client(r"""
flow.data.execution_scope='post_route_functional_plus_sta'; flow.data.verification_supported=true;
await flow.start(); assert.equal(requests.length,1);
assert.match(toasts.at(-1),/Started routed-netlist functional simulation and extracted STA/);
const run=record(); run.execution_scope=flow.data.execution_scope; run.execution_status='Running'; run.validation_status='Not Checked'; run.checks={}; install(run);
assert.match(text(find('postlayout-workflow-result')),/Running tools for routed-netlist functional simulation and extracted STA/);
assert.match(text(find('postlayout-workflow-completion')),/no intermediate pass is inferred/);
assert.equal(find('postlayout-workflow-cancel').disabled,false);
assert.equal(find('postlayout-workflow-run').disabled,true);
assert.match(text(find('postlayout-workflow-timing-summary')),/Setup violations: Not reported/);
""")

    def test_adoption_requires_pass_and_preserves_old_diagnostic_scope(self):
        self.run_client(r"""
flow.data.execution_scope='post_route_functional_plus_sta'; flow.data.verification_supported=true;
const old=record('software-qa-old'); old.execution_scope='saved_event_diagnostic_review'; old.verification_supported=false; old.validation_status='Unsupported';
const run=record('software-qa-completion'); run.execution_scope=flow.data.execution_scope; run.verification_supported=true; run.validation_status='Passed';
flow.data.runs=[old,run]; flow.data.latest_run_id=run.id; flow.runId=run.id;
project.envelope.review_policy={mode:'accept_on_pass',user_authorized:true}; flow.refresh();
assert.equal(flow.pendingPolicy(),true);
const review=new DOMDouble('aside'); flow.renderReview(review); assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,false);
run.freshness='Stale'; flow.renderReview(review); assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
run.freshness='Current'; run.review_status='Accepted'; flow.data.reviews=[{run_id:run.id,decision:'accepted',actor:'automation_policy',provenance:{policy_id:'software-qa-authorized'}}]; flow.renderReview(review);
assert.match(text(review.querySelector('[data-testid="postlayout-workflow-adoption-provenance"]')),/authorized policy software-qa-authorized/);
flow.runId=old.id; flow.refresh(); flow.renderReview(review);
assert.equal(flow.postRoute(old),false); assert.equal(find('postlayout-workflow-completion'),null);
assert.match(text(find('postlayout-workflow-scope')),/S14 remains Unsupported/);
assert.equal(review.querySelector('[data-testid="postlayout-workflow-accept"]').disabled,true);
await flow.review(old,'accepted',''); assert.equal(requests.length,0);
assert.equal(find('postlayout-workflow-run').textContent,'Run post-layout verification');
""")

    def test_new_fixed_artifacts_are_hash_checked_and_manifest_formats_are_preserved(self):
        self.run_client(r"""
const run=record(); run.execution_scope='post_route_functional_plus_sta';
responseBytes=new TextEncoder().encode('SOFTWARE QA ONLY\n');
const ids=['sta-report','sta-log','sta-input-manifest','sta-constraints','sta-parasitics','sta-liberty','completion-report','functional-testbench','functional-models','functional-report'];
run.artifacts=ids.map(id=>({id,bytes:responseBytes.length,sha256:hash(responseBytes),content_type:'text/plain; charset=utf-8',url:`/api/artifacts/postlayout-workflow/${run.id}/${id}`}));
install(run); assert.equal(flow.artifacts(run).length,10);
for(const item of run.artifacts) { assert.ok(find('postlayout-workflow-download-'+item.id)); await flow.viewFile(run,item); assert.match(flow.fileView.text,/SOFTWARE QA ONLY/); }
assert.equal(flow.fileExtension(run,{id:'sta-constraints'}),'sdc');
assert.equal(flow.fileExtension(run,{id:'sta-parasitics'}),'spef');
assert.equal(flow.fileExtension(run,{id:'sta-parasitics',content_type:'application/json'}),'json');
assert.equal(flow.fileExtension(run,{id:'functional-models',content_type:'application/json'}),'json');
const before=fetches.length; await flow.viewFile(run,{...run.artifacts[0],url:'/arbitrary-file'}); assert.equal(fetches.length,before);
await flow.viewFile(run,{...run.artifacts[0],sha256:'wrong'}); assert.equal(flow.fileView,null); assert.match(notices.at(-1)[0],/hash and size/);
""")

    def test_settings_describes_functional_and_sta_separately_from_delay_simulation(self):
        self.run_client(r"""
const app=fs.readFileSync('src/gui/app.js','utf8'), start=app.indexOf('function renderSettings(host) {'), end=app.indexOf('\nfunction conceptCard()',start);
const state={design:{settings:{},project:{name:'SOFTWARE QA ONLY'}},envelope:{postlayout_workflow:{implemented:true}}};
const settingsContext={state,el,workspaceEnabled:false,field:()=>el('div'),badge:label=>el('span',{text:label}),section:(title,description,children)=>el('section',{},children),
  postlayoutFlow:{postRoute:()=>true,preflight:()=>false,diagnostic:()=>false,eventDiagnostic:()=>false},mutate(){},adoption:{render(){}},generation:{renderProvider(){}},conceptCard:()=>el('div')};
vm.createContext(settingsContext); vm.runInContext(app.slice(start,end)+'\nglobalThis.renderSettings=renderSettings;',settingsContext);
const settingsHost=new DOMDouble('main'); settingsContext.renderSettings(settingsHost);
const environment=text(settingsHost.querySelector('[data-testid="eda-settings-environment"]'));
assert.match(environment,/functional \+ STA verification API/); assert.match(environment,/checks timing separately with extracted parasitics/);
assert.match(environment,/SDF delay simulation is outside this method/); assert.match(environment,/mandatory checks to pass/);
assert.equal(environment.includes('S14 remains Unsupported'),false);
""")


if __name__ == '__main__':
    unittest.main()
