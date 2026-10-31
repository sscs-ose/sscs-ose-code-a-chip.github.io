"""Continue the current fresh session after a corrected physical-stage timeout.

Measurements already executed in this same session remain in their original
cells. A separate notebook records definition restoration and tail execution.
"""
from pathlib import Path
from datetime import datetime,timezone
import copy,json,os,time
import nbformat as nbf
from nbclient import NotebookClient
from scripts.flow2_runall_support import item,save
ROOT=Path(__file__).resolve().parents[1]


def resume():
    session=json.loads((ROOT/'docs/flow2_fresh_session_20261023.json').read_text());folder=Path(session['session']);work=Path(session['work']);path=Path(session['notebook'])
    book=nbf.read(path,4);first=next(i for i,c in enumerate(book.cells) if c.id=='runall-gds-audit');restore=[]
    config=next(c.source for c in book.cells if c.id=='runall-config')
    a=config.index('prior_results=');b=config.index('if not __import__',a)
    config=config[:a]+"if not (WORK/'fresh_start.json').is_file():raise FileNotFoundError('No fresh session to continue')\n"+config[b:]
    restore.append(nbf.v4.new_code_cell(config,id='restore-current-session'))
    for cell in book.cells[:first]:
        if cell.source.startswith(('%%inline_module ','%%eda_source ')):
            definitions=cell.source.partition('# NOTEBOOK_RUN\n')[0]
            restore.append(nbf.v4.new_code_cell(definitions,id='restore-'+cell.id))
    context='''history.REFERENCE_ONLY=True
settings=support.Settings(root=ROOT,cache=CACHE,tag=TAG,reuse=False,timeout_s=180,jobs=3)
flow=support.Flow(settings)
source,source_views,design,routed_run,config,pdk=physical_common.inputs(flow)
for reference in sorted(WORK.rglob('*.step.json'))+sorted(WORK.glob('*/step.json')):
    if any(p.startswith('prior_') for p in reference.parts):continue
    data=json.loads(reference.read_text())
    if 'identity' not in data:continue
    name=reference.name.removesuffix('.step.json') if reference.name!='step.json' else reference.parent.name
    flow.receipts[name]=support.item(reference)
outputs={
 'ngspice_runtime':'ngspice_runtime.json',
 'analog_adc_mha':'mha_end_to_end.json',
 'adc_waveform_png':'adc_native_waveform.png',
 'mha_png':'mha_measured.png',
 'mapped_sar':'sar_synthesis/adc_core_digital.mapped.v',
 'mapped_synthesis':'synthesis/automx_cim_mixed_signal_proto.mapped.v',
 'gds':'streamout/automx_cim_mixed_signal_proto.gds',
 'lef':'streamout/automx_cim_mixed_signal_proto.lef',
 'def':'streamout/automx_cim_mixed_signal_proto.def'}
for key,relative in outputs.items():flow.outputs[key]=support.item(WORK/relative)
for name in ('01_core_acquisition','02_conditioner_mux','03_adc_reference'):
    flow.outputs[name+'_png']=support.item(WORK/('render_'+name)/(name+'.png'))
flow.outputs['source_gds']=support.item(source_views['gds'])
flow.outputs['route_checkpoint']=support.item(source_views['odb'])
top_gds=Path(flow.outputs['gds']['path'])
mha=json.loads((WORK/'mha_end_to_end.json').read_text())
for load,pwm in ((200,100),(800,50)):
    fresh_pilot.RESULTS[str(load)]=json.loads((WORK/f'fresh_pex_c{load}_pwm{pwm}'/'measured.json').read_text())
'''
    restore.append(nbf.v4.new_code_cell(context,id='restore-current-native-artifacts'))
    tail=copy.deepcopy(book.cells[first:]);temporary=nbf.v4.new_notebook(cells=restore+tail,metadata=copy.deepcopy(book.metadata));offset=len(restore)
    os.environ.update(AUTOMX_RUNALL_CACHE=session['session'],AUTOMX_RUNALL_TAG=session['tag'])
    started=time.monotonic();status='FAILED';context_path=folder/'continuation_context.ipynb'
    def begin(cell,cell_index,**_):
        if cell.cell_type=='code':print('CONTINUE',cell_index,cell.id,flush=True)
    client=NotebookClient(temporary,timeout=900,kernel_name='python3',allow_errors=False,resources={'metadata':{'path':str(ROOT)}},on_cell_start=begin)
    try:
        client.execute();status='ALL_CODE_CELLS_EXECUTED'
    finally:
        nbf.write(temporary,context_path)
        book.cells[first:]=temporary.cells[offset:]
        book.metadata['automx']['continuation_context']=str(context_path)
        nbf.write(book,path)
        code=[c for c in book.cells if c.cell_type=='code']
        initial=json.loads((folder/'initial_failed_execution.json').read_text())
        report=dict(status=status,timestamp_utc=datetime.now(timezone.utc).isoformat(),elapsed_s=initial['elapsed_s']+time.monotonic()-started,
            notebook=item(path),kernel='python3 (env_mamba)',code_cells=len(code),executed_cells=sum(c.execution_count is not None for c in code),
            errors=[{'cell':c.id,'error':o.get('ename'),'value':o.get('evalue')} for c in code for o in c.outputs if o.output_type=='error'],
            flow=book.metadata['automx']['flow'],execution_mode='continued_current_fresh_session',continued_from_cell='runall-gds-audit',
            initial_attempt=item(folder/'initial_failed_execution.json'),continuation_context=item(context_path),
            scope='Current-session measurements and their original outputs preserved. Function definitions restored in a new env_mamba kernel; corrected geometry check and remaining cells actually executed. No prior-session measurements or logs replayed.')
        save(folder/'execution.json',report);save(ROOT/'docs/flow2_fresh_execution_20261023.json',report)
        print({k:v for k,v in report.items() if k not in ('notebook','initial_attempt','continuation_context')},flush=True)
    return report

if __name__=='__main__':resume()
