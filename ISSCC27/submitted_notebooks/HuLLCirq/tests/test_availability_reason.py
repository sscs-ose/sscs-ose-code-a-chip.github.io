"""Read-only reason labels; no LLM, EDA, project mutation, or network calls."""
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const sandbox={};vm.createContext(sandbox);
vm.runInContext(fs.readFileSync('src/gui/availability.js','utf8').replace(/export /g,'')+'\nthis.classify=availabilityReason;',sandbox);
const classify=sandbox.classify;
"""


class AvailabilityReasonTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated GUI checks.')
        result = subprocess.run([node, '-e', CLIENT + '\n' + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_explicit_implementation_is_not_an_input_request(self):
        self.run_client(r"""
const value=classify({kind:'implementation_required',message:'S05 synthesis is accepted. Checker implementation is needed.'});
assert.equal(value.kind,'implementation');assert.equal(value.label,'Not implemented');
assert.match(value.message,/S05 synthesis is accepted/);
""")

    def test_missing_contract_does_not_falsely_deny_saved_requirements(self):
        self.run_client(r"""
for(const value of [
 classify({code:'verification_contract_missing',message:'The original design has no structured behavioral verification contract.'}),
 classify('The original design has no structured behavioral verification contract.'),
]) {
 assert.equal(value.label,'Not implemented');
 assert.match(value.message,/does not mean the saved test requirements are absent/);
 assert.doesNotMatch(value.message,/design has no/);
}
""")

    def test_machine_kind_overrides_legacy_text_and_code(self):
        self.run_client(r"""
const value=classify({kind:'input_required',code:'verification_contract_missing',message:'The original design has no structured behavioral verification contract.'});
assert.equal(value.label,'Input required');
assert.equal(classify({readiness:{status:'configuration_required',message:'Simulator path required.'},message:'unsupported checker'}).kind,'configuration');
""")

    def test_s04_s05_prerequisites_are_named_and_preserved(self):
        self.run_client(r"""
for(const kind of ['candidate_required','synthesis_required']) {
 const value=classify({kind,message:'The same RTL needs a current accepted S05 netlist.'});
 assert.equal(value.label,'Prerequisites missing');assert.match(value.message,/accepted S05/);
}
assert.equal(classify('Current accepted S04 RTL is required.').kind,'prerequisite');
assert.equal(classify('The same RTL needs a current accepted S05 netlist.').kind,'prerequisite');
assert.equal(classify('Adopt current S08 and all six node sources before physical design.').label,'Prerequisites missing');
""")

    def test_tool_support_errors_are_not_checker_implementation(self):
        self.run_client(r"""
for(const code of ['compiler_unavailable','unsupported_compiler','invalid_simulator','unsupported_synthesizer'])
 assert.equal(classify({code,status:'Unsupported'}).label,'Tool setup required');
assert.equal(classify({code:'unsupported_verification_template'}).label,'Not implemented');
assert.equal(classify({code:'unsupported_language'}).label,'Input required');
""")

    def test_context_budget_keeps_actual_numbers_and_action(self):
        self.run_client(r"""
const message='Estimated input 13,097 + output 3,000 exceeds context window 16,384.';
const value=classify({code:'context_budget',message});
assert.equal(value.label,'Input required');assert.equal(value.message,message);
assert.equal(value.actionLabel,'Inspect required input');
assert.equal(classify(message).kind,'input');
""")

    def test_repeated_guidance_requests_instruction_revision(self):
        self.run_client(r"""
const message='The same repair plan left the problem unresolved. Revise the correction before another request.';
assert.equal(classify(message).label,'Input required');
assert.equal(classify({code:'repair_reconsideration_required',message}).message,message);
""")

    def test_actual_saved_plan_missing_concrete_repair_guidance(self):
        self.run_client(r"""
const raw={status:'Blocked',reason:'No supported concrete repair method. Analyze the saved failure, review the proposed changes, then prepare a new repair preview.'};
const before=JSON.stringify(raw),value=classify(raw);
assert.equal(value.kind,'input');assert.equal(value.label,'Input required');
assert.match(value.message,/No concrete repair instruction is prepared for this diagnostic/);
assert.match(value.message,/Enter a correction in Additional instruction, or prepare an analysis and review/);
assert.equal(value.actionLabel,'Add or review repair instructions');
assert.doesNotMatch(value.message,/unsupported|not implemented|No supported concrete repair method/i);
assert.equal(JSON.stringify(raw),before);
for(const code of ['repair_guidance_missing','missing_repair_guidance','concrete_repair_guidance_required','concrete_repair_instruction_required','repair_instruction_required','repair_analysis_required']) {
 const structured=classify({code});assert.equal(structured.kind,'input');
 assert.match(structured.message,/Enter a correction/);
}
""")

    def test_connection_reason_remains_distinct(self):
        self.run_client(r"""
assert.equal(classify({kind:'connection_required',message:'The model service is offline.'}).label,'Connection required');
assert.equal(classify('Connection refused by the model service.').kind,'connection');
""")

    def test_unknown_is_not_a_guessed_cause(self):
        self.run_client(r"""
const message='The operation cannot start because saved record xyz is inconsistent.';
assert.equal(classify({code:'unrecognized_error',message}).kind,'unknown');
assert.equal(classify({code:'unrecognized_error',message}).message,message);
assert.equal(classify({status:'Blocked'}).label,'Reason unavailable');
assert.doesNotMatch(classify('Blocked').message,/Blocked/);
""")

    def test_nested_readiness_reason_and_diagnostics(self):
        self.run_client(r"""
assert.equal(classify({readiness:{status:'implementation_required',message:'Checker missing.'}}).message,'Checker missing.');
assert.equal(classify({reason:{kind:'synthesis_required',message:'Adopt S05 first.'}}).label,'Prerequisites missing');
assert.equal(classify({diagnostics:[{code:'simulator_unavailable',message:'Icarus is not configured.'}]}).label,'Tool setup required');
""")

    def test_nested_source_diagnostic_keeps_specific_checker_limitation(self):
        self.run_client(r"""
const message='Only int8_mac_stream version 1 is supported.';
const value=classify({kind:'implementation_required',message:'S06 needs a behavioral checker.',readiness:{status:'implementation_required',code:'verification_implementation_required',source_diagnostic:{code:'unsupported_verification_contract',message}}});
assert.equal(value.label,'Not implemented');assert.equal(value.message,message);
const sourceOnly=classify({readiness:{source_diagnostic:{code:'unsupported_verification_template',message:'Unsupported scheduler testbench template.'}}});
assert.equal(sourceOnly.label,'Not implemented');assert.match(sourceOnly.message,/scheduler/);
const legacy=classify({kind:'implementation_required',message:'The saved requirements exist; this checker needs implementation.',readiness:{source_diagnostic:{code:'verification_contract_missing',message:'The original design has no structured behavioral verification contract.'}}});
assert.match(legacy.message,/saved requirements exist/);assert.doesNotMatch(legacy.message,/design has no/);
""")

    def test_current_stage_capability_and_source_requirements(self):
        self.run_client(r"""
assert.equal(classify({kind:'stage_unimplemented'}).label,'Not implemented');
assert.equal(classify('S08 currently integrates the six declared NPU node types.').label,'Not implemented');
for(const message of ['All six exact adopted node sources must remain current.','Adopt the latest current S11 layout before continuing.','Waiting for current accepted S05 synthesis.','No current failed S05 result matches the latest RTL candidate.']) {
 assert.equal(classify(message).label,'Prerequisites missing');
}
for(const kind of ['active_operation'])assert.equal(classify({kind}).label,'Prerequisites missing');
for(const kind of ['unsaved','unsaved_changes','source_conflict','conflict'])assert.equal(classify({kind}).label,'Input required');
""")

    def test_profile_and_save_preflight_reasons(self):
        self.run_client(r"""
for(const message of ['Save an LLM provider profile in Global Settings.','Save the edited provider settings in Global Settings first.'])
 assert.equal(classify(message).label,'Tool setup required');
assert.equal(classify('Save or reopen the current design first.').label,'Input required');
""")

    def test_does_not_mutate_input_records(self):
        self.run_client(r"""
const value={status:'Blocked',readiness:{status:'implementation_required'},diagnostics:[{code:'verification_contract_missing'}]};
const before=JSON.stringify(value);classify(value);assert.equal(JSON.stringify(value),before);
for(const empty of [null,undefined,7,{},[]])assert.equal(classify(empty).kind,'unknown');
""")


if __name__ == '__main__':
    unittest.main()
