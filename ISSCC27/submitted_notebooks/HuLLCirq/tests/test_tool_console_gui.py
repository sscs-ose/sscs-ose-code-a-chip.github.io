"""Complete saved console projection; isolated text fixtures, no tool execution."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('src/gui/workflow.js','utf8').replace(/^import[^\n]+\n/gm,'').replace('export class LocalWorkflow','class LocalWorkflow');
const sandbox={};vm.createContext(sandbox);vm.runInContext(source+'\nglobalThis.consoleEvidence=toolConsoleEvidence;',sandbox);
const evidence=sandbox.consoleEvidence;
"""


class ToolConsoleGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for focused console checks.')
        result = subprocess.run([node, '-e', CLIENT + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_long_stdout_and_stderr_are_complete_raw_text(self):
        self.client(r"""
const stdout='FIRST_STDOUT\n'+'<script>untrusted tool output</script>\n'.repeat(10000)+'FINAL_STDOUT';
const stderr='FIRST_STDERR\r\n'+'warning details\r\n'.repeat(10000)+'FINAL_STDERR';
const result=evidence({checks:{commands:[{command:['yosys','-Q','-p','read_verilog candidate.v; synth'],executed:true,status:'Completed',exit_code:1,stdout,stderr}]}});
assert.equal(result.stdout,stdout);assert.equal(result.stderr,stderr);
assert.ok(result.text.includes('[stdout]\n'+stdout));assert.ok(result.text.includes('[stderr]\n'+stderr));
assert.match(result.text,/FINAL_STDOUT/);assert.match(result.text,/FINAL_STDERR$/);
assert.ok(result.text.includes('<script>untrusted tool output</script>'));
assert.ok(!result.text.includes('\\r\\n')); // Real line breaks, not JSON-escaped strings.
""")

    def test_all_commands_include_version_outcome_and_metadata(self):
        self.client(r"""
const result=evidence({checks:{commands:[
 {command:['yosys','-V'],executed:true,status:'Completed',exit_code:0,elapsed_seconds:0.25,stdout:'Yosys full version\n',stderr:''},
 {command:['yosys','-p','check -assert'],executed:true,status:'Timeout',exit_code:-1,error:'Deadline reached',stdout:'partial exact output\n',stderr:'specific error\n'}
],stdout:'partial exact output\n',stderr:'specific error\n'}});
assert.match(result.text,/COMMAND 1\n\$ yosys -V/);assert.match(result.text,/Elapsed: 0.25 seconds/);
assert.match(result.text,/COMMAND 2\n\$ yosys -p "check -assert"/);assert.match(result.text,/Status: Timeout · exit code: -1 · executed: true/);
assert.match(result.text,/Command error: Deadline reached/);
assert.equal(result.stdout,'Yosys full version\npartial exact output\n');assert.equal(result.stderr,'specific error\n');
assert.equal(result.text.split('partial exact output').length-1,1);
""")

    def test_aggregate_fallback_and_additional_recorded_output_are_retained(self):
        self.client(r"""
const old=evidence({checks:{stdout:'old saved stdout\nFINAL_OLD',stderr:'old saved stderr'}});
assert.equal(old.stdout,'old saved stdout\nFINAL_OLD');assert.equal(old.stderr,'old saved stderr');
assert.ok(old.text.includes('[stdout]\nold saved stdout\nFINAL_OLD'));
const extra=evidence({checks:{commands:[{command:['tool'],stdout:'command output',stderr:''}],stdout:'different run output',stderr:'additional warning'}});
assert.ok(extra.text.includes('[Additional saved run stdout]\ndifferent run output'));
assert.ok(extra.text.includes('[Additional saved run stderr]\nadditional warning'));
assert.equal(extra.stdout,'command outputdifferent run output');assert.equal(extra.stderr,'additional warning');
""")

    def test_simulation_aggregate_copy_does_not_duplicate_compile_or_simulation(self):
        self.client(r"""
const run={checks:{commands:[{stdout:'version\n',stderr:''},{stdout:'compile\n',stderr:'compile warning\n'},{stdout:'simulate\nFINAL',stderr:'sim warning\n'}],stdout:'compile\nsimulate\nFINAL',stderr:'compile warning\nsim warning\n'}};
const result=evidence(run);
assert.equal(result.stdout,'version\ncompile\nsimulate\nFINAL');assert.equal(result.stderr,'compile warning\nsim warning\n');
assert.equal(result.text.split('FINAL').length-1,1);assert.equal(result.text.split('compile warning').length-1,1);
""")

    def test_projection_is_read_only_and_empty_output_is_explicit(self):
        self.client(r"""
const run={id:'saved-run',checks:{commands:[{command:['tool'],executed:false,status:'Unsupported',exit_code:null,stdout:'',stderr:'launch failed'}]}};
const before=JSON.stringify(run);const result=evidence(run);assert.equal(JSON.stringify(run),before);
assert.match(result.text,/exit code: Not recorded · executed: false/);assert.match(result.text,/\[stdout\]\n\(No output recorded\)/);
assert.equal(result.stdout,'');assert.equal(result.stderr,'launch failed');
assert.match(evidence({checks:{}}).text,/No tool commands or output/);
assert.match(evidence({checks:{commands:null}}).text,/No tool commands or output/);
""")


if __name__ == '__main__':
    unittest.main()
