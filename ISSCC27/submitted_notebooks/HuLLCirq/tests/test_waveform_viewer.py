"""Pure waveform parser/model QA; no model, simulator or live browser."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT=Path(__file__).resolve().parents[1]
CLIENT=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const s=fs.readFileSync('src/gui/waveform_viewer.js','utf8').replace(/^import[^\n]*\n/gm,'').replaceAll('export ','');
const c={console};vm.createContext(c);vm.runInContext(s+'\nglobalThis.parseVCD=parseVCD;globalThis.waveformModel=waveformModel;',c);
const vcd='$timescale 1ps $end\n$scope module tb $end\n$var reg 1 ! clk $end\n$var wire 64 " data $end\n$enddefinitions $end\n#0\n$dumpvars\n0!\nbx "\n$end\n#25000\n1!\nb100000000000000000000000000000000000000000000000000001 "\n#50000\n0!\nbz "\n';
const data={interface:{clock:{port:'clock'},reset:{port:'reset',active:'high'},ports:[{name:'clock',direction:'input',width:1},{name:'reset',direction:'input',width:1},{name:'value',direction:'input',width:64},{name:'out',direction:'output',width:64}]},timing:{period_ps:50000,half_period_ps:25000,sample_after_rising_ps:1000},vectors:[{reset:1,drive:{value:'9007199254740993'},expect:{out:'9007199254740993'}},{reset:0,drive:{value:'2'},expect:{out:'2'}}],samples:[{cycle:0,signal:'out',value:'9007199254740993'},{cycle:1,signal:'out',value:'3'}]};
'''

class WaveformTests(unittest.TestCase):
    def check(self,body):
        node=shutil.which('node')
        if not node:self.skipTest('Node required')
        r=subprocess.run([node,'-e',CLIENT+body],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

    def test_vcd_timescale_unknowns_and_wide_values_are_lossless(self):
        self.check("const m=c.parseVCD(vcd);assert.equal(m.end,50);assert.equal(m.signals[1].events[0].value,'X');assert.equal(m.signals[1].events[1].value,'9007199254740993');assert.equal(m.signals[1].events[2].value,'Z');")

    def test_samples_do_not_become_invented_continuous_transitions_or_goldens(self):
        self.check("const m=c.waveformModel(data),r=m.rows.find(r=>r.kind==='Observed samples');assert.equal(r.sampled,true);assert.equal(r.events[0].time,26);assert.equal(r.events[0].value,'9007199254740993');assert.equal(m.mismatches.length,1);assert.equal(m.mismatches[0].cycle,1);assert.equal(m.mismatches[0].actual,'3');assert.equal(m.mismatches[0].expected,'2');assert.equal(m.rows[0].kind,'Saved stimulus');")

    def test_missing_observation_is_never_filled_from_expected(self):
        self.check("data.samples=[];const m=c.waveformModel(data);assert.equal(m.rows.find(r=>r.kind==='Observed samples').events.length,0);assert.equal(m.rows.find(r=>r.kind==='Saved expected samples').events.length,2);")

    def test_vcd_and_expected_rows_coexist_without_replacing_vcd(self):
        self.check("data.vcd=vcd;const m=c.waveformModel(data);assert.equal(m.rows[0].kind,'VCD observed');assert.ok(m.rows.some(r=>r.kind==='Saved expected samples'));assert.ok(!m.rows.some(r=>r.kind==='Observed samples'));")

    def test_bad_scale_timestamp_width_or_value_are_rejected(self):
        self.check("for(const bad of [vcd.replace('1ps','2ps'),vcd+'#1\\n',vcd.replace('64','0'),vcd+'r1.2 !\\n',vcd.replace('b0','b2')]){if(bad===vcd)continue;assert.throws(()=>c.parseVCD(bad));}")

    def test_signed_comparison_uses_declared_width_not_js_number(self):
        self.check("data.interface.ports.at(-1).width=4;data.vectors[0].expect.out='-1';data.samples[0].value='15';data.samples.pop();const m=c.waveformModel(data);assert.equal(m.rows.find(r=>r.kind==='Saved expected samples').events[0].value,'15');assert.equal(m.mismatches.length,0);")

    def test_vcd_comparison_uses_observed_transitions_instead_of_report_or_expected(self):
        self.check("data.vcd='$timescale 1ps $end\\n$var wire 64 ! hc_p3 $end\\n$enddefinitions $end\\n#0\\nb0 !\\n#25000\\nb10 !\\n#100000\\n';const m=c.waveformModel(data);assert.equal(m.comparisons,2);assert.equal(m.mismatches.length,1);assert.equal(m.mismatches[0].actual,'2');assert.equal(m.mismatches[0].expected,'9007199254740993');")

    def test_mixed_unknown_bus_is_preserved_and_counted_as_mismatch(self):
        self.check("data.vcd='$timescale 1ps $end\\n$var wire 64 ! hc_p3 $end\\n$enddefinitions $end\\n#0\\nb10x1 !\\n#100000\\n';const m=c.waveformModel(data);assert.equal(m.comparisons,2);assert.equal(m.mismatches[0].actual,'10X1');")

    def test_short_vcd_does_not_invent_later_observations(self):
        self.check("data.vcd='$timescale 1ps $end\\n$var wire 64 ! hc_p3 $end\\n$enddefinitions $end\\n#0\\nb10 !\\n#30000\\n';const m=c.waveformModel(data);assert.equal(m.comparisons,1);assert.equal(m.missing,1);assert.equal(m.rows[0].end,30);assert.equal(m.end,100);")

    def test_inspection_requests_never_update_execution_adoption_ledger(self):
        self.check(r'''const app=fs.readFileSync('src/gui/app.js','utf8');
const api=app.slice(app.indexOf('async function api('),app.indexOf('\nfunction executionReadFailure('));
let received=0;
Object.assign(c,{reviewOperator:{request:(p,b)=>b},executionAction:()=>null,executionScope:()=>'scope',
 state:{envelope:{revision:{id:'r'}},design:null},executionState:{scopeKey:'scope',setScope:()=>{},receive:()=>received++},
 AbortSignal,sessionFetch:async()=>({ok:true,json:async()=>({run_id:'original',stage:'local_netlist_simulation',execution_status:'Completed',validation_status:'Passed'})}),
 byId:()=>({classList:{remove:()=>{}}})});
vm.runInContext(api,c);
(async()=>{for(const p of ['inspection/waveform/workflow/original','inspection/files','inspection/files/opaque'])await c.api(p);
assert.equal(received,0,'Saved inspections must not overwrite accepted progress');await c.api('workflow');assert.equal(received,1,'Normal execution observation must still update progress');})().catch(e=>{console.error(e);process.exitCode=1;});''')
