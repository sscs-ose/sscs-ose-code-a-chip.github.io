"""Actual shared GUI module in isolated Node; no browser/network/EDA."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]

CLIENT = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const code=fs.readFileSync('src/gui/review_operator.js','utf8').replace(/^import .*;\r?$/mg,'').replace(/export /g,'');
const sandbox={el(){},field:(...args)=>args};vm.createContext(sandbox);
vm.runInContext(code+'\nglobalThis.operator=new ReviewOperator();globalThis.version=REVIEW_ACTOR_VERSION;globalThis.label=reviewActorLabel;globalThis.provenance=adoptionProvenance;',sandbox);
const op=sandbox.operator,version=sandbox.version;
'''


class ReviewOperatorGuiTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node: self.skipTest('Node is needed for isolated GUI checks.')
        result = subprocess.run([node, '-e', CLIENT + body], cwd=PROJECT, capture_output=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_all_ten_review_routes_require_selection_and_keep_original_payload(self):
        self.run_client(r'''
const routes=['review','generation/review','workflow/review','implementation-specs/review','global-generation/review',...['global','physical','drc','lvs','postlayout'].map(x=>x+'-workflow/runs/id/review')];
for(const route of routes){op.reset();const original={decision:'accepted',note:'fixture'};assert.throws(()=>op.request(route,original,version),/Select Human/);op.actor='development_assistant';const sent=op.request(route,original,version);assert.equal(sent.review_operator.actor,'development_assistant');assert.equal(original.review_operator,undefined);assert.equal(sent.note,'fixture');}
''')

    def test_selection_and_reset_are_browser_memory_only(self):
        self.run_client(r'''
let rendered;const host={replaceChildren:field=>rendered=field};op.render(host);assert.equal(rendered[0],'Review operator');assert.equal(rendered[1],'');rendered[2]('human');assert.equal(op.request('review',{},version).review_operator.actor,'human');op.reset();assert.equal(rendered[1],'');assert.throws(()=>op.request('review',{},version),/Select Human/);
''')

    def test_old_service_is_blocked_and_nonreview_requests_unchanged(self):
        self.run_client(r'''
op.actor='development_assistant';assert.throws(()=>op.request('review',{},undefined),/service does not support/);for(const path of ['review-policy','generation/start','physical-workflow/runs','workspace/open','lvs-workflow/repair-profile','postlayout-workflow/runs/id/verify-cleanup']){const body={fixture:true};assert.equal(op.request(path,body,version),body);}assert.equal(op.request('review',undefined,version),undefined);
''')

    def test_labels_never_promote_legacy_human_label_to_actual_person(self):
        self.run_client(r'''
assert.match(sandbox.label({actor:'human'}),/legacy.*unverified/);assert.match(sandbox.provenance({actor:'human'}),/retrospectively/);assert.match(sandbox.label({actor:'development_assistant',provenance:{version}}),/development assistant/);assert.match(sandbox.label({actor:'human',provenance:{version}}),/self-declared/);assert.match(sandbox.provenance({actor:'automation_policy',provenance:{policy_id:'fixture'}}),/authorized adoption policy fixture/);
''')

