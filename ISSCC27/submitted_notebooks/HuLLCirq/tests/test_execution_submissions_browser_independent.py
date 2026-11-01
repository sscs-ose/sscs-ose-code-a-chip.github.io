"""Independent common-start browser-controller fixtures; no app/model/EDA access.

Only Node's in-process VM is used. Fetch, storage, provider, and native work are
synthetic. No other TestCase classes are imported, so discovery is not duplicated.
"""
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/gui/execution_submissions.js"
SERVER_SOURCE = ROOT / "src/hullcirq/server.py"
EVIDENCE = ROOT / ".work/autonomous_qualification_20261031/I17/browser_independent"

CLIENT = r"""
const vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const VERSION='execution-submission-v1',KEY='hullcirq.execution-start-recovery.v1';
const ROUTES=['generation/batches/start','repair-analysis/start','workflow/start','workflow/batches/start','global-generation/start','global-workflow/runs','physical-workflow/runs','drc-workflow/runs','lvs-workflow/runs','postlayout-workflow/runs'];
const clone=x=>JSON.parse(JSON.stringify(x));
const ordered=x=>Array.isArray(x)?x.map(ordered):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,ordered(x[k])])):x;
const semantic=body=>Object.fromEntries(Object.entries(body).filter(([k])=>k!=='submission_id'));
const hash=(route,body)=>crypto.createHash('sha256').update(JSON.stringify(ordered({route,request:semantic(body)}))).digest('hex');
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j});return{promise,resolve,reject}};
let assertions=0;function check(value,message){assertions++;assert.ok(value,message)}
function fixture(options={}){
 const data=options.data||new Map(), events=[],posts=[],reads=[],published=[],notices=[],toasts=[];
 let storageFailure=null,providerCalls=0,nativeCalls=0,uuid=0,foreign=false,reply=null;
 const context={scope:JSON.stringify(['software-project','software-system']),busy:false,readOnly:false,dirty:false,conflict:null,
  envelope:{revision:{id:'software-revision'},workspace_identity:{project_id:'software-project',system_id:'software-system',session_id:'software-session'},execution_submission_protocol_version:VERSION,
   execution_configuration_fingerprints:Object.fromEntries(ROUTES.map(route=>[route,'a'.repeat(64)]))}};
 const storage={getItem(key){if(storageFailure==='read')throw Error('Synthetic storage read failure');return data.get(key)||null},
  setItem(key,value){if(storageFailure==='write')throw Error('Synthetic storage write failure');data.set(key,String(value));events.push('persist')},
  removeItem(key){if(storageFailure==='remove')throw Error('Synthetic storage removal failure');data.delete(key);events.push('remove')}};
 if(options.failRead)storageFailure='read';
 const forbidden=name=>()=>{if(name==='provider')providerCalls++;else nativeCalls++;throw Error('Forbidden real '+name+' operation in pure fixture')};
 const sandbox={crypto:{randomUUID:()=>`software-nonce-${++uuid}`},fetch:forbidden('fetch'),provider:forbidden('provider'),
  require:forbidden('require'),child_process:{spawn:forbidden('spawn'),exec:forbidden('exec')},sessionStorage:options.noStorage?undefined:storage};
 vm.createContext(sandbox);vm.runInContext(__SOURCE__.replace(/export /g,'')+'\nthis.Controller=ExecutionSubmissions;this.routeSet=EXECUTION_START_ROUTES;',sandbox,{timeout:1000});
 let controller;
 function success(route,body,id='software-record-1'){
  return{workspace_identity:clone(context.envelope.workspace_identity),execution_submission_protocol_version:VERSION,
   execution_submission:{version:VERSION,route,submission_id:body.submission_id,record_id:id,replayed:false},
   execution_submission_receipts:{[route]:{[body.submission_id]:{route,request:semantic(clone(body)),binding_hash:hash(route,body),record_id:id,rejection:null}}}};
 }
 async function fakeFetch(path,init){
  if(init?.method==='POST'){
   const durable=JSON.parse(data.get(KEY)||'[]');
   check(durable.some(e=>e.scope===context.scope&&JSON.stringify(e.body)===init.body),'Exact recovery marker must exist before any POST');
   events.push('post');const body=JSON.parse(init.body),route=path.replace(/^\/api\//,'');posts.push({route,body:clone(body),wire:init.body});
   return reply?await reply(route,body):{status:202,value:success(route,body)};
  }
  events.push('read');reads.push(path);return reply?await reply(path):{status:200,value:clone(context.envelope)};
 }
 async function send(route,input){
  const requestedScope=context.scope,body=controller.prepare(route,input);
  try{
   const result=await fakeFetch('/api/'+route,{method:'POST',body:JSON.stringify(body)});
   if(result.status<200||result.status>=300){const raw=result.value.error||{};throw Object.assign(Error(raw.message||'Synthetic rejection'),{status:result.status,code:raw.code,submissionId:raw.submission_id,executionStartRejectedBeforeCreation:raw.execution_start_rejected_before_creation===true})}
   controller.observeSuccess(route,body,result.value);return result.value;
  }catch(error){controller.observeFailure(route,body,error,requestedScope);throw error}
 }
 const callbacks={context:()=>context,foreignPending:()=>foreign,storage:options.noStorage?null:storage,
  read:async()=>{const result=await fakeFetch('/api/project');if(result.status!==200)throw Error('Synthetic GET failure');return result.value},send,
  publish:value=>published.push(clone(value)),changed:()=>events.push('changed'),notify:message=>notices.push(message),toast:message=>toasts.push(message)};
 controller=new sandbox.Controller(callbacks);
 return{context,data,storage,events,posts,reads,published,notices,toasts,callbacks,sandbox,success,send,
  get controller(){return controller},reload(){controller=new sandbox.Controller(callbacks);return controller},
  failStorage:value=>storageFailure=value,setReply:value=>reply=value,setForeign:value=>foreign=value,
  metrics:()=>({posts:posts.length,reads:reads.length,provider_calls:providerCalls,native_calls:nativeCalls})};
}
const input=()=>({revision_id:'software-revision',node_id:'software-node',request_id:'software-legacy-request',nested:{expect:'independent expected value',drive:[1,2,3]}});
const ambiguous=(f,route='workflow/start')=>{const body=f.controller.prepare(route,input());f.controller.observeFailure(route,body,Error('Synthetic lost ACK'));return body};
globalThis.fetch=()=>{throw Error('Real fetch is forbidden in independent fixture')};
"""


class ExecutionSubmissionsBrowserIndependentTests(unittest.TestCase):
    """Independent NodeVM cases; evidence identifies the exact qualified source."""

    @classmethod
    def setUpClass(cls):
        cls.node = shutil.which("node")
        cls.initial_sha256 = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        cls.started_at = datetime.now().astimezone().isoformat()
        cls.run_directory = EVIDENCE / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        cls.run_directory.mkdir(parents=True, exist_ok=False)
        cls.case_records = []

    @classmethod
    def tearDownClass(cls):
        summary = {"started_at": cls.started_at, "finished_at": datetime.now().astimezone().isoformat(),
                   "method_artifacts": len(cls.case_records), "source_sha256": cls.initial_sha256,
                   "method_failures": sum(not item["passed"] for item in cls.case_records),
                   "stable_source": all(item.get("stable_source", True) for item in cls.case_records),
                   "real_application_requests": 0, "real_model_calls": 0, "real_eda_jobs": 0,
                   "scope": "Independent NodeVM and isolated error-decorator function only; no app imports",
                   "cases": cls.case_records}
        (cls.run_directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    def run_client(self, body):
        if not self.node:
            self.skipTest("Node is required for isolated controller fixtures.")
        before = SOURCE.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        started = datetime.now().astimezone().isoformat()
        source = CLIENT.replace("__SOURCE__", json.dumps(before.decode("utf-8")))
        script = source + "\n(async()=>{\n" + body + (
            "\nconsole.log(JSON.stringify({status:'Passed',assertion_checkpoints:assertions,"
            "real_network_requests:0,real_provider_calls:0,real_native_calls:0}));"
            "\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1});")
        environment = os.environ.copy()
        environment.pop("NODE_OPTIONS", None)
        result = subprocess.run([self.node, "-e", script], cwd=ROOT, env=environment,
                                capture_output=True, text=True, encoding="utf-8", timeout=20)
        after = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        artifact = {"method": self._testMethodName, "started_at": started,
                    "finished_at": datetime.now().astimezone().isoformat(),
                    "source_sha256_before": digest, "source_sha256_after": after,
                    "class_initial_sha256": self.initial_sha256,
                    "stable_source": digest == after == self.initial_sha256,
                    "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr,
                    "fixture": "NodeVM only; synthetic fetch/storage/provider/native callbacks; no app import"}
        artifact["passed"] = result.returncode == 0 and artifact["stable_source"]
        self.case_records.append({key: artifact[key] for key in ("method", "passed", "stable_source", "source_sha256_before", "source_sha256_after")})
        target = self.run_directory / (self._testMethodName + ".json")
        target.write_text(json.dumps(artifact, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        self.assertEqual(digest, after, "Controller source moved during the fixture; result is unqualified.")
        self.assertEqual(digest, self.initial_sha256, "Controller source moved during this suite; qualify one stable revision.")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_01_only_ten_common_routes_have_one_owner_and_s04_is_passthrough(self):
        self.run_client(r"""
const f=fixture();assert.deepEqual([...f.sandbox.routeSet].sort(),[...ROUTES].sort());
for(const route of ['generation/start','project','save','generation/cancel','global-generation/context']){
 const body=input();assert.equal(f.controller.prepare(route,body),body);assert.equal(f.data.size,0);
}
f.setForeign(true);assert.equal(f.controller.prepare('generation/start',input()).submission_id,undefined);
f.setForeign(false);ambiguous(f);assert.throws(()=>f.controller.prepare('generation/start',input()),e=>e.request_not_sent===true);
assert.deepEqual(f.metrics(),{posts:0,reads:0,provider_calls:0,native_calls:0});
""")

    def test_02_every_route_persists_frozen_marker_before_mock_post(self):
        self.run_client(r"""
for(const route of ROUTES){const f=fixture(),body=input(),old=JSON.stringify(body);await f.send(route,body);
 assert.equal(JSON.stringify(body),old);assert.equal(f.posts.length,1);assert.ok(f.events.indexOf('persist')<f.events.indexOf('post'));
 assert.equal(f.controller.pending(),undefined);assert.equal(f.controller.lastResolution.recordId,'software-record-1');assert.equal(f.data.size,0);
 assert.equal(f.metrics().provider_calls+f.metrics().native_calls,0);}
""")

    def test_03_preforward_zero_record_refresh_stays_pending_and_explicit_retry_reuses_wire(self):
        self.run_client(r"""
const f=fixture();let persisted=0;f.setReply(async(route,body)=>{if(body)throw Error('Synthetic before-forward drop');return{status:200,value:clone(f.context.envelope)}});
await assert.rejects(f.send('workflow/start',input()));const first=f.posts[0].wire;assert.ok(f.controller.pending());
await f.controller.refresh();assert.equal(f.posts.length,1);assert.equal(f.reads.length,1);assert.ok(f.controller.pending());assert.equal(f.controller.retryGate(),'');
assert.throws(()=>f.controller.prepare('drc-workflow/runs',input()),e=>e.request_not_sent===true);
f.setReply(async(route,body)=>{persisted++;return{status:202,value:f.success(route,body,'software-only-record')}});
await f.controller.retry();assert.equal(f.posts.length,2);assert.equal(f.posts[1].wire,first);assert.equal(persisted,1);assert.equal(f.controller.pending(),undefined);
""")

    def test_04_postpersist_typed_500_does_not_acknowledge_or_automatically_repost(self):
        self.run_client(r"""
for(const status of [400,409,500,502]){const f=fixture();let committed;
 f.setReply(async(route,body)=>{committed=f.success(route,body,'software-committed');return{status,value:{error:{code:'software_postpersist',message:'Synthetic response failure',submission_id:body.submission_id}}}});
 await assert.rejects(f.send('global-generation/start',input()));assert.ok(f.controller.pending());assert.equal(f.posts.length,1);
 f.setReply(async()=>({status:200,value:committed}));await f.controller.refresh();assert.equal(f.posts.length,1);assert.equal(f.controller.pending(),undefined);assert.equal(f.controller.lastResolution.recordId,'software-committed');}
""")

    def test_05_exact_replay_keeps_nonce_nested_body_and_original_configuration(self):
        self.run_client(r"""
const f=fixture(),original=input(),body=f.controller.prepare('physical-workflow/runs',original),frozen=JSON.stringify(body);
original.nested.drive.push(999);original.node_id='changed';f.context.envelope.execution_configuration_fingerprints['physical-workflow/runs']='b'.repeat(64);
f.controller.observeFailure('physical-workflow/runs',body,Error('Synthetic ACK loss'));let records=0;
f.setReply(async(route,wire)=>{assert.equal(JSON.stringify(wire),frozen);records++;const r=f.success(route,wire);r.execution_submission.replayed=true;return{status:202,value:r}});
await f.controller.retry();assert.equal(records,1);assert.equal(f.posts.length,1);assert.equal(f.posts[0].body.submission_configuration_fingerprint,'a'.repeat(64));assert.equal(f.controller.pending(),undefined);
""")

    def test_06_reload_retains_unknown_marker_without_fetch_and_reads_exact_receipt(self):
        self.run_client(r"""
const f=fixture(),body=ambiguous(f),wire=JSON.stringify(body);f.reload();assert.ok(f.controller.pending());assert.equal(f.controller.pending().sending,false);
assert.equal(f.controller.retryGate(),'');assert.equal(f.posts.length+f.reads.length,0);assert.ok(f.controller.presentation());
f.setReply(async()=>({status:200,value:f.success('workflow/start',body)}));await f.controller.refresh();assert.equal(f.controller.pending(),undefined);assert.equal(f.posts.length,0);assert.equal(f.reads.length,1);assert.equal(wire,JSON.stringify(body));
""")

    def test_07_success_requires_exact_version_route_nonce_and_top_record_binding(self):
        self.run_client(r"""
for(const change of [r=>r.execution_submission.version='other',r=>r.execution_submission.route='drc-workflow/runs',r=>r.execution_submission.submission_id='foreign-nonce',r=>r.execution_submission.record_id='foreign-record',r=>r.execution_submission.record_id='',r=>delete r.execution_submission]){
 const f=fixture(),body=ambiguous(f),r=f.success('workflow/start',body);change(r);
 assert.throws(()=>f.controller.observeSuccess('workflow/start',body,r));assert.ok(f.controller.pending());assert.equal(f.data.size,1);}
""")

    def test_08_saved_receipts_reject_changed_request_route_hash_shape_and_rejection(self):
        self.run_client(r"""
for(const change of [s=>s.request.node_id='foreign-node',s=>s.request.nested.drive.push(4),s=>s.route='lvs-workflow/runs',s=>s.binding_hash='not-a-hash',s=>s.binding_hash='A'.repeat(64),s=>s.rejection={status:409,code:'busy',message:'Synthetic refusal'},s=>s.record_id='other-record']){
 const f=fixture(),body=ambiguous(f),r=f.success('workflow/start',body),saved=r.execution_submission_receipts['workflow/start'][body.submission_id];change(saved);
 assert.throws(()=>f.controller.observeSuccess('workflow/start',body,r));assert.ok(f.controller.pending());}
""")

    def test_09_reads_cannot_resolve_foreign_scope_route_nonce_or_invalid_receipts(self):
        self.run_client(r"""
for(const change of [r=>r.execution_submission_receipts={},r=>r.execution_submission_receipts['workflow/start']={},r=>r.execution_submission_receipts['workflow/start']['other']=Object.values(r.execution_submission_receipts['workflow/start'])[0],
 r=>{const s=Object.values(r.execution_submission_receipts['workflow/start'])[0];s.record_id='';},r=>{const s=Object.values(r.execution_submission_receipts['workflow/start'])[0];s.binding_hash='invalid';}]){
 const f=fixture(),body=ambiguous(f),r=f.success('workflow/start',body);change(r);
 if(Object.hasOwn(r.execution_submission_receipts['workflow/start']||{},'other'))delete r.execution_submission_receipts['workflow/start'][body.submission_id];
 f.controller.observeRead(r,f.context.scope);assert.ok(f.controller.pending());}
const f=fixture(),body=ambiguous(f),scope=f.context.scope,r=f.success('workflow/start',body);f.controller.observeRead(r,'foreign-scope');assert.ok(f.controller.pending());
f.context.scope='foreign-scope';f.controller.observeRead(r,scope);assert.equal(f.controller.entries.get(scope).body.submission_id,body.submission_id);
""")

    def test_10_foreign_owner_protocol_readonly_and_missing_fingerprint_fail_closed(self):
        self.run_client(r"""
for(const mutation of [f=>f.setForeign(true),f=>f.context.readOnly=true,f=>f.context.envelope.execution_submission_protocol_version='old',f=>delete f.context.envelope.execution_configuration_fingerprints['workflow/start']]){
 const f=fixture();mutation(f);assert.throws(()=>f.controller.prepare('workflow/start',input()),e=>e.request_not_sent===true);assert.equal(f.posts.length+f.reads.length,0);assert.equal(f.data.size,0);}
""")

    def test_11_unavailable_malformed_or_failed_storage_prevents_posts(self):
        self.run_client(r"""
for(const options of [{noStorage:true},{failRead:true},{data:new Map([[KEY,'not-json']])},{data:new Map([[KEY,'{}']])}]){
 const f=fixture(options);assert.ok(f.controller.storageError);assert.ok(f.controller.blocked());assert.throws(()=>f.controller.prepare('workflow/start',input()),e=>e.request_not_sent===true);assert.equal(f.posts.length,0);}
const f=fixture();f.failStorage('write');assert.throws(()=>f.controller.prepare('workflow/start',input()),e=>e.request_not_sent===true);assert.equal(f.posts.length,0);assert.ok(f.controller.storageError);
""")

    def test_12_duplicate_and_empty_saved_scopes_are_ambiguous_and_never_sent(self):
        self.run_client(r"""
const seed=fixture(),body=ambiguous(seed),entry=JSON.parse(seed.data.get(KEY))[0];
for(const rows of [[entry,{...entry,route:'drc-workflow/runs'}],[{...entry,scope:null}],[{...entry,scope:''}],[{...entry,body:{...body,submission_id:false}}]]){
 const f=fixture({data:new Map([[KEY,JSON.stringify(rows)]])});assert.ok(f.controller.storageError);assert.ok(f.controller.blocked());assert.throws(()=>f.controller.prepare('workflow/start',input()),e=>e.request_not_sent===true);assert.equal(f.posts.length,0);}
""")

    def test_13_null_active_scope_cannot_send_or_consume_an_old_scope_receipt(self):
        self.run_client(r"""
for(const value of [null,undefined,'']){const f=fixture();f.context.scope=value;assert.throws(()=>f.controller.prepare('workflow/start',input()),e=>e.request_not_sent===true);assert.equal(f.data.size,0);}
const f=fixture(),body=ambiguous(f),scope=f.context.scope,reply=f.success('workflow/start',body);f.context.scope=null;
f.controller.observeRead(reply,scope);assert.ok(f.controller.entries.get(scope),'No active system may consume a different scope marker');assert.equal(f.data.size,1);
""")

    def test_14_explicit_falsy_or_invalid_nonce_never_silently_creates_a_new_identity(self):
        self.run_client(r"""
for(const nonce of [null,false,0,'',' space','_leading','a'.repeat(129),{},[]]){
 const f=fixture();assert.throws(()=>f.controller.prepare('workflow/start',{...input(),submission_id:nonce}),e=>e.request_not_sent===true);assert.equal(f.data.size,0);assert.equal(f.posts.length,0);}
const f=fixture(),body=f.controller.prepare('workflow/start',input());assert.equal(body.submission_id,'software-nonce-1');
""")

    def test_15_only_true_precreation_4xx_for_exact_nonce_can_release_marker(self):
        self.run_client(r"""
for(const marker of [undefined,false,0,1,'true',{},[]]){const f=fixture(),body=ambiguous(f);f.controller.observeFailure('workflow/start',body,{status:409,executionStartRejectedBeforeCreation:marker,submissionId:body.submission_id});assert.ok(f.controller.pending());}
for(const status of [200,399,500,502,'409',null]){const f=fixture(),body=ambiguous(f);f.controller.observeFailure('workflow/start',body,{status,executionStartRejectedBeforeCreation:true,submissionId:body.submission_id});assert.ok(f.controller.pending());}
for(const status of [400,403,409,422,429]){const f=fixture(),body=ambiguous(f);f.controller.observeFailure('workflow/start',body,{status,executionStartRejectedBeforeCreation:true,submissionId:body.submission_id});assert.equal(f.controller.pending(),undefined);assert.equal(f.controller.lastResolution.status,'rejected');}
const f=fixture(),body=ambiguous(f);f.controller.observeFailure('workflow/start',body,{status:409,executionStartRejectedBeforeCreation:true,submissionId:'other'});assert.ok(f.controller.pending());
""")

    def test_16_rejected_get_receipt_requires_null_record_and_integer_4xx(self):
        self.run_client(r"""
for(const status of ['409',500,399,null]){const f=fixture(),body=ambiguous(f),r=f.success('workflow/start',body),s=r.execution_submission_receipts['workflow/start'][body.submission_id];s.record_id=null;s.rejection={status,code:'synthetic_busy',message:'Synthetic refusal'};f.controller.observeRead(r,f.context.scope);assert.ok(f.controller.pending());}
const f=fixture(),body=ambiguous(f),r=f.success('workflow/start',body),s=r.execution_submission_receipts['workflow/start'][body.submission_id];s.record_id=null;s.rejection={status:409,code:'synthetic_busy',message:'Synthetic refusal'};f.controller.observeRead(r,f.context.scope);assert.equal(f.controller.pending(),undefined);assert.equal(f.controller.lastResolution.status,'rejected');
""")

    def test_17_late_refresh_cannot_publish_or_clear_another_project(self):
        self.run_client(r"""
const f=fixture(),body=ambiguous(f),scope=f.context.scope,r=f.success('workflow/start',body),wait=deferred();f.setReply(()=>wait.promise);
const reading=f.controller.refresh();assert.equal(f.reads.length,1);f.context.scope='different-project';wait.resolve({status:200,value:r});await reading;
assert.equal(f.published.length,0);assert.ok(f.controller.entries.get(scope));assert.equal(f.posts.length,0);assert.equal(f.controller.reading,false);
""")

    def test_18_pending_different_body_scope_and_read_in_flight_never_create_new_post(self):
        self.run_client(r"""
const f=fixture(),body=ambiguous(f);
for(const altered of [{...body,submission_id:'other'},{...body,node_id:'other'},{...body,nested:{drive:[],expect:'different'}}])assert.throws(()=>f.controller.prepare('workflow/start',altered),e=>e.request_not_sent===true);
f.controller.reading=true;assert.ok(f.controller.retryGate());await f.controller.retry();assert.equal(f.posts.length,0);f.controller.reading=false;
for(const field of ['busy','dirty','readOnly','conflict']){f.context[field]=true;assert.ok(f.controller.retryGate());await f.controller.retry();assert.equal(f.posts.length,0);f.context[field]=false;}
""")

    def test_19_raw_analysis_ack_requires_its_exact_context_and_legacy_request_id(self):
        self.run_client(r"""
for(const field of ['id','submission_id','request_id','context_id']){const f=fixture(),body=f.controller.prepare('repair-analysis/start',{...input(),context_id:'software-context'}),r=f.success('repair-analysis/start',body);delete r.execution_submission_receipts;Object.assign(r,{id:r.execution_submission.record_id,submission_id:body.submission_id,request_id:body.request_id,context_id:body.context_id});r[field]='foreign';assert.throws(()=>f.controller.observeSuccess('repair-analysis/start',body,r));assert.ok(f.controller.pending());}
const f=fixture(),body=f.controller.prepare('repair-analysis/start',{...input(),context_id:'software-context'}),r=f.success('repair-analysis/start',body);delete r.execution_submission_receipts;Object.assign(r,{id:r.execution_submission.record_id,submission_id:body.submission_id,request_id:body.request_id,context_id:body.context_id});f.controller.observeSuccess('repair-analysis/start',body,r);assert.equal(f.controller.pending(),undefined);
""")

    def test_20_server_emits_rejection_metadata_only_for_actual_boolean_true(self):
        before = SERVER_SOURCE.read_bytes()
        digest = hashlib.sha256(before).hexdigest()
        tree = ast.parse(before.decode("utf-8"))
        method = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "_error")
        module = ast.Module(body=[method], type_ignores=[])
        ast.fix_missing_locations(module)
        namespace = {"DomainError": type("FixtureDomainError", (), {})}
        exec(compile(module, "<isolated server error decorator>", "exec"), namespace)
        checks = []
        for flag in (False, 0, 1, "true", {}, [], None, True):
            with self.subTest(flag=repr(flag)):
                error = type("FixtureError", (), {"code": "fixture", "message": "Synthetic refusal", "status": 409,
                    "submission_id": "software-key", "execution_start_rejected_before_creation": flag})()
                replies = []
                receiver = type("FixtureReceiver", (), {"_json": lambda self, value, status: replies.append((value, status))})()
                namespace["_error"](receiver, error)
                observed = replies[0][0]["error"].get("execution_start_rejected_before_creation", False)
                checks.append({"flag": repr(flag), "observed": observed, "expected": flag is True, "passed": observed == (flag is True)})
                self.assertEqual(observed, flag is True)
        after = hashlib.sha256(SERVER_SOURCE.read_bytes()).hexdigest()
        artifact = {"method": self._testMethodName, "server_sha256_before": digest, "server_sha256_after": after,
                    "stable_source": digest == after, "checks": checks, "passed": digest == after and all(item["passed"] for item in checks)}
        self.case_records.append(artifact)
        (self.run_directory / (self._testMethodName + ".json")).write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(digest, after, "Server decorator changed during isolated check.")

    def test_21_background_receipt_cannot_release_marker_before_post_ack_finishes(self):
        self.run_client(r"""
const f=fixture(),wait=deferred();let ack;
f.setReply(async(route,body)=>{ack=f.success(route,body);return wait.promise});
const sent=f.send('workflow/start',input());assert.equal(f.posts.length,1);const scope=f.context.scope;
f.controller.observeRead(ack,scope);assert.ok(f.controller.pending(),'A background read cannot clear a sending marker and permit a fresh submission');
assert.throws(()=>f.controller.prepare('workflow/start',input()),e=>e.request_not_sent===true);
wait.reject(Error('Synthetic ACK lost after background observation'));await assert.rejects(sent);assert.equal(f.controller.pending().sending,false);
f.controller.observeRead(ack,scope);assert.equal(f.controller.pending(),undefined);assert.equal(f.posts.length,1);
""")


if __name__ == "__main__":
    unittest.main()
