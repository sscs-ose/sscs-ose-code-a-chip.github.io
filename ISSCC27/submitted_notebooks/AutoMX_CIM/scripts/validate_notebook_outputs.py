"""Execute output/report/definition cells without repeating the long EDA flow."""
from pathlib import Path
from datetime import datetime,timezone
import ast,json,shutil,time,copy,sys
import nbformat
from nbclient import NotebookClient

b=Path(__file__).resolve().parents[1];sys.path.insert(0,str(b))
from scripts.enrich_cim_notebook import enrich
original=nbformat.read(b/'AutoMX_CIM_Code_a_Chip.ipynb',4)
book=enrich(original)
folder=b/'diagnostics'/('output_validation_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
folder.mkdir();nbformat.write(book,folder/'candidate.ipynb')
last=json.loads((b/'LATEST_RUN.json').read_text());measured=Path(last['run'])/'full_native/full_native'
source={c.id:c for c in book.cells}
pre=nbformat.v4.new_code_cell('''from pathlib import Path
import os,json,types,numpy as np
from IPython.display import display,Markdown,Image
os.environ['AUTOMX_FULL_NATIVE']='on'
os.environ['AUTOMX_CIM_ROOT']='''+repr(str(b))+'''
os.environ['AUTOMX_RUNALL_CACHE']='''+repr(str(folder/'work'))+'''
os.environ['AUTOMX_RUNALL_TAG']='output_check'
_bundle=Path('''+repr(str(b))+''')
''',id='output-test-context')
cells=[pre,copy.deepcopy(source['argument-bootstrap']),copy.deepcopy(source['standalone-runtime']),
 nbformat.v4.new_code_cell("_design_review_namespace.update(BUNDLE=_bundle,OUT=Path("+repr(str(folder))+"),BASE=_bundle,Path=Path,np=np,RTL_FIELDS=('sample','sample_n','result','eoc','eoc_osr','pr','pro','pc','pb','p0','nr','nro','nc','nb','n0'))\n",id='output-namespace'),
 copy.deepcopy(source['full-lab-config'])]
config=copy.deepcopy(source['native-runall-config']);config.id='output-registry'
config.source=config.source.rsplit('portable.start(ROOT,WORK)',1)[0]
cells.append(config)
real=[]
for c in book.cells:
 if c.cell_type!='code':continue
 cid=c.id
 use=cid.startswith('native-inline-')
 use|=cid.startswith('native-restored-archive-') or cid in ['native-story-decoder_errors','native-story-routing_progress','raw-reader','rtl-testbench','klayout-script']
 if use:
  cells.append(copy.deepcopy(c));real.append(cid)
  if cid=='native-inline-support':
   # Real numerical records are copied verbatim into the report reader's test directory.
   context="_verified_work=Path("+repr(str(measured))+")\n"
   context+="for _rel in ['area_comparison.json','mha_end_to_end.json','cold_pnr/step.json','render_top/top.render.json','render_top/top.png']:\n    _dest=flow.work/_rel;_dest.parent.mkdir(parents=True,exist_ok=True);__import__('shutil').copy2(_verified_work/_rel,_dest)\n"
   context+="flow.outputs.update(json.loads((_verified_work/'runall_manifest.json').read_text())['views'])\n"
   cells.append(nbformat.v4.new_code_cell(context,id='output-measured-record-context'))
for c in book.cells:
 if c.cell_type=='code' and c.id.startswith('native-restored-server-flow-'):
  cells.append(copy.deepcopy(c));real.append(c.id)
tooltest=r'''probe=flow.work/'output_probe.txt'
probe_code="print('verbose detail');print('Number of cells: 7');open("+repr(str(probe))+",'w').write('ok')"
result=flow.run('output_probe',[__import__('sys').executable,'-c',probe_code],outputs=[probe])
assert result['returncode']==0 and probe.read_text()=='ok'
log=Path(result['log']['path']).read_text();assert 'verbose detail' in log and 'Number of cells: 7' in log
try:
    flow.run('output_probe_error',[__import__('sys').executable,'-c',"print('failure detail');raise SystemExit(3)"])
except RuntimeError:
    assert 'failure detail' in (flow.work/'output_probe_error/native.log').read_text()
else:raise AssertionError('Tool failure was swallowed')
'''
cells.append(nbformat.v4.new_code_cell(tooltest,id='output-tool-check'))
cells.append(nbformat.v4.new_code_cell("flow.work=_verified_work\n_design_review_namespace.update(BASE=Path("+repr(str(folder/'export_view'))+"),E={})\n",id='output-export-context'))
cells.append(copy.deepcopy(source['standalone-sync-physical']))
real.append('standalone-sync-physical')
subset=nbformat.v4.new_notebook(cells=cells)
for c in subset.cells:
 c.outputs=[];c.execution_count=None;c.metadata.pop('execution',None)
start=time.monotonic();status='FAILED'
try:
 NotebookClient(subset,timeout=150,kernel_name='python3',allow_errors=False,resources={'metadata':{'path':str(b)}}).execute()
 status='PASSED'
finally:
 nbformat.write(subset,folder/'outputs.executed.ipynb')
 report={'status':status,'checked_utc':datetime.now(timezone.utc).isoformat(),'elapsed_s':time.monotonic()-start,
  'validation_mode':'Output/report/definition cells and real subprocess logging; SPICE/PnR results retained from verified full run.',
  'notebook':str(folder/'outputs.executed.ipynb'),'candidate':str(folder/'candidate.ipynb'),'real_cell_ids':real,
  'executed_cells':sum(c.execution_count is not None for c in subset.cells),
  'errors':[{'cell':c.id,'error':o.get('evalue')} for c in subset.cells for o in c.outputs if o.output_type=='error'],
  'tables':sum('text/markdown' in o.get('data',{}) for c in subset.cells for o in c.outputs),
  'plots':sum('image/png' in o.get('data',{}) for c in subset.cells for o in c.outputs)}
 (b/'docs/output_validation_20261027.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2),flush=True)
