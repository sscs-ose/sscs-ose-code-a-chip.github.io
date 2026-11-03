"""Saved RTL actions and truthful evidence display; isolated software fixtures only."""
from pathlib import Path
import shutil
import subprocess
import unittest

from test_generation_recovery_gui import CLIENT

PROJECT = Path(__file__).resolve().parents[1]
SAVED_CANDIDATE = r"""
failed.execution_status='Completed';failed.validation_status='Passed';failed.error=null;
failed.rtl='module qa_control; endmodule';failed.raw_content='QA preserved original answer';
failed.checks={interface:{validation_status:'Passed'},syntax:{validation_status:'Passed',executed:true,exit_code:0},behavioral:{validation_status:'Not Run',executed:false}};
failed.verification_plan_error={code:'verification_contract_missing',message:'Historical contract was missing'};
failed.saved_rtl_verification={available:true,message:'Verification supported for the current source'};
project.envelope.review_policy={mode:'accept_on_pass',user_authorized:true};
workspace.render(host);
"""


class SavedRtlVerificationGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated client checks.")
        result = subprocess.run(
            [node, "-e", CLIENT + "\n" + SAVED_CANDIDATE +
             "\n(async()=>{\n" + body +
             "\nconsole.log('Passed: saved RTL verification GUI');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
            cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_s04_pass_is_external_interface_only_and_legacy_checks_stay_intact(self):
        self.run_client(r"""
const before=JSON.stringify(failed);
assert.equal(workspace.validationLabel(failed),'Passed');
assert.match(text(test('generation-job-status')),/Passed/);
assert.match(text(test('generation-check-summary')),/External interface: Passed.*Synthesis: S05.*Circuit behavior: S06/);
assert.equal(test('generation-behavioral-not-run'),null);assert.equal(test('verify-saved-rtl'),null);
workspace.artifactTab='checks';workspace.renderResult();
assert.match(text(test('candidate-checks')),/behavioral.*Not Run/s);
assert.equal(JSON.stringify(failed),before);assert.equal(requests.length,0);
const stageHost=new DOMDouble('div');
Object.assign(sandbox,{state:{stage:'local_rtl_generation'},generation:workspace,byId:()=>stageHost,dirty:()=>false,workflowStage:()=>null,statusIcon:()=>new DOMDouble('span')});
const app=fs.readFileSync('src/gui/app.js','utf8');
installStatusPresentation(app);
vm.runInContext(app.slice(app.indexOf('function renderStageStatus()'),app.indexOf('\nfunction render()'))+'\nrenderStageStatus();',sandbox);
assert.match(text(stageHost),/VALIDATION\s+Passed/);
""")

    def test_unsupported_behavior_checker_does_not_block_interface_adoption(self):
        self.run_client(r"""
failed.saved_rtl_verification={available:false,code:'unsupported_node',message:'Old behavioral checker missing'};
failed.behavioral_verification={status:'implementation_required',available:false};
workspace.renderResult();const review=new DOMDouble('div');workspace.renderReview(review);
assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,false);
assert.equal(test('verify-saved-rtl'),null);assert.equal(requests.length,0);
""")

    def test_s04_adoption_needs_no_llm_connection_or_compiler_evidence(self):
        self.run_client(r"""
workspace.llm={profile:null,profile_revision_id:null,probe:null};workspace.profileDraft.name='Unsaved unrelated profile';
failed.checks.syntax={validation_status:'Not Run',executed:false};
failed.checks.behavioral={validation_status:'Not Run',executed:false};
const review=new DOMDouble('div');workspace.renderReview(review);
assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,false);
assert.match(text(review),/S04 acceptance does not verify circuit behavior; S06/);
assert.equal(requests.length,0);
""")

    def test_review_still_blocks_dirty_stale_readonly_nonlatest_or_active_records(self):
        self.run_client(r"""
const changes=[()=>project.dirty=true,()=>project.conflict='changed',()=>workspace.requestBusy=true,
()=>project.envelope.workspace_identity.read_only=true,()=>failed.freshness='Stale',()=>failed.rtl='',
()=>project.envelope.workflow[0].review_status='Awaiting Review',()=>workspace.generation.nodes[0].latest_job_id='newer',
()=>failed.execution_status='Running'];
for(const change of changes){
 project.dirty=false;project.conflict=null;workspace.requestBusy=false;project.envelope.workspace_identity.read_only=false;
 project.envelope.workflow[0].review_status='Accepted';workspace.generation.nodes[0].latest_job_id=failed.id;
 failed.freshness='Current';failed.rtl='module qa_control; endmodule';failed.execution_status='Completed';
 change();const review=new DOMDouble('div');workspace.renderReview(review);
 assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,true);
}
assert.equal(requests.length,0);
""")

    def test_historical_behavior_failure_is_preserved_without_s04_block(self):
        self.run_client(r"""
failed.validation_status='Failed';failed.checks.behavioral={validation_status:'Failed',executed:true,exit_code:1};
failed.diagnostics=[{severity:'error',code:'old_behavior_failure',message:'Historical failed check'}];
const before=JSON.stringify(failed);workspace.artifactTab='checks';workspace.renderResult();
assert.equal(workspace.validationLabel(failed),'Passed');
assert.match(text(test('generation-diagnostics')),/old_behavior_failure/);
assert.match(text(test('candidate-checks')),/Failed/);assert.equal(JSON.stringify(failed),before);
const review=new DOMDouble('div');workspace.renderReview(review);
assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,false);
assert.equal(requests.length,0);
""")

    def test_interface_failure_blocks_s04_even_when_old_other_checks_passed(self):
        self.run_client(r"""
failed.checks.interface.validation_status='Failed';failed.checks.behavioral={validation_status:'Passed',executed:true};
workspace.renderResult();const review=new DOMDouble('div');workspace.renderReview(review);
assert.equal(workspace.validationLabel(failed),'Failed');
assert.equal(review.querySelector('[data-testid="accept-candidate"]').disabled,true);
assert.match(text(test('generation-check-summary')),/External interface: Failed/);assert.equal(requests.length,0);
""")

    def test_old_verified_job_lineage_and_raw_answer_remain_readable(self):
        self.run_client(r"""
failed.operation='verify';failed.verification_of_job_id='original';failed.review_status='Accepted';
workspace.generation.all_nodes_accepted=false;workspace.renderResult();
assert.match(text(test('generation-verification-lineage')),/Saved RTL verification of original.*No model request/);
workspace.artifactTab='raw';workspace.renderResult();assert.match(text(host.querySelector('#generation-result-content')),/Preserved original model answer/);
const review=new DOMDouble('div');workspace.renderReview(review);
assert.match(text(review),/Other project nodes remain incomplete/);assert.equal(requests.length,0);
""")


if __name__ == "__main__":
    unittest.main()
