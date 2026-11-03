"""Evaluate the real GUI module graph up to startup, without a browser or API."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLIENT = r"""
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict');
const directory=path.resolve('src/gui'),html=fs.readFileSync(path.join(directory,'index.html'),'utf8');
const ids=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(match=>[match[1],{addEventListener(){},dataset:{},children:[]}]))
const context=vm.createContext({console,structuredClone,URL,crypto:{randomUUID:()=> 'software-only'},
 document:{getElementById:id=>{assert.ok(ids.has(id),`Startup requires missing DOM id ${id}`);return ids.get(id);}},
 setTimeout(){throw Error('Module initialization must not schedule an execution before start');},
 fetch(){throw Error('No API is permitted in module initialization QA');}});
const modules=new Map();
function load(file){
 file=path.resolve(file);assert.ok(file.startsWith(directory+path.sep),'Relative imports must stay in the GUI folder');
 if(modules.has(file))return modules.get(file);
 let source=fs.readFileSync(file,'utf8');
 if(path.basename(file)==='app.js'){
   assert.match(source,/\nstart\(\);\s*$/);
   source=source.replace(/\nstart\(\);\s*$/,'\nglobalThis.moduleInitializationComplete=true;');
 }
 const module=new vm.SourceTextModule(source,{context,identifier:file});modules.set(file,module);return module;
}
(async()=>{
 const app=load(path.join(directory,'app.js'));
 await app.link((specifier,referrer)=>{assert.ok(specifier.startsWith('./'));return load(path.resolve(path.dirname(referrer.identifier),specifier));});
 await app.evaluate();assert.equal(context.moduleInitializationComplete,true);
 assert.ok(modules.has(path.join(directory,'generation_batch.js')));
 assert.ok(modules.has(path.join(directory,'flow_guidance.js')));
 console.log(JSON.stringify({scope:'real ESM graph linked and initialized; start deliberately suppressed; no API/model/EDA',module_count:modules.size,status:'Passed'}));
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
"""


class GuiStartupImportTests(unittest.TestCase):
    def test_real_module_imports_exports_and_synchronous_initialization(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("Node is required for module initialization QA.")
        result = subprocess.run([node, "--experimental-vm-modules", "-e", CLIENT], cwd=ROOT,
                                capture_output=True, text=True, encoding="utf-8", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"status":"Passed"', result.stdout)


if __name__ == "__main__":
    unittest.main()
