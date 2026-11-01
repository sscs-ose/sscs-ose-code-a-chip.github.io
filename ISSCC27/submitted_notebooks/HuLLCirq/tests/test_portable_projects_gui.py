"""Isolated GUI event regression; not an actual-browser qualification."""
import unittest
import test_workspace_gui as workspace


class PortableGuiTests(unittest.TestCase):
    run_client = workspace.WorkspaceClientTests.run_client
    def test_evidence_export_requires_private_confirmation_and_never_edits_design(self):
        self.run_client(r"""
const calls=[];manager.download=async(...args)=>calls.push(args);
manager.form=async()=>({confirmation:'not confirmed'});await manager.exportEvidence({id:'p',name:'software-qa'});assert.equal(calls.length,0);
manager.form=async(title,fields,description)=>{assert.match(description,/raw prompts/);assert.match(description,/not a public/);return {confirmation:'PRIVATE'};};
await manager.exportEvidence({id:'p',name:'software-qa'});assert.equal(calls.length,1);assert.equal(calls[0][0],'workspace/evidence-export/p');assert.equal(operations.length,0);
""")

    def test_restored_inspector_has_sandboxed_map_download_and_no_run_control(self):
        self.run_client(r"""
responder=async()=>({restore_policy:'archive only',unavailable:[],entries:[{path:'maps/s/r/v/view/layout_roles.html',size:4,sha256:'a'.repeat(64),file_id:'1'}],maps:[{layout_run_id:'r',html_path:'maps/s/r/v/view/layout_roles.html'}]});
sandbox.sessionFetch=async()=>({ok:true,headers:{get:()=>'text/html; charset=utf-8'},text:async()=>'<html>Software QA installed viewer</html>'});
await manager.inspectEvidence({id:'p'});
const dialog=document.body.children.find(node=>node.tag==='dialog'&&node['aria-label']==='Verified portable evidence');
assert.ok(dialog);const button=descend(dialog).find(node=>node.tag==='button'&&node.text.startsWith('Open archived Functional Map'));assert.ok(button);await button.click();
const frame=descend(dialog).find(node=>node.tag==='iframe');assert.equal(frame.sandbox,'allow-scripts');assert.equal(frame.referrerPolicy,'no-referrer');assert.equal(frame.src,'/api/workspace/evidence-map/p/1');
assert.equal(operations.length,0);assert.equal(requests.length,1);assert.equal(requests[0].route,'workspace/evidence/p');
""")

    def test_archived_versions_have_distinct_labels_for_the_same_physical_run(self):
        self.run_client(r"""
const ids=['functional-map-'+'1'.repeat(32),'functional-map-'+'2'.repeat(32)];
const paths=ids.map(id=>`maps/s/r/${id}/view/layout_roles.html`);
sandbox.sessionFetch=async()=>({ok:true,headers:{get:()=>'text/html; charset=utf-8'},text:async()=>'<html>Software QA installed viewer</html>'});
responder=async()=>({restore_policy:'archive only',unavailable:[],entries:paths.map((path,i)=>({path,size:4,sha256:'a'.repeat(64),file_id:String(i)})),maps:ids.map((id,i)=>({layout_run_id:'r',map_id:id,html_path:paths[i]}))});
await manager.inspectEvidence({id:'p'});
const dialog=document.body.children.find(node=>node.tag==='dialog'&&node['aria-label']==='Verified portable evidence');
const buttons=descend(dialog).filter(node=>node.tag==='button'&&node.text.startsWith('Open archived Functional Map'));
assert.equal(buttons.length,2);assert.notEqual(buttons[0].text,buttons[1].text);
for(let i=0;i<2;i++){assert.ok(buttons[i].text.includes(ids[i]));await buttons[i].click();const frames=descend(dialog).filter(node=>node.tag==='iframe'&&!node.removed);assert.equal(frames.at(-1).src,`/api/workspace/evidence-map/p/${i}`);}
assert.equal(operations.length,0);
""")

    def test_archived_map_read_error_is_visible_and_late_response_cannot_install_frame(self):
        self.run_client(r"""
responder=async()=>({restore_policy:'archive only',unavailable:[],entries:[{path:'maps/s/r/v/view/layout_roles.html',size:4,sha256:'a'.repeat(64),file_id:'1'}],maps:[{layout_run_id:'r',map_id:'v',html_path:'maps/s/r/v/view/layout_roles.html'}]});
sandbox.sessionFetch=async()=>({ok:false,status:409,json:async()=>({error:{message:'SOFTWARE QA invalid compact table'}})});
await manager.inspectEvidence({id:'p'});
const dialog=document.body.children.find(node=>node.tag==='dialog'&&node['aria-label']==='Verified portable evidence');
const button=descend(dialog).find(node=>node.tag==='button'&&node.text.startsWith('Open archived Functional Map'));
await button.click();
const status=descend(dialog).find(node=>node['data-testid']==='workspace-evidence-map-status');
assert.match(status.textContent,/Failed: SOFTWARE QA invalid compact table/);
assert.equal(descend(dialog).filter(node=>node.tag==='iframe').length,0);
let finish;sandbox.sessionFetch=()=>new Promise(resolve=>{finish=resolve;});
const pending=button.click();dialog.close();await Promise.resolve();
finish({ok:true,headers:{get:()=>'text/html'},text:async()=>'<html>Software QA</html>'});await pending;
assert.equal(descend(dialog).filter(node=>node.tag==='iframe').length,0);
assert.equal(operations.length,0);
""")

    def test_pasted_raw_json_goes_unchanged_to_explicit_restore_only(self):
        self.run_client(r"""
manager.pasteEvidence();const dialog=manager.formDialog;
const source=descend(dialog).find(node=>node.tag==='textarea');const raw='{"wide":21778071482940061661655974875633165533189,"private":"SOFTWARE QA"}\r\n';source.value=raw;
await dialog.querySelector('form').dispatch('submit');await Promise.resolve();
assert.equal(operations.length,1);assert.equal(operations[0].action,'restore-evidence');assert.equal(operations[0].body.bundle_text,raw);assert.equal(requests.length,0);
""")
