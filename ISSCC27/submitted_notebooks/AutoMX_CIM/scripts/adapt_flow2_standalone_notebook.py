"""Port the existing 260-cell notebook to bundled inputs and fresh measurements."""
from pathlib import Path
import ast,copy,json,shutil,textwrap,sys
import nbformat as nbf
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
DEST=Path('/media/nam/EDABK/AutoMX_CIM_standalone_20261024')

SETUP=r'''
from pathlib import Path
import os,json,re,copy,tempfile,time,subprocess,shutil,gzip,sys
from datetime import datetime,timezone
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display,Markdown,Image
BUNDLE=Path(os.environ.get('AUTOMX_BUNDLE_DIR','.')).resolve()
if not (BUNDLE/'standalone.json').is_file():raise FileNotFoundError('Open Jupyter from the standalone laboratory folder')
OUT=BUNDLE/'runs'/('fresh_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
OUT.mkdir(parents=True,exist_ok=False)
BASE=OUT/'review_data';BASE.mkdir()
(BASE/'rtl').symlink_to(BUNDLE/'third_party/SKY130_SAR_ADC1/mixed_signal_partition/verilog/rtl')
E={};NATIVE=os.environ.get('AUTOMX_REVIEW_NATIVE','on').lower()
plt.rcParams.update({'figure.dpi':120,'axes.spines.top':False,'axes.spines.right':False,'font.size':10})
def table(headers,rows):
    display(Markdown('| '+' | '.join(map(str,headers))+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+'\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)))
def record(path):return json.loads((BASE/path).read_text())
def savefig(name):
    plt.tight_layout();plt.savefig(OUT/name,bbox_inches='tight');plt.show();plt.close()
print('STANDALONE FRESH RUN — no stored conversion records or routed top checkpoint.')
print('Source IP and tool inputs:',BUNDLE)
print('New empty output folder:',OUT)
print('Python:',sys.executable)
'''

EXPERIMENT_INIT=r'''
def __init__(self,flow):
    self.flow=flow;self.root=flow.root;self.references={};self.calibration_keys=set();self.required=[]
    self.lib=flow.base/'tools/ngspice_shared44/install/lib/libngspice.so'
    if not self.lib.is_file():raise FileNotFoundError('Bundled shared ngspice runtime was not prepared')
    self.sources=[self.lib,*[self.root/'scripts'/f for f in ('flow2_rtl_spice_cosim.py','flow2_adc_partition.py')]]
    ip=self.root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition'
    manifest=json.loads((ip/'provenance.json').read_text())
    for source in manifest['files']:
        path=ip/source['path']
        if digest(path)!=source['sha256']:raise ValueError('Bundled pinned SAR source differs')
        self.sources.append(path)
    self.sources += [self.root/'inputs/core_acquisition.spice',self.root/'inputs/conditioner.spice',
        self.root/'pdks/analog/sky130A/libs.tech/ngspice/sky130.lib.spice']
'''

FLOW_CONTAINER=r'''
def container(self,program,args,name,work=None):
    from automx_standalone import container
    return container(self.root,program,args,'automx-'+self.settings.tag+'-'+name,work or self.work)
'''

def replace_function(source,name,text,cls=None):
    body=source.partition('\n')[2];tree=ast.parse(body.partition('# NOTEBOOK_RUN\n')[0])
    nodes=tree.body
    if cls:nodes=next(n for n in nodes if isinstance(n,ast.ClassDef) and n.name==cls).body
    node=next(n for n in nodes if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
    lines=body.splitlines(keepends=True);indent=' '*node.col_offset
    replacement=textwrap.indent(textwrap.dedent(text).strip(),indent)+'\n'
    body=''.join(lines[:node.lineno-1])+replacement+''.join(lines[node.end_lineno:])
    return source.splitlines()[0]+'\n'+body

def adapt(dest=DEST):
    dest=Path(dest);original=nbf.read(dest/'source_notebook.ipynb',4);book=copy.deepcopy(original)
    cells={c.id:c for c in book.cells}
    for c in book.cells:
        if c.cell_type=='code':c.outputs=[];c.execution_count=None;c.metadata.pop('execution',None)
    # The full runtime is in this cell, not a hidden import from the development checkout.
    loader='''\n@register_cell_magic\ndef standalone_runtime(line,cell):\n    module=_argument_types.ModuleType("automx_standalone")\n    module.__file__=str(__import__("pathlib").Path.cwd()/"scripts/standalone_runtime.py")\n    _argument_sys.modules[module.__name__]=module\n    exec(compile(cell,module.__file__,"exec"),module.__dict__)\n    get_ipython().user_ns["portable"]=module\n'''
    cells['argument-bootstrap'].source+=loader
    runtime=(ROOT/'scripts/standalone_runtime.py').read_text()
    runtime_cell=nbf.v4.new_code_cell('%%standalone_runtime\n'+runtime,id='standalone-runtime')
    book.cells.insert(book.cells.index(cells['setup']),runtime_cell)
    cells['setup'].source='%%design_review setup\n'+textwrap.dedent(SETUP).strip()+'\n'
    prepare=nbf.v4.new_code_cell('''from pathlib import Path
import os,json
_bundle=_design_review_namespace['BUNDLE']
os.environ['AUTOMX_CIM_ROOT']=str(_bundle)
os.environ['AUTOMX_FULL_NATIVE']='on'
_blocked_roots=portable.guard_old_checkout(_bundle)
print('External design inputs blocked:',len(_blocked_roots),'prefixes')
''',id='standalone-prepare')
    book.cells.insert(book.cells.index(cells['full-lab-config']),prepare)
    data=dest/'data';data.mkdir(exist_ok=True)
    source_data=ROOT/'submission/ISSCC27/submitted_notebooks/automx_cim/data'
    if not (source_data/'native_lab_cells.json').is_file():source_data=dest/'data'
    mapping=json.loads((source_data/'native_lab_cells.json').read_text())
    (data/'native_lab_cells.json').write_text(json.dumps(mapping,indent=2)+'\n')
    (data/'native_lab_outputs.json').write_text(json.dumps({r['original_id']:[] for r in mapping['cells'] if r['cell_type']=='code'})+'\n')
    cells['full-lab-config'].source=cells['full-lab-config'].source.replace("_lab_package = (_design_review_namespace['BASE']", "_lab_package = (_design_review_namespace['BUNDLE']")
    # The original native configuration creates the fresh session before starting cold PnR.
    cell=cells['native-runall-config']
    cell.source=cell.source.replace("'/home/nam/Vihn/interface_verify/fpga_export_18x18_mnist_softreset/test_folder/AutoMX-CIM'",'str(_bundle)')
    cell.source+='\nportable.start(ROOT,WORK)\n'
    # All helper imports resolve within the bundled source tree.
    for cid in ['native-inline-support']:
        prefix,body=cells[cid].source.partition('\n')[0],cells[cid].source.partition('\n')[2]
        body=replace_function(body,'container',FLOW_CONTAINER,cls='Flow')
        cells[cid].source=prefix+'\n'+body
    # Replace only the physical operations that formerly required a routed checkpoint.
    operations={'native-inline-physical_common':['inputs'],
        'native-runall-synthesis':['synthesize_sar','synthesize'],
        'native-runall-streamout':['streamout'],'native-runall-gds-audit':['audit_gds'],
        'native-runall-signal-lvs':['lvs'],'native-runall-power':['power'],
        'native-runall-timing':['timing','parse_library'],
        'native-runall-environment':['environment'],'native-runall-ngspice':['prepare_shared']}
    for cid,names in operations.items():
        c=cells[cid];original_body=c.source.partition('\n')[2]
        magic=original_body.splitlines()[0];invoke=original_body.partition('# NOTEBOOK_RUN\n')[2]
        c.source='%%native_lab '+c.metadata['automx_native_origin']['original_id']+'\n'+magic+'\nfrom automx_standalone import '+','.join(names)+'\n# NOTEBOOK_RUN\n'+invoke
    # Experiment preparation uses bundled schematic/model inputs rather than old result receipts.
    c=cells['native-runall-partition-sources'];first,_,body=c.source.partition('\n')
    c.source=first+'\n'+replace_function(body,'__init__',EXPERIMENT_INIT,cls='Experiment')
    # The subprocess netlist generator itself also uses bundled source IP.
    c=cells['native-inline-cosim'];first,_,body=c.source.partition('\n')
    body=body.replace("root=Path(root);_,data,views=source(root,'core_tap_pex_srv_20261022_01')", "root=Path(root);views={'schematic':root/'inputs/core_acquisition.spice'};data={'pdk':str(root/'pdks/analog/sky130A')}")
    body=body.replace("condition=json.loads((root/common.BASE/'mixed_wrapper_20261020_01_cond/summary.json').read_text())\n    condition=condition.get('block',condition)\n    cond=common._verified(root,condition['views']['schematic'])", "cond=root/'inputs/conditioner.spice'")
    c.source=first+'\n'+body
    # Fresh acquisition of all MHA transactions precedes independent validation of their records.
    moved=[cells['native-new-c49e894a'],cells['native-runall-measured-mha']]
    for c in moved:book.cells.remove(c)
    index=book.cells.index(cells['evidence-schema']);book.cells[index:index]=moved
    sync=nbf.v4.new_code_cell('portable.export_conversions(get_ipython().user_ns,_design_review_namespace)\n',id='standalone-sync-conversions')
    book.cells.insert(book.cells.index(cells['evidence-schema']),sync)
    factorial=nbf.v4.new_code_cell('portable.export_factorial(get_ipython().user_ns,_design_review_namespace)\n',id='standalone-sync-factorial')
    book.cells.insert(book.cells.index(cells['factorial-method']),factorial)
    physical=nbf.v4.new_code_cell('portable.export_physical(get_ipython().user_ns,_design_review_namespace)\n',id='standalone-sync-physical')
    book.cells.insert(book.cells.index(cells['physical-method']),physical)
    # The full route is now built from RTL; final publication has no old-route assertion.
    c=cells['native-runall-manifest'];c.source='%%native_lab runall-manifest\n%%inline_module publish\nfrom automx_standalone import publish\n# NOTEBOOK_RUN\nmanifest=publish.publish(flow,INLINE_SOURCES,history.REPLAY_RECORDS)\n'
    # All analysis output is labelled as current-run acquisition in this laboratory.
    for c in book.cells:
        if c.cell_type=='code' and c.id in ('validate-evidence','factorial-result','waveform','physical-reports','klayout-native','results'):
            c.source=c.source.replace('Recorded cohort','Fresh cohort').replace('Recorded ngspice','Current-run ngspice').replace('Recorded Icarus','Current-run Icarus').replace('Recorded OpenROAD','Current-run OpenROAD').replace('Recorded Netgen','Current-run Netgen').replace('Recorded KLayout','Current-run KLayout').replace('Recorded result','Current-run result').replace('Recorded coupled','Current-run coupled').replace('recorded native analog; fresh Python analysis','fresh native analog, cold PnR and Python analysis')
    intro=nbf.v4.new_markdown_cell('''# Standalone fresh laboratory — source IP → new measurements → cold top GDS

This copy includes RTL, circuit source IP, macro layouts, both PDK installations,
ngspice shared runtime and the OpenLane tool source/image. It needs no development
checkout. Run from this folder with env_mamba and Restart Kernel & Run All.

Every run creates an empty directory under `runs/`. Stored ADC codes, voltage
measurements, waveforms and an old routed top are not supplied as runtime inputs.
The baseline/factorial, 41 coupled conversions, analysis and physical top are
generated again. Cold OpenLane starts from RTL and bundled hard-macro IP views.
Historical exploratory recipes remain visible as context; the active final path
performs fresh measurements and tool execution. External design paths are blocked.

The physical profile targets a functional prototype: filler insertion and long
automatic signoff campaigns are separate from cold placement/routing; bounded
DRC, extraction, connectivity and timing produce their actual reports.
''',id='standalone-introduction')
    book.cells.insert(0,intro)
    book.metadata['automx_review'].update(edition='standalone_fresh_cold_pnr',external_checkout_required=False,
        old_measurements_used=False,old_routed_checkpoint_used=False)
    from scripts.enrich_cim_notebook import enrich
    checkpoint_source=ROOT/'data/checkpoints'
    if checkpoint_source.is_dir() and checkpoint_source.resolve()!=(dest/'data/checkpoints').resolve():
        shutil.copytree(checkpoint_source,dest/'data/checkpoints',dirs_exist_ok=True)
    book=enrich(book)
    nbf.validate(book);target=dest/'AutoMX_CIM_Code_a_Chip.ipynb';nbf.write(book,target)
    for name in ('standalone_runtime.py','adapt_flow2_standalone_notebook.py','standalone_execute.py','standalone_readme.md',
                 'enrich_cim_notebook.py','validate_cim_notebook_lessons.py',
                 'cim_function_reference.py','cim_paper_lesson.py','cim_measurement_extension.py','render_flow2_wrapper_gds.py','cim_output_presentation.py'):
        if (ROOT/'scripts'/name).resolve()!=(dest/'scripts'/name).resolve():
            shutil.copyfile(ROOT/'scripts'/name,dest/'scripts'/name)
    # Guard child Python tools as well, while leaving OS/tool installations available.
    guard=dest/'tools/python_guard';guard.mkdir(parents=True,exist_ok=True)
    guardcode='import sys,os,json\nfrom pathlib import Path\n'
    guardcode+='prefixes='+repr(json.loads((dest/'standalone.json').read_text())['forbidden_roots'])+'\n'
    guardcode+='def audit(event,args):\n if event=="open" and args and isinstance(args[0],(str,bytes,os.PathLike)):\n  p=os.fsdecode(args[0])\n  if any(p==r or p.startswith(r+"/") for r in prefixes):raise PermissionError("External design input blocked: "+p)\nsys.addaudithook(audit)\n'
    (guard/'sitecustomize.py').write_text(guardcode)
    launcher='''#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
mkdir -p tmp
export AUTOMX_BUNDLE_DIR="$PWD"
export PYTHONPATH="$PWD/tools/python_guard:$PWD"
export TMPDIR="$PWD/tmp"
automx_python="${AUTOMX_PYTHON:-/home/nam/anaconda3/envs/env_mamba/bin/python}"
if [[ ! -x "$automx_python" ]]; then automx_python="$(command -v python)"; fi
export PATH="$(dirname -- "$automx_python"):$PATH"
'''
    for name,invoke in [('run_notebook.sh','-m jupyter lab AutoMX_CIM_Code_a_Chip.ipynb'),
                        ('run_all.sh','-u execute_standalone.py')]:
        (dest/name).write_text(launcher+'exec "$automx_python" '+invoke+'\n')
        (dest/name).chmod(0o755)
    shutil.copyfile(ROOT/'scripts/standalone_execute.py',dest/'execute_standalone.py')
    print('ADAPTED_STANDALONE_NOTEBOOK',target,'cells',len(book.cells),'code',sum(c.cell_type=='code' for c in book.cells),flush=True)
    return target

if __name__=='__main__':adapt(ROOT if (ROOT/'standalone.json').is_file() else DEST)
