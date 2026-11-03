"""Connection labels update in place; isolated real GUI modules, no live API."""
import shutil
import subprocess
import unittest

from test_visual_navigation import CLIENT, PROJECT

EXPOSE = CLIENT.replace(
    'setNavigate:callback=>{setStage=callback;}',
    'connectionBuilder,refreshConnectionChoices,nodeFields,portFields,arrayFields,mutate,'
    'setDisplayHooks:hooks=>{syncChrome=hooks.chrome;renderHierarchy=hooks.hierarchy;'
    'renderReview=hooks.review;autosave=hooks.autosave;render=hooks.render;flushActiveField=()=>{};},'
    'setNavigate:callback=>{setStage=callback;}')

SETUP = r"""
Object.defineProperty(DOMNode.prototype,'value',{get(){return this._value??this.attributes.value??'';},set(value){this._value=String(value);},configurable:true});
qa.state.design.settings={clock_name:'clock_i',reset_name:'reset_i'};
for(const [index,node] of qa.state.design.nodes.entries()){
 node.constraints={latency_cycles:1,protocol:'valid_ready'};node.behavior='';node.test_expectations='';
 node.ports=[{id:'input-'+index,name:'data_in',direction:'input',width:32,signed:true,protocol:'valid_ready',clock:'clock_i',reset:'reset_i'},
 {id:'output-'+index,name:'data_out',direction:'output',width:32,signed:true,protocol:'valid_ready',clock:'clock_i',reset:'reset_i'}];
}
qa.state.saved=structuredClone(qa.state.design);qa.state.selected={kind:'node',id:'node-b',ids:['node-b']};
qa.state.verificationDrafts={'node-b':{text:'{unfinished verification text',pending:true,error:'retained'}};
const calls=[];qa.setDisplayHooks({chrome:()=>calls.push('chrome'),hierarchy:()=>calls.push('hierarchy'),review:()=>calls.push('review'),autosave:()=>calls.push('browser-backup'),render:()=>calls.push('full-render')});
qa.state.graph={update:()=>calls.push('graph')};
const host=qa.connectionBuilder();elements.set('qa-connection-host',host);for(const control of host.querySelectorAll('select'))elements.set(control.id,control);
const from=host.querySelector('[data-testid="new-edge-source"]'),to=host.querySelector('[data-testid="new-edge-target"]');
const sourceValue=JSON.stringify(['node-b','output-1']),targetValue=JSON.stringify(['node-a','input-0']);from.value=sourceValue;to.value=targetValue;
const edit=(host,id,value)=>{const control=host.querySelector(`[data-testid="${id}"]`);assert.ok(control,id);control.value=value;document.activeElement=control;control.selectionStart=2;control.selectionEnd=4;for(const callback of control.listeners.input||control.listeners.change||[])callback();return control;};
"""


class ConnectionChoiceClientTests(unittest.TestCase):
    def client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated connection-label checks.')
        result = subprocess.run([node, '--experimental-vm-modules', '-e', EXPOSE +
                                 '\n(async()=>{const qa=await initialize();\n' + SETUP + body +
                                 '\nassert.equal(requests.length,0);})().catch(e=>{console.error(e.stack||e);process.exitCode=1;});'],
                                cwd=PROJECT, capture_output=True, text=True, encoding='utf-8', timeout=25)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_node_and_port_edits_update_options_without_replacing_active_fields_or_selection(self):
        self.client(r"""
const selected=qa.state.selected,draft=JSON.stringify(qa.state.verificationDrafts),fields=qa.nodeFields(qa.state.design.nodes[1]);
const option=from.children.find(item=>item.value===sourceValue),active=edit(fields,'node-name','Rotate register');
assert.equal(document.activeElement,active);assert.equal(active.selectionStart,2);assert.equal(active.selectionEnd,4);
assert.equal(from.children.find(item=>item.value===sourceValue),option);assert.match(option.textContent,/Rotate register.data_out.*32 bits/);
assert.equal(from.value,sourceValue);assert.equal(to.value,targetValue);assert.equal(qa.state.selected,selected);assert.equal(JSON.stringify(qa.state.verificationDrafts),draft);
const output=qa.state.design.nodes[1].ports[1],outputFields=qa.portFields(qa.state.design.nodes[1],output);
edit(outputFields,'port-name-output-1','output_data');const width=edit(outputFields,'port-width-output-1','8');
assert.equal(document.activeElement,width);assert.match(option.textContent,/Rotate register.output_data.*8 bits/);assert.doesNotMatch(option.textContent,/data_out|32 bits/);
const signed=outputFields.querySelector('#port-signed-output-1');signed.value='false';for(const callback of signed.listeners.change)callback();
assert.equal(output.signed,false);assert.equal(from.value,sourceValue);assert.equal(to.value,targetValue);assert.equal(JSON.stringify(qa.state.verificationDrafts),draft);assert.equal(calls.includes('full-render'),false);
""")

    def test_connect_reads_retained_live_endpoint_selection_and_same_option_objects(self):
        self.client(r"""
const beforeSource=from.children.find(option=>option.value===sourceValue),beforeTarget=to.children.find(option=>option.value===targetValue);
qa.mutate(design=>{design.nodes[0].name='XOR register';design.nodes[0].ports[0].name='input_data';design.nodes[0].ports[0].width=8;},false);
assert.equal(from.children.find(option=>option.value===sourceValue),beforeSource);assert.equal(to.children.find(option=>option.value===targetValue),beforeTarget);
assert.match(beforeTarget.textContent,/XOR register.input_data.*8 bits/);host.querySelector('[data-testid="add-edge"]').click();
assert.equal(qa.state.design.edges.length,1);assert.deepEqual(JSON.parse(JSON.stringify(qa.state.design.edges[0].source)),{node_id:'node-b',port_id:'output-1'});assert.deepEqual(JSON.parse(JSON.stringify(qa.state.design.edges[0].target)),{node_id:'node-a',port_id:'input-0'});
""")

    def test_invalid_endpoint_selection_resets_only_to_existing_choice_and_empty_lists_disable_connect(self):
        self.client(r"""
from.value='removed endpoint';qa.refreshConnectionChoices();assert.ok(from.children.some(option=>option.value===from.value));
qa.state.design.nodes[1].ports[1].name='renamed';qa.refreshConnectionChoices();assert.ok(from.children.some(option=>option.value===from.value));assert.equal(to.value,targetValue);
qa.state.design.nodes.forEach(node=>node.ports=node.ports.filter(port=>port.direction==='input'));qa.refreshConnectionChoices();assert.equal(from.value,'');assert.equal(from.disabled,true);assert.equal(host.querySelector('[data-testid="add-edge"]').disabled,true);
""")

    def test_array_help_distinguishes_historical_npu_limit_from_generic_contract_configuration(self):
        self.client(r"""
let fields=qa.arrayFields(qa.state.design.nodes[1]);let help=fields.querySelector('[data-testid="array-profile-help"]').textContent;
assert.match(help,/historical NPU profile.*2 × 2 PE/);assert.match(help,/configure the generic cycle-vector system contract in Specifications/);assert.match(help,/1–16 rows and columns/);
qa.state.design.global_verification={kind:'generic_cycle_vectors'};fields=qa.arrayFields(qa.state.design.nodes[1]);help=fields.querySelector('[data-testid="array-profile-help"]').textContent;
assert.match(help,/selected generic cycle-vector profile.*1–16/);assert.match(help,/independent system expectations/);assert.match(help,/no verification result/);assert.equal(calls.length,0);
""")


if __name__ == '__main__':
    unittest.main()
