"""Focused S07 request feedback checks, without browser, service or EDA calls."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync('src/gui/implementation_specs.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class NodeImplementationSpecs','class NodeImplementationSpecs');
const sandbox={};vm.createContext(sandbox);vm.runInContext(source+'\nthis.Workspace=NodeImplementationSpecs;',sandbox);
const notifications=[],calls=[],sourceRun={id:'saved-s06',validation_status:'Passed'};
const project={envelope:{revision:{id:'same-saved-revision'}}};
let failure;
const view=new sandbox.Workspace({project:()=>project,request:async(...args)=>{calls.push(args);throw failure;},notify:(...args)=>notifications.push(args)});
view.nodeId='control';view.gate=()=>'';view.source=()=>sourceRun;view.refresh=()=>{};
"""


class S07RequestFeedbackGuiTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node required for isolated client checks.')
        result = subprocess.run([node, '-e', CLIENT + body], cwd=PROJECT,
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_internal_error_identifies_s07_and_preserved_source_without_resending(self):
        self.client(r"""
(async()=>{
failure=Object.assign(new Error('The request could not be completed.'),{code:'internal_error',status:500});
await view.start();
assert.equal(calls.length,1);assert.equal(calls[0][0],'implementation-specs/start');
assert.match(notifications[0][0],/S07 extraction failed.*saved-s06.*preserved/);
assert.match(notifications[0][0],/Check saved specifications before retrying/);
assert.equal(notifications[0][1],'error');assert.equal(view.busy,false);
assert.equal(sourceRun.validation_status,'Passed');assert.equal(view.specId,null);
})().catch(e=>{console.error(e);process.exitCode=1});
""")

    def test_domain_error_keeps_its_actual_actionable_explanation(self):
        self.client(r"""
(async()=>{
failure=Object.assign(new Error('The source adoption is no longer current.'),{code:'source_not_adopted',status:409});
await view.start();assert.equal(calls.length,1);
assert.equal(notifications[0][0],failure.message);assert.equal(view.busy,false);
assert.equal(sourceRun.validation_status,'Passed');
})().catch(e=>{console.error(e);process.exitCode=1});
""")


if __name__ == '__main__':
    unittest.main()
