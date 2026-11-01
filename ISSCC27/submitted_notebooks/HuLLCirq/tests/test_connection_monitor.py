"""Prepared-local health monitoring with fake requests/timers; no real API or process."""
from pathlib import Path
import shutil
import subprocess
import unittest


PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const timers=new Map(),requests=[],changes=[];let nextTimer=1,responder=async()=>({runtime:{state:'Running'}});
const project={readOnly:false,profileDirty:false,envelope:{workspace_identity:{session_id:'session-a'},llm:{profile_revision_id:'profile-a',profile:{execution_location:'Local',base_url:'http://127.0.0.1:11435/v1',model:'qwen3:8b'}}}};
let visible=true;
const sandbox={URL,Date,setTimeout:(callback,delay)=>{const id=nextTimer++;timers.set(id,{callback,delay});return id;},clearTimeout:id=>timers.delete(id)};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync('src/gui/connection_monitor.js','utf8').replace('export class ConnectionMonitor','class ConnectionMonitor')+'\nthis.ConnectionMonitor=ConnectionMonitor;',sandbox);
const monitor=new sandbox.ConnectionMonitor({project:()=>project,request:(...args)=>{requests.push(args);return responder(...args);},changed:()=>changes.push(monitor.runtime?.state||monitor.error),visible:()=>visible});
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve,reject;const promise=new Promise((r,j)=>{resolve=r;reject=j;});return{promise,resolve,reject};};
"""


class ConnectionMonitorTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for isolated GUI monitoring checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body +
                                 "\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_only_explicit_receive_starts_get_only_health_check(self):
        self.run_client(r"""
assert.equal(requests.length,0);assert.equal(timers.size,0);
monitor.receive();await tick();assert.equal(requests.length,1);
assert.deepEqual(requests[0],['workspace/local-runtime']);assert.equal(monitor.runtime.state,'Running');
assert.ok(monitor.checkedAt);assert.equal(timers.size,1);assert.equal([...timers.values()][0].delay,15000);
monitor.receive();assert.equal(requests.length,1);assert.equal(timers.size,1);
""")

    def test_ineligible_profiles_snapshots_and_drafts_never_query_the_server(self):
        self.run_client(r"""
const original=structuredClone(project.envelope.llm.profile);
for(const profile of [{...original,execution_location:'Network'},{...original,model:'other'},{...original,base_url:'http://127.0.0.1:11434/v1'},{...original,base_url:'https://remote.invalid/v1'},{...original,base_url:'http://user:pass@127.0.0.1:11435/v1'},{...original,base_url:'http://127.0.0.1:11435/v1?secret=value'}]){
 project.envelope.llm.profile=profile;project.envelope.llm.profile_revision_id+='-next';monitor.receive();await tick();
}
project.envelope.llm.profile=original;project.profileDirty=true;monitor.receive();await tick();
project.profileDirty=false;project.readOnly=true;monitor.receive();await tick();
project.readOnly=false;project.envelope.workspace_identity.session_id=null;monitor.receive();await tick();
assert.equal(requests.length,0);assert.equal(timers.size,0);
""")

    def test_hidden_document_defers_observation_without_starting_any_request(self):
        self.run_client(r"""
visible=false;monitor.receive();await tick();assert.equal(requests.length,0);assert.equal(timers.size,1);
const timer=[...timers.values()][0];timers.clear();visible=true;timer.callback();await tick();
assert.equal(requests.length,1);assert.deepEqual(requests[0],['workspace/local-runtime']);
""")

    def test_pending_observation_is_coalesced_and_old_session_response_is_ignored(self):
        self.run_client(r"""
const first=deferred(),second=deferred();responder=()=>requests.length===1?first.promise:second.promise;
monitor.receive();monitor.refresh();monitor.receive();assert.equal(requests.length,1);
project.envelope.workspace_identity.session_id='session-b';monitor.receive();assert.equal(requests.length,2);
second.resolve({runtime:{state:'Stopped'}});await tick();first.resolve({runtime:{state:'Running'}});await tick();
assert.equal(monitor.runtime.state,'Stopped');assert.equal(changes.length,1);assert.equal(timers.size,1);
for(const request of requests)assert.deepEqual(request,['workspace/local-runtime']);
""")

    def test_failure_and_invalid_response_remain_visible_then_recover_on_get(self):
        self.run_client(r"""
responder=async()=>({});monitor.receive();await tick();assert.match(monitor.error,/unavailable/);assert.equal(monitor.runtime,null);
responder=async()=>{throw Error('Service offline');};await monitor.refresh();assert.equal(monitor.error,'Service offline');
responder=async()=>({runtime:{state:'Running'}});await monitor.refresh();assert.equal(monitor.error,null);assert.equal(monitor.runtime.state,'Running');
assert.equal(requests.length,3);for(const request of requests)assert.deepEqual(request,['workspace/local-runtime']);
""")

    def test_stop_invalidates_pending_response_without_poll_or_resend(self):
        self.run_client(r"""
const pending=deferred();responder=()=>pending.promise;monitor.receive();assert.equal(requests.length,1);
monitor.stop();pending.resolve({runtime:{state:'Running'}});await tick();
assert.equal(monitor.runtime,null);assert.equal(monitor.pending,false);assert.equal(timers.size,0);assert.equal(changes.length,0);
""")


if __name__ == "__main__":
    unittest.main()
