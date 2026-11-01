"""Focused project-dialog software regressions; no circuit, model or EDA run."""
from pathlib import Path
import shutil
import subprocess
import unittest

PROJECT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('fs'), vm=require('vm'), assert=require('assert/strict');
const source=fs.readFileSync('src/gui/workspace.js','utf8').replace(/^import[^\n]*\n/gm,'').replace('export class WorkspaceManager','class WorkspaceManager');
class DOMDouble {
  constructor(tag,attributes={}) { this.tag=tag; this.children=[]; this.listeners={}; this.open=false; Object.assign(this,attributes); }
  append(...children) { this.children.push(...children.flat(Infinity).filter(child=>child!=null&&child!==false)); }
  replaceChildren(...children) { this.children=[]; this.append(...children); }
  addEventListener(name,callback) { (this.listeners[name]??=[]).push(callback); }
  async dispatch(name,event={preventDefault(){}}) { for(const listener of this.listeners[name]||[]) await listener(event); }
  querySelector(selector) { return descend(this).find(node=>typeof node==='object'&&(selector==='input'?node.tag==='input':selector==='form'?node.tag==='form':node['data-testid']===selector.match(/^\[data-testid="(.*)"\]$/)?.[1]))||null; }
  showModal() { this.open=true; }
  close(value='') { this.returnValue=value; this.open=false; queueMicrotask(()=>this.dispatch('close')); }
  focus() { document.activeElement=this; }
  remove() { this.removed=true; }
  reportValidity() { return true; }
  async click() { return this.onclick?.(); }
}
const descend=host=>host.children.flatMap(child=>child&&typeof child==='object'?[child,...descend(child)]:[]);
const el=(tag,attributes={},...children)=>{const node=new DOMDouble(tag,attributes);node.append(...children);return node;};
const document={body:new DOMDouble('body'),getElementById:id=>elements[id]};
const elements=Object.fromEntries(['workspace-dialog','workspace-dialog-content','workspace-home','workspace-library','workspace-close-dialog'].map(id=>[id,new DOMDouble('div')]));
const field=(label,value,change,options={})=>{const input=el('input',{...options,value});input.addEventListener('input',()=>change(input.value));return el('div',{},input);};
const notices=[],requests=[],operations=[];
let responder=async()=>({}),session='software-qa';
const sandbox={el,field,badge:()=>el('span'),downloadJson(){},document,console,queueMicrotask,Date,
  setTimeout:callback=>{queueMicrotask(callback);return 1;},workspaceSession:()=>session,setWorkspaceSession:value=>session=value};
vm.createContext(sandbox);vm.runInContext(source+'\nglobalThis.WorkspaceManager=WorkspaceManager;',sandbox);
const manager=new sandbox.WorkspaceManager({request:async(route,body)=>{requests.push({route,body});return responder(route,body);},notify:message=>notices.push(message),project:()=>({}),beforeLeave:async()=>true,toast(){}});
manager.operate=async(action,body)=>operations.push({action,body});
const normalized=value=>JSON.parse(JSON.stringify(value));
const find=id=>manager.formDialog.querySelector('[data-testid="'+id+'"]');
const submit=async()=>{await manager.formDialog.querySelector('form').dispatch('submit');await Promise.resolve();};
"""


class WorkspaceClientTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for the isolated project-dialog checks.")
        result = subprocess.run([node, "-e", CLIENT + "\n(async()=>{\n" + body +
                                 "\nconsole.log('Passed: focused workspace dialog software fixture');\n})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});"],
                                cwd=PROJECT, capture_output=True, text=True, encoding="utf-8", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_two_project_forms_submit_fresh_values_and_release_modal_reference(self):
        self.run_client(r"""
for(const name of ['Software QA first','Software QA second']) {
  const pending=manager.newProject(); const dialog=manager.formDialog;
  find('workspace-field-name').value=name; // Emulate keyboard/autofill without blur.
  await submit(); await pending;
  assert.equal(dialog.removed,true); assert.equal(manager.formDialog,null);
}
assert.deepEqual(normalized(operations),[
  {action:'create-project',body:{name:'Software QA first',system_name:'Main system',top_module:'system_top'}},
  {action:'create-project',body:{name:'Software QA second',system_name:'Main system',top_module:'system_top'}}]);
""")

    def test_double_click_does_not_stack_forms_and_cancel_allows_reopening(self):
        self.run_client(r"""
const first=manager.newProject(), dialog=manager.formDialog;
await manager.newProject(); assert.equal(manager.formDialog,dialog);
assert.equal(document.body.children.filter(node=>node.tag==='dialog'&&!node.removed).length,1);
dialog.close('cancel'); await first; assert.equal(manager.formDialog,null); assert.equal(operations.length,0);
const again=manager.newProject(); assert.notEqual(manager.formDialog,dialog);
manager.formDialog.close('cancel'); await again; assert.equal(operations.length,0);
""")

    def test_parent_picker_populates_reviewable_full_project_path(self):
        self.run_client(r"""
responder=async(route,body)=>route==='workspace/folder-picker'
  ?{picker:{id:'software-qa-picker',status:'Pending',directory:null}}
  :{picker:{id:'software-qa-picker',status:'Completed',directory:'C:\\software-qa'}};
const pending=manager.newProject();
find('workspace-field-name').value='QA: Design';await find('workspace-field-name').dispatch('input');
await find('workspace-browse-project_directory').click();
assert.equal(find('workspace-field-project_directory').value,'C:\\software-qa\\QA_ Design');
assert.equal(find('workspace-form-submit').disabled,false);
await submit();await pending;
assert.equal(operations[0].body.project_directory,'C:\\software-qa\\QA_ Design');
assert.equal(requests[0].route,'workspace/folder-picker');assert.equal(requests[1].route,'workspace/folder-picker/software-qa-picker');
""")

    def test_cancelled_and_failed_picker_leave_manual_entry_available(self):
        self.run_client(r"""
for(const status of ['Cancelled','Failed']) {
  responder=async()=>({picker:{id:'software-qa-picker',status,directory:null,message:'SOFTWARE QA chooser unavailable'}});
  const pending=manager.openDirectory();
  await find('workspace-browse-directory').click();assert.equal(find('workspace-form-submit').disabled,false);
  assert.match(find('workspace-folder-status').textContent,status==='Cancelled'?/cancelled/:/SOFTWARE QA chooser unavailable/);
  find('workspace-field-directory').value='C:\\software-qa\\existing';await submit();await pending;
  assert.equal(operations.at(-1).action,'open-directory');assert.equal(operations.at(-1).body.directory,'C:\\software-qa\\existing');
}
""")

    def test_closing_form_stops_picker_polling_without_project_operation(self):
        self.run_client(r"""
let finish;responder=route=>route==='workspace/folder-picker'?new Promise(resolve=>finish=resolve):Promise.resolve({picker:{id:'software-qa-picker',status:'Cancelled'}});
const pending=manager.newProject(),dialog=manager.formDialog;
const browse=find('workspace-browse-project_directory').click();
dialog.close('cancel');await pending;
finish({picker:{id:'software-qa-picker',status:'Pending',directory:null}});await browse;
assert.equal(requests.length,2);assert.equal(requests[1].route,'workspace/cancel-folder-picker');
assert.equal(requests[1].body.picker_id,'software-qa-picker');assert.equal(operations.length,0);assert.equal(manager.formDialog,null);
""")

    def test_delete_confirmation_names_exact_project_and_count_and_cancel_sends_nothing(self):
        self.run_client(r"""
const project={id:'project-software-qa',name:'Exact QA name <unchanged>',management_revision:'project-revision',systems:[{id:'one'},{id:'two'}]};
manager.data.active={project_id:project.id,session_id:session};
const pending=manager.deleteProject(project),dialog=manager.formDialog;
const text=descend(dialog).map(node=>node.text||'').join(' ');
assert.match(text,/Exact QA name <unchanged>/);assert.match(text,/2 systems/);assert.match(text,/folder, RTL, results and history stay in place/);
assert.equal(find('workspace-form-submit').text,'Move to Trash');
dialog.close('cancel');await pending;assert.equal(operations.length,0);
""")

    def test_delete_submits_captured_project_revision_and_never_filesystem_paths(self):
        self.run_client(r"""
const project={id:'project-software-qa',name:'QA',directory:'C:\QA\retained',management_revision:'shown-revision',systems:[{}]};
manager.data.active={project_id:project.id,session_id:session};
const pending=manager.deleteProject(project);
project.management_revision='later-changed';
await submit();await pending;
assert.deepEqual(normalized(operations),[{action:'delete-project',body:{project_id:'project-software-qa',expected_project_revision:'shown-revision'}}]);
assert.equal(manager.tab,'trash');assert.equal(manager.formDialog,null);
""")

    def test_trash_restore_is_explicit_and_retains_pinned_identity(self):
        self.run_client(r"""
manager.data.trash=[{id:'trash-software-qa',deleted_at:'2026-10-15T00:00:00Z',project:{id:'project-retained',name:'Retained QA',directory:'C:\QA\retained',management_revision:'retained-revision',systems:[{}]}}];
const host=el('div');manager.renderTrash(host);
assert.equal(operations.length,0);
const button=descend(host).find(node=>node['data-testid']==='workspace-restore-trash-software-qa');
assert.equal(button.text,'Restore project');await button.click();
assert.deepEqual(normalized(operations),[{action:'restore-project',body:{trash_id:'trash-software-qa',expected_project_revision:'retained-revision'}}]);
assert.equal(descend(host).some(node=>/purge|permanent|delete files/i.test(node.text||'')),false);
""")

    def test_timed_out_open_refreshes_inside_modal_then_reconnects_explicitly_without_resending(self):
        self.run_client(r"""
// Use the real production operation path for this recovery-only regression.
manager.operate=sandbox.WorkspaceManager.prototype.operate.bind(manager);
const project={id:'software-qa-project',name:'Software QA',systems:[{id:'software-qa-system'}]};
const oldIdentity={session_id:session,project_id:null,system_id:null,read_only:false};
manager.receive({projects:[project],active:oldIdentity},true);manager.dialog.showModal();
const activations=[],draft={software_qa_unsaved:'KEEP EXACT DRAFT'};const before=JSON.stringify(draft);
let leaves=0;manager.callbacks.beforeLeave=async()=>{leaves++;return true;};manager.callbacks.activate=value=>activations.push(value);
responder=async()=>{throw new Error('SOFTWARE QA timeout; operation may already have completed. Refresh Projects.');};
await manager.open(project,project.systems[0]);
assert.equal(requests.length,1);assert.equal(requests[0].route,'workspace/open');assert.equal(activations.length,0);
assert.equal(session,oldIdentity.session_id);assert.equal(manager.dialog.open,true);
const refresh=manager.content.querySelector('[data-testid="workspace-refresh-projects"]');
assert.ok(refresh);assert.equal(refresh.text,'Refresh Projects');assert.equal(refresh.disabled,false);
const completedIdentity={session_id:'software-qa-completed-open',project_id:project.id,system_id:project.systems[0].id,read_only:false};
responder=async()=>({projects:[project],active:completedIdentity});await refresh.click();
assert.equal(requests.length,2);assert.equal(requests[1].route,'workspace');assert.equal(requests[1].body,undefined);
assert.equal(session,oldIdentity.session_id);assert.equal(activations.length,0);assert.equal(manager.contextCurrent(),false);
const reconnect=manager.content.querySelector('[data-testid="workspace-reconnect"]');assert.ok(reconnect);
await reconnect.click();assert.equal(session,completedIdentity.session_id);assert.equal(activations.length,1);
assert.equal(activations[0].workspace.active.session_id,completedIdentity.session_id);assert.equal(leaves,2);
assert.equal(requests.length,2);assert.equal(JSON.stringify(draft),before);
assert.equal(requests.some(item=>/workflow|generation|probe/.test(item.route)),false);
assert.equal(operations.length,0);
""")


    def test_array_variant_command_creates_only_explicit_fresh_project_request(self):
        self.run_client(r"""
const design={nodes:[...['00','01','10','11'].map(index=>({id:'npu2-pe'+index})),...Array.from({length:7},(_,index)=>({id:'other-'+index}))]};
const project={id:'source-project',name:'Original',systems:[{id:'source-system'}]};
manager.data={projects:[project],active:{project_id:project.id,system_id:'source-system',session_id:session},library:[],recent:[],trash:[]};
manager.callbacks.project=()=>({design});assert.equal(manager.arrayVariantAvailable(),true);
const before=JSON.stringify(design),commands=[];
manager.form=async(title,fields,description,label)=>{assert.equal(label,'Create separate project');assert.match(description,/does not modify the original project/);return {name:'New PE array'};};
manager.operate=async(action,body,options)=>commands.push({action,body,options});
assert.equal(commands.length,0);await manager.newArrayVariant();assert.equal(commands.length,1);
assert.equal(commands[0].action,'array-variant');assert.deepEqual(normalized(commands[0].body),{project_id:'source-project',system_id:'source-system',name:'New PE array'});
assert.equal(commands[0].options.context,true);assert.equal(commands[0].options.protect,true);
assert.equal(Object.hasOwn(commands[0].body,'results'),false);assert.equal(JSON.stringify(design),before);
""")

    def test_array_variant_unavailable_on_unsupported_or_changed_workspace(self):
        self.run_client(r"""
const nodes=[...['00','01','10','11'].map(index=>({id:'npu2-pe'+index})),...Array.from({length:7},(_,index)=>({id:'other-'+index}))];
let design={nodes};manager.callbacks.project=()=>({design});
manager.data.active={project_id:'source-project',system_id:'source-system',session_id:session};
assert.equal(manager.arrayVariantAvailable(),true);
design={nodes:nodes.slice(1)};assert.equal(manager.arrayVariantAvailable(),false);
design={nodes:nodes.map(node=>node.id==='npu2-pe00'?{...node,instance_array:{rows:2,columns:2}}:node)};assert.equal(manager.arrayVariantAvailable(),false);
design={nodes};manager.data.active.session_id='other-session';assert.equal(manager.arrayVariantAvailable(),false);
manager.data.active=null;assert.equal(manager.arrayVariantAvailable(),false);
await manager.newArrayVariant();assert.equal(operations.length,0);assert.equal(requests.length,0);
""")


if __name__ == "__main__":
    unittest.main()
