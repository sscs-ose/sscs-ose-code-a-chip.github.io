"""Build one complete notebook with restored history and editable inline EDA code.

Source files are read ONLY by this authoring script. The generated notebook
contains those implementations and executes its own inline module sources.
"""
from pathlib import Path
import ast
import copy
import hashlib
import json
import re
import shutil
import sys
import textwrap
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
BOOK=ROOT/'AutoMX_CIM_Sky130_MHA.ipynb'
COMPACT=ROOT/'docs/AutoMX_CIM_runall_compact_20261023.ipynb'
LEGACY=ROOT/'docs/AutoMX_CIM_legacy_server_20261023.ipynb'
PKG='automx_nb_inline_v1'


def read(path):return (ROOT/path).read_text()
def sha(text):return hashlib.sha256(text.encode()).hexdigest()
def nodes(path,*names):
    source=read(path);tree=ast.parse(source);rows=[]
    for name in names:
        node=next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==name)
        start=min([node.lineno,*[d.lineno for d in getattr(node,'decorator_list',[])]])
        rows.append('\n'.join(source.splitlines()[start-1:node.end_lineno]))
    return '\n\n\n'.join(rows)+'\n'

def method(path,cls,name):
    source=read(path);node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name==cls)
    node=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name)
    return textwrap.dedent('\n'.join(source.splitlines()[node.lineno-1:node.end_lineno]))+'\n'


def clean(source):
    source=re.sub(r'^from __future__ import .*\n','',source,flags=re.M)
    source=re.sub(r'^ROOT\s*=\s*Path\(__file__\).*$', 'ROOT = Path(PROJECT_ROOT)',source,flags=re.M)
    return source


HISTORY_PATHS={
 'original-002':['docs/CODEX_PROGRESS_20261022.md','docs/CODEX_PROGRESS_20261022_0700.md'],
 '024cb1b0':['configs/sky130_mha_tiny.json'],
 'original-010':['results/receipts/environment.json'],
 'original-012':['results/receipts/stage1_mha_tiny.json'],
 'original-014':['results/receipts/mha_tiny_schedule_manifest.json','results/receipts/mha_tiny_schedule.json'],
 'original-016':['vectors/baseline_k32_m8/weights/manifest.json','vectors/baseline_k32_m8/vector/vector_manifest.json'],
 '40d8f72c':['physical/sky130/macro/macro_contract.json'],
 '437e4fa6':['results/receipts/spice/ternary_cell.json','results/receipts/spice/column_4x1.json','results/receipts/spice/column_8x1.json','results/receipts/spice/automx_ternary_cim_4x4_core.json'],
 'c4dd9fe2':['results/receipts/physical/stage5_summary.json'],
 '91f2d41f':['results/sky130/automx_ternary_cim_4x4_core_characterization.json','results/sky130/stage6_mha_comparison.json'],
 'core-pex-coverage-run':['results/receipts/physical/core_pex_coverage.json'],
 'b10e6122':['results/sky130/core_transfer_diagnostics/measured.json'],
 '83b715de':['results/sky130/core_transfer_design_space/measured.json'],
 'dff1da18':['results/sky130/core_candidate_pex/measured.json'],
 'core-candidate-full-tt-run':['results/sky130/core_candidate_full_tt/measured.json'],
 'post49-holdout-run':['results/sky130/post49_holdout_tt/measured.json'],
 'post49-work-packages-check':['docs/CODEX_PROGRESS_20261022.md'],
 'post49-decoder-diagnostic-run':['results/sky130/post49_decoder_diagnostic.json'],
 'post49-calibration-tt-run':['results/sky130/post49_calibration_tt/measured.json'],
 'post49-calibration-holdout-run':['results/sky130/post49_calibration_holdout/prepared.json'],
 'post49-offline-architecture-run':['results/sky130/post49_decoder_architecture/offline.json'],
 'post49-row-partition-run':['results/sky130/post49_row_partition/adjacent/measured.json'],
 'post49-partition-full-cal-run':['results/sky130/post49_partition_full_tt/calibration/measured.json'],
 'post49-partition-full-holdout-run':['results/sky130/post49_partition_full_tt/holdout/measured.json'],
 'post49-pvt-smoke-run':['results/sky130/post49_pvt_smoke/prepared.json'],
 'story-60-0-run':['results/sky130/wrapper_load_full_tt/c820ff/measured.json','results/sky130/wrapper_idle_augmented_tt/c820ff/measured.json'],
 'story-60-1-run':['results/sky130/wrapper_sample_hold_tt/measured.json','results/sky130/wrapper_sample_hold_tt/decomposition.json','results/sky130/wrapper_sample_hold_edge_tt/measured.json','results/sky130/flow2_sample_hold_sweep/pex_3d4425cdc7db/measured.json','results/sky130/flow2_sample_hold_settled_tt/pex_3d4425cdc7db/measured.json','results/sky130/flow2_sample_hold_aperture_tt/pex_3d4425cdc7db/measured.json','results/sky130/flow2_sample_hold_refined_aperture_tt/pex_3d4425cdc7db/measured.json'],
 'fb549349':['results/receipts/stage7_regression.json'],
 'stage7-stress-run':['results/receipts/stage7_stress.json'],
 'stage7-two-read-regression':['results/receipts/stage7_2p2_regression.json'],
 'story-70-0-run':['results/receipts/stage8_core_bound_clean.json','results/receipts/stage8_core_bound_demo.json'],
 'story-70-1-run':['results/receipts/stage8_core_bound_clean.json','results/receipts/stage8_core_bound_demo.json'],
 '0ee3887e':['results/receipts/stage8_core_bound_clean.json','results/receipts/stage8_core_bound_demo.json'],
 'story-70-2-run':['results/receipts/stage8_core_bound_clean.json','results/receipts/stage8_core_bound_demo.json'],
 'original-071':['results/receipts/stage8_preflight.json','results/receipts/wrapper_signoff.json'],
 '04465d43':['results/receipts/physical/stage5_summary.json','results/receipts/chip_prototype_signoff.json'],
}

BOOTSTRAP=r'''from pathlib import Path
import os,sys,json,hashlib,types
from IPython.core.magic import register_cell_magic
ROOT=Path(os.environ.get("AUTOMX_CIM_ROOT",Path.cwd())).resolve()
if not (ROOT/"configs/sky130_mha_tiny.json").is_file():raise FileNotFoundError("Start Jupyter in the AutoMX-CIM root")
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
CACHE=Path(os.environ.get("AUTOMX_RUNALL_CACHE","/media/nam/EDABK/AutoMX_CIM_runall_20261023")).resolve()
TAG=os.environ.get("AUTOMX_RUNALL_TAG","combined_inline_srv_20261023_01")
if not __import__('re').fullmatch('[A-Za-z][A-Za-z0-9_]{0,63}',TAG):raise ValueError("Invalid work tag")
INLINE_ROOT=CACHE/TAG/"notebook_sources"/"automx_nb_inline_v1"
INLINE_ROOT.mkdir(parents=True,exist_ok=True)
(INLINE_ROOT/"__init__.py").write_text("")
if str(INLINE_ROOT.parent) not in sys.path:sys.path.insert(0,str(INLINE_ROOT.parent))
import automx_nb_inline_v1
INLINE_SOURCES={}
RUN_LEGACY_CAMPAIGNS=False  # replay saved measurements by default; do not restart hundreds of old SPICE jobs
LEGACY_NS={"ROOT":ROOT,"__name__":"notebook_legacy"}

@register_cell_magic
def inline_module(line,cell):
    """Execute definitions visibly written in this cell in an isolated namespace.

    The generated .py is an executed-source snapshot / native-worker input,
    not a helper implementation read from the checkout. Edit the cell to edit
    the algorithm. Separating globals prevents old/new function names colliding.
    """
    name=line.strip()
    if not __import__('re').fullmatch('[a-z][a-z0-9_]*',name):raise ValueError("Invalid inline module name")
    definitions,_,invoke=cell.partition("# NOTEBOOK_RUN\n")
    path=INLINE_ROOT/(name+".py")
    header=("from __future__ import annotations\nfrom pathlib import Path\nimport sys\n"
        +"PROJECT_ROOT=Path("+repr(str(ROOT))+")\nINLINE_ROOT=Path("+repr(str(INLINE_ROOT))+")\n"
        +"sys.path.insert(0,str(PROJECT_ROOT))\nsys.path.insert(0,str(INLINE_ROOT.parent))\n")
    text=header+definitions
    if not path.is_file() or path.read_text()!=text:path.write_text(text)
    module=types.ModuleType("automx_nb_inline_v1."+name);module.__file__=str(path)
    sys.modules[module.__name__]=module
    setattr(automx_nb_inline_v1,name,module)
    exec(compile(text,str(path),"exec"),module.__dict__)
    get_ipython().user_ns[name]=module
    INLINE_SOURCES[name]={"path":str(path),"sha256":hashlib.sha256(text.encode()).hexdigest()}
    if invoke.strip():exec(compile(invoke,"<notebook-call:"+name+">","exec"),get_ipython().user_ns)

@register_cell_magic
def eda_source(line,cell):
    """Materialize the native tool script whose complete text is in this cell."""
    name=line.strip()
    if Path(name).name!=name:raise ValueError("Use a simple tool source filename")
    definitions,_,invoke=cell.partition("# NOTEBOOK_RUN\n")
    path=INLINE_ROOT/name
    if not path.is_file() or path.read_text()!=definitions:path.write_text(definitions)
    INLINE_SOURCES[name]={"path":str(path),"sha256":hashlib.sha256(definitions.encode()).hexdigest()}
    if invoke.strip():exec(compile(invoke,"<notebook-native:"+name+">","exec"),get_ipython().user_ns)
print("Python:",sys.executable,"\nProject:",ROOT,"\nTag:",TAG,"\nInline native inputs:",INLINE_ROOT)
'''


def build():
    from scripts.flow2_notebook_results_prose import legacy_prose,MODERN
    if not COMPACT.exists():shutil.copy2(BOOK,COMPACT)
    compact=nbf.read(COMPACT,4);old=nbf.read(LEGACY,4);cells=[];mapping=[]
    def md(text,id=None,**meta):
        c=nbf.v4.new_markdown_cell(text,**({'id':id} if id else {}));c.metadata.update(meta);cells.append(c);return c
    def code(id,text,**meta):
        c=nbf.v4.new_code_cell(text,id=id);c.metadata.update(meta);cells.append(c);return c
    def inline(name,body,invoke='',id=None,origin=None):
        body=clean(body)
        text='%%inline_module '+name+'\n'+body.rstrip()+'\n'
        if invoke:text+='\n# NOTEBOOK_RUN\n'+invoke+'\n'
        return code(id or 'inline-'+name,text,inline_origin=origin or 'notebook implementation')
    def tool(name,body,id):return code(id,'%%eda_source '+name+'\n'+body,inline_origin='native source included in notebook')
    md('''# AutoMX-CIM — flow đầy đủ: các phép đo cũ → analog/SAR/MHA → top core mixed-signal

**Một notebook, Run All từ đầu đến cuối bằng kernel env_mamba.** Phần A giữ lại các bước/nội dung đo kiểm trước đây; phần B tiếp tục bằng partition analog + SAR RTL và xuất top. Phần C giữ phiên orchestration cũ để tra cứu. Các checkpoint Markdown, receipt, log, deck và kết quả âm đều giữ nguyên.

**Code xử lý nằm trong cell:** các cell `%%inline_module` chứa đầy đủ định nghĩa hàm/class và phần gọi ở cuối cell. Magic chỉ cô lập namespace; không đọc implementation từ file helper. Các cell `%%eda_source` chứa toàn bộ script cần đưa cho process KLayout/OpenROAD. File trong `notebook_sources/` là snapshot sinh từ nội dung cell để native worker chạy, không phải implementation giấu bên ngoài notebook.

**Run All:** đọc lại receipt/log của các chiến dịch cũ, kiểm hash và hiện số liệu đo; phần B chạy tool hoặc reuse artifact theo hash. Chuỗi phát triển hiển thị lỗi transfer, **52/128 decode errors**, đọc 2+2 với **0/256 decode errors**, và independent OpenROAD DRC **50 → 16 → 16 → 0**. Các tập đo và tool được ghi riêng trong từng bảng.

[Notebook 127 cell nguyên bản](docs/AutoMX_CIM_legacy_server_20261023.ipynb) · [Bản Run All trước khi thêm chuỗi đo](docs/AutoMX_CIM_runall_compact_20261023.ipynb).''',id='combined-intro')
    code('runall-config',BOOTSTRAP)
    inline('history',read('scripts/flow2_notebook_history.py'))
    story_source=read('scripts/flow2_experiment_story.py')
    inline('story',story_source.split('def transfer_error')[0])
    def story_cell(name,title,intro,invoke=None):
        md('### '+title+'\n\n'+intro,id='story-'+name+'-guide')
        header='from pathlib import Path\nfrom collections import Counter\nimport json,re\nfrom IPython.display import Markdown,display\n'+f'from {PKG}.story import EVIDENCE,BASE,PHYSICAL,fingerprint,read_report,table,linked\n'
        inline('story_'+name,header+nodes('scripts/flow2_experiment_story.py',name),invoke or ('story_'+name+'.'+name+'(ROOT)'),id='story-'+name)

    # Full historical narrative and executable recipes, preserving source identity.
    md('## Phần A — numerical contract, Stage 4/5, PEX/TT, holdout, 2+2 và RTL cũ\n\nMỗi cell code dưới đây hiện lại phép đo đã lưu. Recipe gốc và implementation runner được đặt cùng cell; nhánh chạy lại chỉ bật khi chủ động chọn RUN_LEGACY_CAMPAIGNS.',id='combined-history')
    known_modules={}
    def library_body(path):
        body=read(path);package=path.replace('/','.').removesuffix('.py').rsplit('.',1)[0]
        from importlib.util import resolve_name
        for node in ast.walk(ast.parse(body)):
            if isinstance(node,ast.ImportFrom) and node.level:
                before='from '+'.'*node.level+(node.module or '')+' import'
                after='from '+resolve_name('.'*node.level+(node.module or ''),package)+' import'
                body=body.replace(before,after)
        return body
    extra_libraries={
        'original-012': [('legacy_attention','automx_cim/attention.py')],
        'original-014': [('legacy_schedule','automx_cim/scheduler.py')],
        '437e4fa6': [('legacy_stage4_generator','automx_cim/circuit/sky130.py'),('legacy_stage4_runner','automx_cim/spice/runner.py')],
        'c4dd9fe2': [('legacy_stage5','automx_cim/physical/stage5.py')],
        '91f2d41f': [('legacy_stage6','automx_cim/characterization.py')],
    }
    for old_index,c in enumerate(old.cells[21:],21):
        original=c.source
        m=re.fullmatch(r'Historical code `([^`]+)` \(disabled\):\s*````python\n(.*)\n````\s*',original,re.S)
        cid='restored-'+c.id
        if not m:
            new=md(legacy_prose(c.id,original),id=cid)
        else:
            key,recipe=m[1],m[2]
            for libname,libpath in extra_libraries.get(key,[]):
                inline(libname,library_body(libpath),origin=libpath)
            if key=='original-012':recipe=recipe.replace('from automx_cim import run_stage1, write_stage1_receipt',f'from {PKG}.legacy_attention import run_stage1, write_stage1_receipt')
            if key=='original-014':recipe=recipe.replace('from automx_cim import build_tiny_mha_schedule, write_stage2_schedule',f'from {PKG}.legacy_schedule import build_tiny_mha_schedule, write_stage2_schedule')
            if key=='91f2d41f':recipe=recipe.replace('from automx_cim.characterization import write_stage6',f'from {PKG}.legacy_stage6 import write_stage6')
            if key=='437e4fa6':
                a=recipe.index('from automx_cim import (');b=recipe.index(')',a)+1
                recipe=recipe[:a]+f'from {PKG}.legacy_stage4_generator import discover_sky130_model_library, generate_stage4_spice\nfrom {PKG}.legacy_stage4_runner import run_stage4_manifest'+recipe[b:]
            tree=ast.parse(recipe);primary=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import):primary.extend(a.name for a in node.names if a.name.startswith('scripts.') and (ROOT/(a.name.replace('.','/')+'.py')).is_file())
                elif isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('scripts.') and (ROOT/(node.module.replace('.','/')+'.py')).is_file():primary.append(node.module)
            native_entries={'c4dd9fe2':'scripts.run_stage5_physical','fb549349':'scripts.run_stage7_regression','stage7-stress-run':'scripts.run_stage7_stress'}
            if key in native_entries:primary.insert(0,native_entries[key])
            primary=[v for v in dict.fromkeys(primary) if not v.startswith(PKG+'.')];body='';module_name='legacy_'+c.id.replace('-','_')
            if primary:
                selected=primary[0];path=selected.replace('.','/')+'.py';body=clean(read(path))
                # Restore the original call against this cell's implementation.
                recipe=recipe.replace('import '+selected+' as ',f'import {PKG}.{module_name} as ')
                recipe=recipe.replace('from '+selected+' import ',f'from {PKG}.{module_name} import ')
                known_modules[selected]=module_name
                # Native subprocesses now execute the source materialized from this cell.
                for quote in ("'",'"'):
                    original_path=selected.replace('.','/')+'.py'
                    recipe=recipe.replace('ROOT / '+quote+original_path+quote,'INLINE_ROOT / '+quote+module_name+'.py'+quote)
                    recipe=recipe.replace('ROOT / '+quote+'scripts'+quote+' / '+quote+Path(original_path).name+quote,'INLINE_ROOT / '+quote+module_name+'.py'+quote)
                if key=='c4dd9fe2':body=body.replace('from automx_cim.physical.stage5 import',f'from {PKG}.legacy_stage5 import').replace('from automx_cim.physical import run_stage5, write_preflight_receipt',f'from {PKG}.legacy_stage5 import run_stage5\nfrom automx_cim.physical import write_preflight_receipt')
            else:
                # Visible old notebook recipe plus active receipt reader.
                body='"""Original notebook recipe retained below with replay as the default."""\n'
            # Do not reload generated modules through importlib: source is the cell itself.
            recipe=re.sub(r'^(\w+) = importlib.reload\(\1\)\s*$',r'# inline module already loaded from this cell: \1',recipe,flags=re.M)
            recipe=re.sub(r'^from __future__ import .*$', '# future annotations are enabled by the inline compiler',recipe,flags=re.M)
            paths=HISTORY_PATHS.get(key,[])
            invoke='historical_rows = history.review_reports(ROOT, '+repr(paths)+', label='+repr(key)+')\n'
            if key in ('core-candidate-full-tt-run','post49-partition-full-cal-run'):
                invoke+='history.plot_saved_transfer(ROOT, '+repr(paths[0])+', '+repr(key)+')\n'
            invoke+='\n# Original notebook invocation, preserved for deliberate native regeneration.\nif RUN_LEGACY_CAMPAIGNS:\n'+textwrap.indent(recipe,'    ')+'\n'
            new=inline(module_name,body,invoke,id=cid,origin=primary[0] if primary else 'historical notebook cell '+key)
            new.metadata['original_code_sha256']=sha(m[2]);new.metadata['historical_recipe']=key
        new.metadata['original_cell_id']=c.id;new.metadata['original_source_sha256']=sha(original)
        mapping.append(dict(original_index=old_index,original_id=c.id,original_sha256=sha(original),combined_id=new.id))
        if m:
            stories={
              'b10e6122':('transfer_error','Đo lỗi transfer ban đầu','Đọc các cặp đảo mức từ report ngspice PEX đã chạy; in trực tiếp case và điện áp đo.'),
              'core-candidate-full-tt-run':('candidate_result','Sau sửa tải/PWM: kiểm lại 101 case','Kết quả chọn tải/PWM được đối chiếu trên toàn bộ tập PEX ban đầu.'),
              'post49-calibration-tt-run':('decoder_errors','Đo error của decoder và tìm nguyên nhân','Đọc những dòng giải mã sai của holdout cũ và minimum gap của calibration mở rộng.'),
              'post49-partition-full-holdout-run':('partition_result','Sau thay đổi cách đọc: kết quả 2+2','So sánh các mốc đo với tập dữ liệu riêng của từng chiến dịch; ngưỡng được khóa trước fresh holdout.')}
            if key in stories:story_cell(*stories[key])

    # Primary modern implementation dependencies, all embedded visibly.
    md('## Phần B — tiếp tục bằng code inline đến top core mixed-signal\n\nMã dưới đây trực tiếp điều khiển các tool native. Không import các helper flow2_runall_*.py để thực hiện pipeline. Kết quả gồm waveform ADC, output MHA, mapped netlist, GDS/DEF/LEF, LVS, RC và timing.',id='combined-modern')
    from scripts import run_flow2_core_acquisition as core
    from scripts import run_flow2_acquisition_layout as acq
    from scripts import flow2_wrapper_design as design
    from scripts import run_flow2_wrapper_transistor_lvs as lvs_module
    common='''from pathlib import Path
from collections import Counter
import json,re,math,os,hashlib
BASE=Path("results/sky130/flow2_wrapper_integration")
BUILD=Path("build/flow2_wrapper_integration")
OPENLANE_SOURCE=Path("/home/nam/dependencies/openlane_src")
OPENLANE_PDK=Path("/home/nam/.volare_openlane_30ee138_nam")
IMAGE="efabless/openlane:30ee1388932eb55a89ad84ee43997bfe3a386421-amd64"
TOP="automx_cim_mixed_signal_proto"
NATIVE="mixed_wrapper_srv_20261022_04_impl_gds"
def _sha(path):
 with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
'''
    common+='CELL='+repr(core.CELL)+'\nPINS='+repr(core.PINS)+'\nACQ_PINS='+repr(acq.PINS)+'\nCOND='+repr(design.COND)+'\nCOND_PINS='+repr(design.COND_PINS)+'\nPRIMITIVES='+repr(lvs_module.PRIMITIVES)+'\n'
    common+=nodes('scripts/flow2_integration_common.py','tag_ok')+nodes('scripts/run_flow2_acquisition_layout.py','_verified')
    common+=nodes('scripts/run_flow2_acquisition_layout.py','_rc_audit').replace('set(PINS)','set(ACQ_PINS)')
    common+=nodes('scripts/run_flow2_core_tap_transient.py','source').replace('common.','').replace('core.acq._rc_audit','_rc_audit')
    common+=nodes('scripts/run_flow2_antenna_streamout.py','component_masters','validate_streamout_log')
    common+=nodes('scripts/run_flow2_wrapper_transistor_lvs.py','validate_netgen')
    common+=nodes('scripts/run_flow2_chip_sta.py','prototype_sdc','timing_metrics')
    common+=nodes('scripts/run_flow2_wrapper_postroute.py','clock_model')
    common+='''
def container_command(root,program,args,name):
 home=Path.home().resolve();root=Path(root).resolve()
 if not root.is_relative_to(home):raise ValueError('project must be under mounted home')
 return ['docker','run','--name',name,'--rm','--user',str(os.getuid())+':'+str(os.getgid()),
  '--network','host','--security-opt','seccomp=unconfined','-v',str(OPENLANE_SOURCE)+':/openlane',
  '-v',str(OPENLANE_SOURCE/'designs')+':/openlane/install','-v',str(home)+':'+str(home),
  '-v',str(OPENLANE_PDK)+':'+str(OPENLANE_PDK),'-e','PDK_ROOT='+str(OPENLANE_PDK),'-e','PDK=sky130A',
  '-w','/openlane','--entrypoint',program,IMAGE,*map(str,args)]
'''
    inline('geometry_common',common,origin='inlined geometry/PDK/DEF/LVS/STA helpers and explicit constants')
    support=read('scripts/flow2_runall_support.py').replace('from scripts.flow2_integration_common import tag_ok',f'from {PKG}.geometry_common import tag_ok').replace('from scripts.run_flow2_wrapper_postroute import container_command',f'from {PKG}.geometry_common import container_command')
    support=support.replace("script=self.root/'scripts/render_flow2_wrapper_gds.py'","script=Path(INLINE_ROOT)/'render_flow2_wrapper_gds.py'")
    inline('support',support,'''settings=support.Settings(root=ROOT,cache=CACHE,tag=TAG,reuse=True,timeout_s=180,jobs=3)
flow=support.Flow(settings)''',id='inline-support')
    tool('render_flow2_wrapper_gds.py',read('scripts/render_flow2_wrapper_gds.py'),'inline-klayout-render-source')
    tool('flow2_chip_pg_check.py',read('scripts/flow2_chip_pg_check.py'),'inline-pg-worker-source')
    inline('waveforms',read('scripts/flow2_waveforms.py'))
    inline('klayout_checks',read('scripts/flow2_klayout_checks.py'))
    attention='from dataclasses import dataclass\nimport numpy as np\n'+nodes('automx_cim/attention.py','MHAResult','softmax','mha_from_projections','error_metrics')
    inline('attention',attention)
    inline('adc_partition',read('scripts/flow2_adc_partition.py'))
    worker=clean(read('scripts/flow2_rtl_spice_cosim.py'))
    worker=worker.replace('from scripts import flow2_adc_partition as adc',f'from {PKG} import adc_partition as adc')
    worker=worker.replace('from scripts.run_flow2_core_tap_transient import source',f'from {PKG}.geometry_common import source')
    worker=worker.replace('from scripts import run_flow2_core_acquisition as core',f'from {PKG} import geometry_common as core')
    worker=worker.replace('from scripts import flow2_wrapper_design as design',f'from {PKG} import geometry_common as design')
    worker=worker.replace('from scripts import flow2_integration_common as common',f'from {PKG} import geometry_common as common')
    inline('cosim',worker,origin='full shared-ngspice / original SAR RTL feedback implementation')
    nb_imports=f'from {PKG}.support import digest,item,save,verified\n'
    modern=clean(read('scripts/flow2_runall_notebook.py')).replace('from scripts.flow2_runall_support import digest,item,save,verified',nb_imports.strip()).replace('from scripts.flow2_waveforms import read_raw',f'from {PKG}.waveforms import read_raw')
    setup='import json,sys,shutil,tarfile\nfrom pathlib import Path\n'+nb_imports+"ARCHIVE_SHA='e7dadfb7bd5474fd22409c1e5a67acdec19f77e597df68e17c5549bc1390d7fd'\n"
    inline('environment',setup+nodes('scripts/flow2_runall_notebook.py','environment'),'environment.environment(flow)',id='runall-environment')
    inline('ngspice_setup',setup+nodes('scripts/flow2_runall_notebook.py','prepare_shared'),'shared_library=ngspice_setup.prepare_shared(flow)',id='runall-ngspice')
    physical_source=clean(read('scripts/flow2_runall_physical.py'))
    replacements={
      'from scripts.flow2_runall_support import item,digest,save':f'from {PKG}.support import item,digest,save',
      'from scripts import flow2_integration_common as c':f'from {PKG} import geometry_common as c',
      'from scripts import run_flow2_wrapper_postroute as p':f'from {PKG} import geometry_common as p',
      "p.native.notebook.DEFAULT_PDK/'sky130A'":"p.OPENLANE_PDK/'sky130A'",
      'from scripts.run_flow2_antenna_streamout import validate_streamout_log,component_masters':f'from {PKG}.geometry_common import validate_streamout_log,component_masters',
      'from scripts.flow2_klayout_checks import summarize':f'from {PKG}.klayout_checks import summarize',
      'from scripts.flow2_runall_support import verified':f'from {PKG}.support import verified',
      'from scripts.run_flow2_wrapper_transistor_lvs import validate_netgen':f'from {PKG}.geometry_common import validate_netgen',
      'from scripts.run_flow2_chip_sta import prototype_sdc,timing_metrics':f'from {PKG}.geometry_common import prototype_sdc,timing_metrics',
      'from scripts.run_flow2_wrapper_postroute import clock_model':f'from {PKG}.geometry_common import clock_model',
      "script=flow.root/'scripts/flow2_chip_pg_check.py'":"script=Path(INLINE_ROOT)/'flow2_chip_pg_check.py'"}
    for a,b in replacements.items():physical_source=physical_source.replace(a,b)
    physical_header='import json,re,xml.etree.ElementTree as ET\nfrom pathlib import Path\n'+nb_imports+f'from {PKG}.geometry_common import TOP,NATIVE\n'
    physical_source=physical_source.replace('Netgen unique signal match; extraction reused through exact full-GDS geometry equivalence. PG/body/transistor scope remains separate.','Netgen unique signal match; exact full-GDS geometry equivalence verified.').replace('Fresh synthesis of the same upstream SAR RTL used by the transistor co-simulation; not a replacement routed ADC macro.','Yosys mapped the same upstream SAR RTL used by transistor co-simulation.')
    physical_source=physical_source.replace('REUSE bounded INCOMPLETE DRC attempt: waiver only, never DRC-clean. Use a new tag/reuse=False to retry.','KLayout: hash-verified receipt of the previous bounded check.').replace('json.dumps(drc,indent=2)',"json.dumps({k:v for k,v in drc.items() if k!='scope'},indent=2)")
    ptree=ast.parse(physical_source)
    def physical_functions(*names):
        return '\n\n'.join(ast.get_source_segment(physical_source,next(n for n in ptree.body if isinstance(n,ast.FunctionDef) and n.name==name)) for name in names)+'\n'
    inline('physical_common',physical_header+physical_functions('inputs'))
    mha_source=clean(read('scripts/flow2_partition_mha.py'))
    mha_source=mha_source.replace('from automx_cim.attention import mha_from_projections,error_metrics',f'from {PKG}.attention import mha_from_projections,error_metrics')
    mha_source=mha_source.replace('from scripts.flow2_runall_support import digest,item,save,verified',nb_imports.strip())
    mha_source=mha_source.replace("self.root/'scripts'/f for f in ('flow2_rtl_spice_cosim.py','flow2_adc_partition.py')", "Path(INLINE_ROOT)/(f+'.py') for f in ('cosim','adc_partition','geometry_common','support')")
    mha_source=mha_source.replace('from scripts.run_flow2_core_tap_transient import source',f'from {PKG}.geometry_common import source').replace('from scripts import flow2_integration_common as common',f'from {PKG} import geometry_common as common')
    mha_source=mha_source.replace("self.root/'scripts/flow2_rtl_spice_cosim.py'","Path(INLINE_ROOT)/'cosim.py'")
    inline('mha_engine',mha_source,'''experiment=mha_engine.Experiment(flow)
source,source_views,design,routed_run,config,pdk=physical_common.inputs(flow)
print("Pinned analog/native inputs:",len(experiment.sources))
print("Verified routed source:",support.item(source_views["odb"]))''',id='runall-partition-sources')
    # Reuse all modern explanatory cells, replacing each short external call with its full implementation.
    skip={'runall-config','runall-environment','runall-ngspice','runall-partition-sources'}
    for c in compact.cells[7:]:
        if c.cell_type=='markdown':md(MODERN.get(c.id,c.source),id='new-'+c.id);continue
        name=c.id
        if name in skip:continue
        if name=='runall-render-macros':
            body='import json\nfrom pathlib import Path\n'+nodes('scripts/render_flow2_components.py','catalog')
            invoke='macro_views=catalog.catalog(ROOT,design/"config.json")[:3]\nfor macro in macro_views:\n print(macro["title"])\n flow.render(macro["source"],macro["cell"],macro["name"])'
            inline('catalog',body,invoke,id=name)
        elif name=='runall-calibration':inline('calibration','import json,numpy as np\n'+nb_imports+method('scripts/flow2_partition_mha.py','Experiment','calibrate'),'calibration=calibration.calibrate(experiment)',id=name)
        elif name=='runall-measured-mha':inline('measured_mha','import json,numpy as np\n'+nb_imports+f'from {PKG}.attention import mha_from_projections,error_metrics\nfrom {PKG}.mha_engine import quantize_context\n'+method('scripts/flow2_partition_mha.py','Experiment','mha').replace("if k not in ('jobs','evidence')","if k in ('shape','output','reference_quantized_output','metrics','relative_l2','floating_reference_relative_l2','projection_transactions','unique_holdout_patterns')"),'mha=measured_mha.mha(experiment)',id=name)
        elif name=='runall-adc-waveform':
            body=setup+nodes('scripts/flow2_runall_notebook.py','plot_conversion').replace('from scripts.flow2_waveforms import read_raw',f'from {PKG}.waveforms import read_raw')
            inline('adc_plot',body,'conversion=adc_plot.plot_conversion(flow,mha["jobs"][0]["case"])',id=name)
        elif name=='runall-mha-plots':inline('mha_plot',setup+nodes('scripts/flow2_runall_notebook.py','plot_mha'),'mha_plot.plot_mha(flow,mha)\nprint("Quantized/floating relative L2:",mha["relative_l2"],mha["floating_reference_relative_l2"])',id=name)
        elif name=='runall-synthesis':inline('synthesis',physical_header+f'from {PKG}.physical_common import inputs\n'+physical_functions('synthesize_sar','synthesize'),'synthesis.synthesize_sar(flow)\nsynthesis.synthesize(flow)',id=name)
        elif name=='runall-streamout':
            story_cell('routing_progress','Vi phạm routing và các lần ECO','Trích report OpenROAD thực: net, bounding box, lớp kim loại và số marker sau từng lần khôi phục route.')
            inline('streamout',physical_header+f'from {PKG}.physical_common import inputs\n'+physical_functions('streamout'),'top_gds=streamout.streamout(flow)',id=name)
        elif name=='runall-gds-audit':inline('gds_audit',physical_header+f'from {PKG}.physical_common import inputs\n'+physical_functions('audit_gds').replace('outputs=[xml],cwd=work,timeout_s=180','outputs=[xml],cwd=work,timeout_s=45'),'audit=gds_audit.audit_gds(flow)',id=name)
        elif name=='runall-render-top':
            body=setup+method('scripts/flow2_runall_support.py','Flow','render').replace("script=self.root/'scripts/render_flow2_wrapper_gds.py'", "script=Path(INLINE_ROOT)/'render_flow2_wrapper_gds.py'")
            inline('top_render',body,'top_render.render(flow,top_gds,geometry_common.TOP,"top")',id=name)
        elif name=='runall-signal-lvs':inline('signal_lvs',physical_header+f'from {PKG}.physical_common import inputs\n'+physical_functions('lvs'),'signal_lvs.lvs(flow)',id=name)
        elif name=='runall-power':inline('power',physical_header+f'from {PKG}.physical_common import inputs\n'+physical_functions('power'),'power_report=power.power(flow)',id=name)
        elif name=='runall-timing':inline('timing',physical_header+f'from {PKG}.physical_common import inputs\n'+physical_functions('timing','parse_library'),'timing_report=timing.timing(flow)\ntiming.parse_library(flow)',id=name)
        elif name=='runall-manifest':
            body=setup+nodes('scripts/flow2_runall_notebook.py','publish')
            body=body.replace("print(json.dumps({k:v for k,v in report.items() if k not in ('views','native_steps')},indent=2,ensure_ascii=False))", "print(json.dumps({k:report[k] for k in ('tag','projection_transactions','unique_holdout_patterns','relative_l2_quantized_reference','published_folder')},indent=2,ensure_ascii=False))")
            body=body.replace('def publish(flow):','def publish(flow,inline_sources,historical_evidence):')
            body=body.replace('    required=', '    inline_path=flow.work/"inline_sources_manifest.json";save(inline_path,inline_sources)\n    history_path=flow.work/"historical_evidence_manifest.json";save(history_path,historical_evidence)\n    required=')
            body=body.replace('    folder=flow.root/', '    report["inline_sources"]=item(inline_path)\n    report["historical_evidence"]=item(history_path)\n    folder=flow.root/')
            story_cell('dependencies','Kết quả cũ nào làm tiền đề cho bước sau?','Đối chiếu hash report đầu vào, xác nhận ODB ECO cuối chính là nguồn của GDS hiện tại và nêu vai trò của các kết quả 127 cell cũ.',invoke='story_dependencies.dependencies(ROOT,flow)')
            story_cell('final_results','Tổng hợp kết quả đo và artifact cuối','Đọc số liệu trực tiếp từ output của Run All hiện tại.',invoke='story_final_results.final_results(flow)')
            inline('publish',body,'manifest=publish.publish(flow,INLINE_SOURCES,history.REPLAY_RECORDS)',id=name)
        else:raise ValueError('Unmapped modern cell '+name)
    # Keep every cell of the previous server orchestration as an explicit appendix.
    md('## Phần C — phiên server orchestration trước đây (giữ đủ cell gốc)\n\nCác recipe này giữ để tra cứu/reproduce một phiên cũ, không thay đổi mode của flow hiện tại. Run All đọc receipt của phiên; RUN_LEGACY_CAMPAIGNS=True mới gọi recipe cũ. Số liệu phát triển và artifact được tổng hợp tại các bảng đo của flow hiện tại.',id='combined-orchestration-appendix')
    for old_index,c in enumerate(old.cells[:21]):
        cid='restored-'+c.id
        if c.cell_type=='markdown':new=md(legacy_prose(c.id,c.source),id=cid)
        else:
            source=c.source
            # Store visible full old code; execution is explicit and isolated from modern globals.
            body='if RUN_LEGACY_CAMPAIGNS:\n'+textwrap.indent(re.sub(r'^from __future__ import .*$', '# future import omitted in guarded notebook recipe',source,flags=re.M),'    ')+ '\nelse:\n    historical_server_rows=history.review_reports(ROOT,["results/receipts/chip_prototype_signoff.json"],label='+repr(c.id)+',show_log=False)\n'
            new=code(cid,body,historical_recipe=c.id)
        new.metadata['original_cell_id']=c.id;new.metadata['original_source_sha256']=sha(c.source)
        mapping.append(dict(original_index=old_index,original_id=c.id,original_sha256=sha(c.source),combined_id=new.id))
    # Publish only after the historical appendix has also been reviewed.
    final_index=next(i for i,c in enumerate(cells) if c.id=='new-3bed6f56')
    appendix_index=next(i for i,c in enumerate(cells) if c.id=='combined-orchestration-appendix')
    final_cells=cells[final_index:appendix_index]
    del cells[final_index:appendix_index]
    cells.extend(final_cells)
    book=nbf.v4.new_notebook(cells=cells)
    book.metadata={'kernelspec':{'display_name':'Python (env_mamba)','language':'python','name':'python3'},'language_info':{'name':'python'},
        'automx':{'flow':'flow2_combined_inline_v2','historical_cell_mapping':sorted(mapping,key=lambda row:row['original_index']),
                 'historical_cells_preserved':len(mapping),'compact_backup':str(COMPACT.relative_to(ROOT))}}
    nbf.write(book,BOOK)
    (ROOT/'docs/flow2_combined_inline_cell_map_20261023.json').write_text(json.dumps(dict(historical_archive=str(LEGACY.relative_to(ROOT)),preserved_cells=len(mapping),mapping=sorted(mapping,key=lambda row:row['original_index'])),indent=2)+'\n')
    print(BOOK,'cells',len(cells),'code',sum(c.cell_type=='code' for c in cells),'preserved historical cells',len(mapping))

if __name__=='__main__':build()
