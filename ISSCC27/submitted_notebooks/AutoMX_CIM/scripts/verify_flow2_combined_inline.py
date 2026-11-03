"""Verify the executed notebook, its inline snapshots and published artifacts."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
import nbformat
from scripts.flow2_runall_support import item,save,verified
ROOT=Path(__file__).resolve().parents[1]


def verify():
    book_path=ROOT/'AutoMX_CIM_Sky130_MHA.ipynb';book=nbformat.read(book_path,4)
    execution=ROOT/'docs/flow2_combined_inline_execution_20261023.json';run=json.loads(execution.read_text())
    assert run['status']=='ALL_CODE_CELLS_EXECUTED' and not run['errors']
    assert run['executed_cells']==run['code_cells']
    assert verified(run['notebook'])==book_path
    # Resolve the manifest through the active tag's portable pointer receipt.
    tag='combined_inline_srv_20261023_01'
    pointer=ROOT/'results/receipts'/('flow2_runall_'+tag+'.json')
    manifest_path=verified(json.loads(pointer.read_text())['manifest']);manifest=json.loads(manifest_path.read_text());work=manifest_path.parent
    sources=verified(manifest['inline_sources']);inline=json.loads(sources.read_text())
    history=verified(manifest['historical_evidence']);historical=json.loads(history.read_text())
    checked=0
    for cell in book.cells:
        if cell.cell_type!='code' or not cell.source.startswith(('%%inline_module ','%%eda_source ')):continue
        first,_,source=cell.source.partition('\n');name=first.split(maxsplit=1)[1]
        definitions=source.partition('# NOTEBOOK_RUN\n')[0]
        path=verified(inline[name]);text=path.read_text()
        if first.startswith('%%inline_module'):
            header=('from __future__ import annotations\nfrom pathlib import Path\nimport sys\n'
                +'PROJECT_ROOT=Path('+repr(str(ROOT))+')\nINLINE_ROOT=Path('+repr(str(work/'notebook_sources/automx_nb_inline_v1'))+')\n'
                +'sys.path.insert(0,str(PROJECT_ROOT))\nsys.path.insert(0,str(INLINE_ROOT.parent))\n')
            expected=header+definitions
        else:expected=definitions
        # IPython normalizes the terminal newline before dispatching a cell magic.
        assert text in (expected,expected+'\n'),(cell.id,name)
        checked+=1
    assert checked==len(inline)
    for value in manifest['views'].values():
        if isinstance(value,dict) and 'path' in value and 'sha256' in value:verified(value)
    for reference in manifest['native_steps'].values():
        native=json.loads(verified(reference).read_text());verified(native['log'])
        for output in native.get('outputs',[]):verified(output)
    archived=nbformat.read(ROOT/'docs/AutoMX_CIM_legacy_server_20261023.ipynb',4)
    mapping=book.metadata['automx']['historical_cell_mapping'];assert len(mapping)==len(archived.cells)==127
    for row,cell in zip(mapping,archived.cells):
        assert row['original_id']==cell.id and row['original_sha256']==hashlib.sha256(cell.source.encode()).hexdigest()
    story_path=verified(manifest['views']['measured_development_story']);story=json.loads(story_path.read_text())
    assert story['decoder_errors']['mismatches']==52 and story['decoder_errors']['samples']==128
    assert story['partition_decode']['mismatches']==0 and story['partition_decode']['samples']==256
    assert [r['markers'] for r in story['routing']]==[50,16,16,0]
    assert len(story['verified_dependency_edges'])==8 and all(r['verified'] for r in story['verified_dependency_edges'])
    assert story['final_route_dependency']['verified']
    tests=ROOT/'docs/flow2_combined_inline_tests_20261023.xml';suites=ET.parse(tests).getroot().iter('testsuite')
    stats={name:0 for name in ('tests','failures','errors','skipped')}
    for suite in suites:
        for name in stats:stats[name]+=int(suite.get(name,0))
    assert stats['tests']>=99 and stats['failures']==stats['errors']==stats['skipped']==0
    report=dict(status='COMBINED_INLINE_RUNALL_VERIFIED_WITH_PHYSICAL_WAIVERS',notebook=item(book_path),execution=item(execution),
        notebook_cells=len(book.cells),executed_code_cells=run['executed_cells'],elapsed_s=run['elapsed_s'],historical_cells_preserved=len(mapping),
        historical_recipe_cells=sum(bool(c.metadata.get('historical_recipe')) for c in book.cells),
        embedded_images=sum('image/png' in output.get('data',{}) for cell in book.cells for output in cell.get('outputs',[])),
        inline_source_count=len(inline),inline_cell_to_snapshot_bindings_verified=checked,
        native_receipts=len(manifest['native_steps']),historical_groups=len(historical),
        legacy_archive=item(ROOT/'docs/AutoMX_CIM_legacy_server_20261023.ipynb'),compact_backup=item(ROOT/'docs/AutoMX_CIM_runall_compact_20261023.ipynb'),
        cell_map=item(ROOT/'docs/flow2_combined_inline_cell_map_20261023.json'),tests=item(tests),test_results=stats,
        manifest=item(manifest_path),inline_sources=item(sources),historical_evidence=item(history),measured_development_story=item(story_path),
        gds=manifest['views']['gds'],analog_adc_mha=manifest['views']['analog_adc_mha'],
        verified_historical_dependency_edges=len(story['verified_dependency_edges']),measured_route_markers=[r['markers'] for r in story['routing']],
        drc=manifest['drc']['status'],fabrication_ready=manifest['fabrication_ready'],
        scope='Fresh env_mamba kernel executed the visible inline implementations. Historical tables replay measured reports and native logs with distinct cohorts; SHA-bound dependency edges identify reused inputs and the final routed checkpoint.')
    for path in (ROOT/'docs/flow2_combined_inline_postflight_20261023.json',ROOT/'results/receipts/flow2_combined_inline_20261023.json'):save(path,report)
    print(json.dumps({k:report[k] for k in ('notebook_cells','executed_code_cells','inline_source_count','embedded_images','verified_historical_dependency_edges','test_results','elapsed_s')},indent=2))
    return report

if __name__=='__main__':verify()
