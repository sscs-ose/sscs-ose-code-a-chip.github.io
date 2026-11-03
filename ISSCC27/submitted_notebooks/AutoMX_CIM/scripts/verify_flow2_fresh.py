"""Check that Run All produced current-session native measurements and logs."""
from pathlib import Path
import json,re,shutil,copy
import nbformat
from scripts.flow2_runall_support import verified,save
from scripts.flow2_notebook_theory import apply_front_matter
ROOT=Path(__file__).resolve().parents[1]


def verify():
    session=json.loads((ROOT/'docs/flow2_fresh_session_20261023.json').read_text());folder=Path(session['session']);work=Path(session['work'])
    run=json.loads((folder/'execution.json').read_text());book_path=Path(session['notebook']);book=nbformat.read(book_path,4)
    assert run['status']=='ALL_CODE_CELLS_EXECUTED' and run['executed_cells']==run['code_cells'] and not run['errors']
    verified(run['notebook'])
    assert book.metadata['automx']['flow']=='flow2_fresh_inline_v3'
    start=json.loads((work/'fresh_start.json').read_text());assert start['pre_existing_results']==0 and start['reuse'] is False
    manifest=json.loads((work/'runall_manifest.json').read_text());native=[]
    for name,ref in manifest['native_steps'].items():
        path=verified(ref);record=json.loads(path.read_text());log=verified(record['log'])
        assert log.is_relative_to(folder) and log.stat().st_mtime>=start['started_epoch_s'],name
        for output in record.get('outputs',[]):verified(output)
        native.append({'step':name,'returncode':record['returncode'],'elapsed_s':record['elapsed_s'],'log':str(log)})
    assert len(native)>=54
    pilot=json.loads((work/'fresh_pex_before_after.json').read_text())
    assert pilot['before']['gap_v']<0 and pilot['after']['gap_v']>0
    for variant in ('before','after'):
        for job in pilot[variant]['jobs']:
            assert job['returncode']==0
            log=Path(job['log']);assert log.is_relative_to(work) and log.stat().st_mtime>=start['started_epoch_s']
    mha=json.loads(verified(manifest['views']['analog_adc_mha']).read_text())
    assert mha['projection_transactions']==32 and mha['unique_holdout_patterns']==30 and mha['relative_l2']<=.25
    fresh_activity=json.loads(verified(manifest['views']['fresh_activity']).read_text());assert fresh_activity['reuse'] is False
    text=[]
    for cell in book.cells:
        for output in cell.get('outputs',[]):
            if output.output_type=='stream':text.append(output.text)
            elif 'text/markdown' in output.get('data',{}):text.append(output.data['text/markdown'])
            elif 'text/plain' in output.get('data',{}):text.append(output.data['text/plain'])
    visible='\n'.join(text)
    assert not re.search(r'(?i)sha[-_ ]?256|\b[0-9a-f]{64}\b',visible),'Digest remains visible in cell output'
    assert 'REUSE (hash verified)' not in visible and 'SAVED NATIVE LOG (historical)' not in visible
    assert 'INLINE IMPLEMENTATION' not in visible and 'INLINE NATIVE SOURCE' not in visible
    assert 'Historical recipe retained:' not in visible
    assert '[RTL/SAR]' in visible and 'decision' in visible and 'EOC 1' in visible
    assert 'lines retained in log' not in visible
    assert 'NATIVE ngspice OUTPUT' in visible and 'result_code_12bit' in visible
    for marker in ('RUN synthesis','RUN streamout','RUN signal_lvs','RUN timing'):assert marker in visible,marker
    sources=json.loads(verified(manifest['inline_sources']).read_text());checked=0
    header=('from __future__ import annotations\nfrom pathlib import Path\nimport sys\n'
        +'PROJECT_ROOT=Path('+repr(str(ROOT))+')\nINLINE_ROOT=Path('+repr(str(work/'notebook_sources/automx_nb_inline_v1'))+')\n'
        +'sys.path.insert(0,str(PROJECT_ROOT))\nsys.path.insert(0,str(INLINE_ROOT.parent))\n')
    for cell in book.cells:
        if not cell.source.startswith(('%%inline_module ','%%eda_source ')):continue
        first,_,source=cell.source.partition('\n');name=first.split(maxsplit=1)[1]
        text=verified(sources[name]).read_text();defs=source.partition('# NOTEBOOK_RUN\n')[0]
        expected=(header if first.startswith('%%inline_module') else '')+defs
        assert text in (expected,expected+'\n'),cell.id
        checked+=1
    assert checked==len(sources)
    result={'status':'FRESH_RUNALL_COMPLETED','session':str(folder),'notebook':str(book_path),'work':str(work),
        'code_cells_executed':run['executed_cells'],'execution_mode':run.get('execution_mode','single_kernel_run_all'),'elapsed_s':run['elapsed_s'],'initial_result_files':0,'reuse':False,
        'fresh_native_steps':len(native),'fresh_pex_jobs':4,'native_steps':native,
        'pex_before_gap_mv':pilot['before']['gap_v']*1000,'pex_after_gap_mv':pilot['after']['gap_v']*1000,
        'projection_transactions':mha['projection_transactions'],'unique_holdout_patterns':mha['unique_holdout_patterns'],
        'relative_l2_quantized_reference':mha['relative_l2'],'relative_l2_floating_reference':mha['floating_reference_relative_l2'],
        'inline_sources_checked':checked,'visible_digests':0,'gds':manifest['views']['gds']['path'],
        'loader_banners':0,'native_output_mode':'live_stdout_stderr','embedded_images':sum('image/png' in o.get('data',{}) for c in book.cells for o in c.get('outputs',[]))}
    save(folder/'fresh_verification.json',result);save(ROOT/'docs/flow2_fresh_verification_20261023.json',result)
    presented=apply_front_matter(copy.deepcopy(book))
    nbformat.write(presented,ROOT/'AutoMX_CIM_Sky130_MHA.ipynb')
    print(json.dumps({k:v for k,v in result.items() if k!='native_steps'},indent=2))
    return result

if __name__=='__main__':verify()
