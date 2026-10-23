"""Execute notebook using this interpreter, export HTML and verify artifacts."""
from pathlib import Path
import json,os,sys,time,subprocess,hashlib
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',MPLBACKEND='Agg')
os.environ['JUPYTER_PATH']=str(Path(sys.prefix)/'share/jupyter')
runtime=Path(__file__).resolve().parent/'reruns/jupyter_runtime'
runtime.mkdir(parents=True,exist_ok=True)
os.environ['TMP']=str(runtime)
os.environ['TEMP']=str(runtime)
os.environ['JUPYTER_RUNTIME_DIR']=str(runtime)
os.environ['MPLCONFIGDIR']=str(runtime/'matplotlib')
import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager
P=Path(__file__).resolve().parent
if len(sys.argv)>1:P=Path(sys.argv[1]).resolve()
t=time.perf_counter()
nb=nbformat.read(P/'Trust_Before_Pass.ipynb',as_version=4)
km=KernelManager(kernel_name='python3')
km.kernel_spec.argv=[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}']
client=NotebookClient(nb,timeout=60,startup_timeout=30,resources={'metadata':{'path':str(P)}},km=km)
client.execute(cwd=str(P))
km.shutdown_kernel(now=True)
nbformat.validate(nb)
nbformat.write(nb,P/'Trust_Before_Pass.ipynb')
html,_=HTMLExporter().from_notebook_node(nb)
(P/'Trust_Before_Pass.html').write_text(html,encoding='utf-8')
errors=[o for c in nb.cells if c.cell_type=='code' for o in c.get('outputs',[]) if o.output_type=='error']
assert not errors
assert all(c.execution_count for c in nb.cells if c.cell_type=='code')
figs=[]
import base64
for c in nb.cells:
    for o in c.get('outputs',[]):
        if 'image/png' in o.get('data',{}):
            f=P/'figures'/('figure_'+str(len(figs)+1)+'.png');f.parent.mkdir(exist_ok=True)
            f.write_bytes(base64.b64decode(o['data']['image/png']));figs.append(f.name)
tests=subprocess.run([sys.executable,'-m','unittest','discover','-v','-s',str(P),'-p','test_*.py'],cwd=P,capture_output=True,text=True)
assert tests.returncode==0,tests.stderr
(P/'validation_tests.log').write_text(tests.stdout+tests.stderr,encoding='utf-8')
import re
test_count=int(re.search(r'Ran (\d+) tests',tests.stderr).group(1))
record={'release':nb.metadata['trust_before_pass']['version'],'python':sys.version,'notebook_cells':len(nb.cells),'executed_code_cells':sum(c.cell_type=='code' for c in nb.cells),
        'errors':len(errors),'figures':figs,'wall_s':time.perf_counter()-t,'tests_passed':test_count,
        'interaction_validation':'Finite browser payload checked against current Python; actual browser validation recorded separately. No human trial. Default notebook leaves learner tasks unanswered.',
        'executable':sys.executable,'prefix':sys.prefix,'base_prefix':sys.base_prefix,
        'scope':'Fresh notebook kernel using the explicitly selected interpreter. Dependency isolation recorded separately; not a fresh OS or Linux validation.'}
(P/'VALIDATION.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
