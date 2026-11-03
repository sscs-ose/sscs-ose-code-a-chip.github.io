"""Generic cancellation presentation; isolated software scenarios, never circuit evidence."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT=Path(__file__).resolve().parents[1]
CLIENT=r"""
// Isolated presentation scenarios. No network, browser, project, model or EDA calls.
const fs=require('node:fs'), vm=require('node:vm'), assert=require('node:assert/strict');
const sourcePath='src/gui/flow_guidance.js', results=[], sandbox={};let decisions=0;
vm.createContext(sandbox);
vm.runInContext('{'+fs.readFileSync('src/gui/availability.js','utf8').replace(/export /g,'')+'\nglobalThis.availabilityReason=availabilityReason;}',sandbox);
vm.runInContext(fs.readFileSync(sourcePath,'utf8').replace(/^import[^\n]+\n/gm,'').replace(/export /g,'')+'\nglobalThis.resolve=resolveStageGuidance;globalThis.decisions=GUIDANCE_DECISIONS;',sandbox);
const stages=sandbox.FLOW_STAGES || ['local_rtl_generation','local_synthesis','local_netlist_simulation','node_implementation_specs','global_rtl_generation','global_synthesis','global_netlist_simulation','layout','drc','lvs','post_layout_verification'];
const cancelled={id:'software-qa',execution_status:'Cancelled',validation_status:'Not Checked',review_status:'Awaiting Review',freshness:'Current',checks:{cleanup_unresolved:false,diagnostics:[],commands:[{status:'Cancelled',executed:true,exit_code:-15,cleanup_unresolved:false}]},diagnostics:[]};
const context=(stage='layout',fields={})=>({stage,implemented:true,record:structuredClone(cancelled),prerequisite:'specifications',runTestId:stage==='local_rtl_generation'?undefined:stage+'-software-qa-existing-control',runLabel:'Explicit existing stage action',...fields});
function resolve(c){decisions++;const before=JSON.stringify(c);const answer=sandbox.resolve(c);assert.equal(JSON.stringify(c),before,'Presentation must not mutate input records');assert.notEqual(answer.tone,'success');return answer;}
function check(name,body){try{body();results.push({name,status:'Passed'});}catch(e){results.push({name,status:'Failed',message:e.message});}}
check('clean terminal typed cancellation across common S04-S14 paths',()=>{for(const stage of stages){const r=resolve(context(stage));assert.equal(r.decisionId,'cancelled');assert.equal(r.title,'Execution cancelled');assert.equal(r.primary.kind,'inspect');assert.match(r.summary,/does not establish an RTL or circuit defect/);assert.equal(r.secondary.kind,stage==='local_rtl_generation'?'inspect':'control');if(r.secondary.kind==='control')assert.equal(r.secondary.testId,context(stage).runTestId);}});
check('real failures, unsupported results and interrupted execution retain failure guidance',()=>{for(const fields of [{execution_status:'Failed'},{execution_status:'Interrupted'},{execution_status:'Completed',validation_status:'Failed'},{execution_status:'Completed',validation_status:'Unsupported'},{validation_status:'Failed'},{error:{code:'source_changed',message:'Real source mismatch'}},{checks:{validation_status:'Failed',diagnostics:[]}},{diagnostics:[{severity:'error',message:'Retained real error'}]},{checks:{diagnostics:[{severity:'error',message:'Retained real error'}]}}]){const r=resolve(context('layout',{record:{...structuredClone(cancelled),...fields}}));assert.equal(r.decisionId,'failed');}});
check('unresolved aggregate or command cleanup never offers retry',()=>{for(const flags of [{cleanup_unresolved:true},{cleanup_unresolved:false,commands:[{cleanup_unresolved:true}]}]){const r=resolve(context('layout',{gate:'Cleanup must be verified.',record:{...structuredClone(cancelled),checks:flags}}));assert.equal(r.decisionId,'cancelled');assert.match(r.title,/cleanup/);assert.equal(r.primary.kind,'inspect');assert.equal(r.secondary,undefined);}});
check('verified cleanup resolution retains normal current-stage guards',()=>{const c=context('layout');c.record.cleanup_resolution={status:'Verified'};c.record.checks.cleanup_unresolved=true;const r=resolve(c);assert.equal(r.title,'Execution cancelled');assert.equal(r.secondary.kind,'control');const blocked=resolve({...c,gate:'A current source is required.'});assert.equal(blocked.decisionId,'prerequisite');assert.equal(blocked.secondary.kind,'inspect');});
check('unknown start, reconnect and active operations take precedence',()=>{for(const stage of stages){let r=resolve(context(stage,{reconnect:'existing-reconnect'}));assert.equal(r.decisionId,'reconnect');assert.equal(r.primary.testId,'existing-reconnect');r=resolve(context(stage,{executionOverlay:{status:'Failed',reconnectRequired:true},executionReconnect:()=>{throw Error('No callback may run');}}));assert.equal(r.decisionId,'execution_reconnect');r=resolve(context(stage,{executionOverlay:{status:'Running'}}));assert.equal(r.decisionId,'execution_running');r=resolve(context(stage,{activeOperation:{stage:'specifications'}}));assert.equal(r.decisionId,'active_other');r=resolve(context(stage,{busy:true}));assert.equal(r.decisionId,'active_current');}});
check('read-only conflict unsaved and invalid inputs retain priority',()=>{for(const stage of stages){for(const [field,value,id] of [['readOnly',true,'read_only'],['conflict',true,'conflict'],['dirty',true,'dirty'],['invalidInput','Invalid saved input','invalid_input']])assert.equal(resolve(context(stage,{[field]:value})).decisionId,id);}});
check('historical stale source revision and review guards retain priority',()=>{for(const stage of stages){assert.equal(resolve(context(stage,{historical:true})).decisionId,'history');assert.equal(resolve(context(stage,{recordCurrent:false})).decisionId,'source_history');assert.equal(resolve(context(stage,{record:{...structuredClone(cancelled),freshness:'Stale'}})).decisionId,'stale');assert.equal(resolve(context(stage,{record:{...structuredClone(cancelled),review_status:'Changes Requested'}})).decisionId,'review_changes');}assert.equal(resolve(context('global_rtl_generation',{sourceRevisionConflict:true,gate:'Mixed source revisions'})).decisionId,'prerequisite');assert.equal(resolve(context('layout',{integrationUnsupported:'Implementation missing'})).decisionId,'integration_unsupported');});
check('epoch invalidation stays ahead of cancellation history',()=>{const r=resolve(context('layout',{executionOverlay:{invalidated:true},hasSavedEvidence:true}));assert.equal(r.decisionId,'execution_invalidated');assert.equal(r.title,'Run this stage again');assert.equal(r.secondary.kind,'inspect');});
check('source gate is inspect-only and does not offer execution',()=>{for(const stage of stages){const r=resolve(context(stage,{gate:'Current accepted source is required.'}));assert.equal(r.decisionId,'prerequisite');assert.equal(r.primary.kind,'inspect');assert.equal(r.secondary.kind,'inspect');}assert.equal(resolve(context('layout',{implemented:false})).decisionId,'unimplemented');});
check('selected S05 cancellation does not recommend RTL repair from other failed nodes',()=>{for(const fields of [{synthesisRepairCount:2,synthesisSummary:{total:3,accepted:1}},{synthesisSummary:{total:3,accepted:1,sameRtlRetry:2}}]){const r=resolve(context('local_synthesis',fields));assert.equal(r.decisionId,'cancelled');assert.doesNotMatch(JSON.stringify(r),/Prepare RTL repair|workflow-batch-repair-all/);}});
check('S04 scoped provider and batch guidance remain authoritative',()=>{let r=resolve(context('local_rtl_generation',{localGuidance:{title:'Configure provider first',summary:'Required saved provider',primary:{kind:'inspect',label:'Inspect provider'}}}));assert.equal(r.decisionId,'local_generation');r=resolve(context('local_rtl_generation',{generationBatchGuidance:{title:'Inspect generation batch',primary:{kind:'inspect',label:'Inspect saved batch'}}}));assert.equal(r.decisionId,'generation_batch');});
check('S06 batch and checker prerequisites remain authoritative',()=>{let r=resolve(context('local_netlist_simulation',{netlistSummary:{total:3,accepted:1,runnable:2,failed:0,blocked:0}}));assert.equal(r.decisionId,'s06_batch');r=resolve(context('local_netlist_simulation',{blocker:{kind:'configuration_required',message:'Simulator required'}}));assert.equal(r.decisionId,'s06_configuration');});
check('cancellation decision is registered once without changing primary stage count',()=>{assert.equal(sandbox.decisions.filter(x=>x==='cancelled').length,1);assert.equal(sandbox.decisions.length,49);});
const summary={scope:'Private isolated presentation scenarios; not actual GUI or circuit evidence',source:sourcePath,groups:results.length,decisions,passed:results.filter(x=>x.status==='Passed').length,failed:results.filter(x=>x.status==='Failed').length,productionEdits:0,results};
console.log(JSON.stringify(summary,null,2));process.exitCode=summary.failed?1:0;

"""

class CancelledGuidanceTests(unittest.TestCase):
    def test_cancellation_priority_cleanup_real_errors_and_read_only_actions(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node required for isolated presentation checks.')
        result=subprocess.run([node,'-e',CLIENT],cwd=PROJECT,capture_output=True,text=True,encoding='utf-8',timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        summary=json.loads(result.stdout)
        self.assertEqual(summary['failed'],0)
        self.assertEqual(summary['groups'],13)

if __name__=='__main__':unittest.main()
