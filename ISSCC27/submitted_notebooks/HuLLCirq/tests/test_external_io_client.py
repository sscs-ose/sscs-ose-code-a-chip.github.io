"""Bounded client draft/graph fixtures, never actual GUI/circuit qualification."""
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
class DOMDouble {
 constructor(tag,attrs={}){this.tag=tag;this.children=[];this.attributes={};this.listeners={};Object.assign(this,attrs);this.classList={add(){},remove(){}};}
 append(...children){this.children.push(...children.flat(Infinity).filter(x=>x!==null&&x!==undefined&&x!==false));}
 replaceChildren(...children){this.children=[];this.append(...children);}
 setAttribute(key,value){this.attributes[key]=String(value);}
 addEventListener(key,value){this.listeners[key]=value;}
 querySelector(){return null;}
}
const el=(tag,attrs={},...children)=>{const n=new DOMDouble(tag,attrs);n.append(...children);return n;};
const source=file=>fs.readFileSync('src/gui/'+file,'utf8').replace(/^import[^\n]*\n/gm,'').replace(/\bexport (?=(function|const|class)\b)/g,'');
const sandbox={el,element:el,svgElement:el,badge:text=>el('span',{text}),field:(label,value,change,options)=>el('field',{label,value,change,...options}),structuredClone,console,window:{addEventListener(){}},AbortController};
vm.createContext(sandbox);
vm.runInContext(source('design_instances.js')+'\n'+source('external_io.js')+'\n'+source('graph.js')+'\nglobalThis.c={hasExternalIO,blankExternalIO,externalPorts,expandedExternalPorts,externalEndpointChoices,parseGraphEndpoint,externalBindingLabel,externalConnectionProblem,externalArrayResizeProblem,externalBlocks,renderExternalInspector,GraphEditor};',sandbox);
const c=sandbox.c,plain=x=>JSON.parse(JSON.stringify(x));
const port=(id,name,direction,width=4)=>({id,name,direction,width,signed:false,protocol:'valid_ready',clock:'clk',reset:'rst'});
const design=()=>({settings:{clock_name:'clk',reset_name:'rst'},nodes:[{id:'counter',name:'Counter',module_name:'counter',ports:[port('in','data_in','input'),port('out','data_out','output')]}],edges:[],layout:{nodes:{counter:{x:300,y:100}},viewport:{x:0,y:0,zoom:1}}});
const exterior=(id,name,direction,width=4)=>({id,name,direction,width,signed:false,protocol:'valid_ready'});
const descendants=n=>[n,...n.children.filter(x=>x instanceof DOMDouble).flatMap(descendants)];
"""


class ExternalIOClientTests(unittest.TestCase):
    def run_client(self, body):
        node = shutil.which('node')
        if not node:
            self.skipTest('Node is required for isolated client fixtures.')
        completed = subprocess.run([node, '-e', CLIENT + '\n' + body], cwd=ROOT,
                                   capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_legacy_is_not_mutated_or_given_implicit_boundaries(self):
        self.run_client("const d=design(), before=JSON.stringify(d); assert.equal(c.hasExternalIO(d),false); assert.deepEqual(plain(c.externalBlocks(d)),[]); assert.deepEqual(plain(c.expandedExternalPorts(d)),[]); assert.equal(JSON.stringify(d),before);")

    def test_two_virtual_blocks_never_increase_dut_node_count(self):
        self.run_client("const d=design();d.external_io=c.blankExternalIO();const before=JSON.stringify(d), blocks=c.externalBlocks(d);assert.equal(blocks.length,2);assert.deepEqual(plain(blocks.map(x=>x.direction)),['input','output']);assert.equal(d.nodes.length,1);assert.equal(JSON.stringify(d),before);assert(blocks[0].x+blocks[0].width<d.layout.nodes.counter.x);")

    def test_stream_expansion_preserves_reverse_ready_direction(self):
        self.run_client("const d=design();d.external_io={version:1,ports:[exterior('a','data_in','input'),exterior('b','data_out','output')],connections:[]};assert.deepEqual(plain(c.expandedExternalPorts(d)),[{name:'data_in',direction:'input',width:4,signed:false},{name:'data_in_valid',direction:'input',width:1,signed:false},{name:'data_in_ready',direction:'output',width:1,signed:false},{name:'data_out',direction:'output',width:4,signed:false},{name:'data_out_valid',direction:'output',width:1,signed:false},{name:'data_out_ready',direction:'input',width:1,signed:false}]);")

    def test_binding_uses_exact_endpoint_and_rejects_type_or_duplicate(self):
        self.run_client("const d=design();d.external_io={version:1,ports:[exterior('a','data_in','input')],connections:[]};const endpoint={node_id:'counter',port_id:'in'};assert.equal(c.externalConnectionProblem(d,'a',endpoint),'');d.external_io.ports[0].width=8;assert.match(c.externalConnectionProblem(d,'a',endpoint),/same width/);d.external_io.ports[0].width=4;d.external_io.connections.push({id:'b',external_port_id:'a',...endpoint});assert.match(c.externalConnectionProblem(d,'a',endpoint),/already bound/);")

    def test_array_binding_and_resize_protection(self):
        self.run_client("const d=design();d.nodes[0].instance_array={rows:2,columns:2};d.external_io={version:1,ports:[exterior('a','lane','input')],connections:[]};assert.match(c.externalConnectionProblem(d,'a',{node_id:'counter',port_id:'in'}),/exact existing/);const endpoint={node_id:'counter',port_id:'in',instance_index:[1,1]};assert.equal(c.externalConnectionProblem(d,'a',endpoint),'');d.external_io.connections.push({id:'b',external_port_id:'a',...endpoint});assert.match(c.externalArrayResizeProblem(d,'counter',{rows:1,columns:1}),/External terminals/);assert.equal(c.externalArrayResizeProblem(d,'counter',{rows:2,columns:2}),'');")

    def test_canvas_draws_boundaries_and_external_binding(self):
        self.run_client("const d=design();d.external_io={version:1,ports:[exterior('a','data_in','input')],connections:[{id:'b',external_port_id:'a',node_id:'counter',port_id:'in'}]};const editor=new c.GraphEditor(el('host'),{});editor.update(d,null);const all=descendants(editor.viewport);assert.equal(all.filter(x=>x['data-testid']?.startsWith('external-block-')).length,2);assert.equal(all.filter(x=>x['data-external-binding-id']==='b').length,1);assert.equal(d.nodes.length,1);")

    def test_canvas_click_connects_external_input_and_output(self):
        self.run_client("const d=design();d.external_io={version:1,ports:[exterior('a','data_in','input'),exterior('b','data_out','output')],connections:[]};const added=[],event={stopPropagation(){}};const editor=new c.GraphEditor(el('host'),{select(){},addExternalBinding:(id,endpoint)=>added.push({id,endpoint})});editor.update(d,null);const target=name=>descendants(editor.viewport).find(x=>x['aria-label']===name);target('External input port data_in, 4 bits').listeners.click(event);target('Counter input port data_in, 4 bits').listeners.click(event);target('Counter output port data_out, 4 bits').listeners.click(event);target('External output port data_out, 4 bits').listeners.click(event);assert.deepEqual(plain(added),[{id:'a',endpoint:{node_id:'counter',port_id:'in'}},{id:'b',endpoint:{node_id:'counter',port_id:'out'}}]);")

    def test_default_view_fits_symbols_without_edit_and_pan_undo_keeps_original(self):
        self.run_client("const d=design();d.external_io=c.blankExternalIO();const before=JSON.stringify(d),committed=[];const editor=new c.GraphEditor(el('host'),{commitLayout:x=>committed.push(x)});editor.svg.getBoundingClientRect=()=>({width:600,height:400});editor.update(d,null);assert.equal(JSON.stringify(d),before);const blocks=c.externalBlocks(d),v=editor.renderedView;assert(blocks.every(b=>b.x*v.zoom+v.x>=0&&(b.x+b.width)*v.zoom+v.x<=600));editor.startPan({clientX:0,clientY:0});editor.activePointer.moved=true;editor.endPointer();assert.deepEqual(plain(committed[0].viewport),{x:0,y:0,zoom:1});assert.equal(JSON.stringify(d),before);")

    def test_inspector_and_missing_binding_remain_repairable(self):
        self.run_client("const d=design();d.external_io={version:1,ports:[],connections:[{id:'broken',external_port_id:'missing',node_id:'counter',port_id:'in'}]};const host=el('host');c.renderExternalInspector(host,d,{direction:'input'},{});const all=descendants(host);assert(all.some(x=>x.text==='Remove invalid external connection'));assert(all.some(x=>x.text==='+ Add external input'));assert.match(c.externalBindingLabel(d,d.external_io.connections[0]),/Missing external/);")


if __name__ == '__main__':
    unittest.main()
