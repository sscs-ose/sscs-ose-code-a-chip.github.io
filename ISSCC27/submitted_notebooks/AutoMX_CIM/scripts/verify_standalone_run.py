"""Validate a completed standalone execution and its newly generated artifacts."""
from pathlib import Path
import argparse, json, datetime, re
import nbformat

def verify(root):
    root = Path(root).resolve()
    execution = json.loads((root / 'standalone_execution.json').read_text())
    assert execution['status'] == 'ALL_CODE_CELLS_EXECUTED', execution
    assert execution['executed_cells'] == execution['code_cells'] and not execution['errors']
    book = nbformat.read(root / 'AutoMX_CIM_Code_a_Chip.executed.ipynb', 4)
    assert all(c.execution_count is not None for c in book.cells if c.cell_type == 'code')
    seed_cells = json.loads((root / 'data/source_notebook_cell_ids.json').read_text())['cells']
    present = {c.id for c in book.cells}
    policy_path = root/'data/notebook_editorial_policy.json'
    retired = set(json.loads(policy_path.read_text())['remove_markdown_ids']) if policy_path.is_file() else set()
    assert not [c['id'] for c in seed_cells if c['id'] not in present and
                not (c['cell_type'] == 'markdown' and c['id'] in retired)]
    # The newest directory must itself contain the successful manifest; no fallback
    # to a previous successful run when the most recent execution failed.
    run = max((root / 'runs').glob('fresh_*'), key=lambda p: p.name)
    work = run / 'full_native/full_native'
    started = datetime.datetime.strptime(run.name.removeprefix('fresh_'), '%Y%m%d_%H%M%S_%f').replace(
        tzinfo=datetime.timezone.utc).timestamp()
    evidence = json.loads((run / 'review_data/evidence.json').read_text())
    assert len(evidence['cases']) == 41 and len(evidence['factorial']) == 4
    for case in evidence['cases']:
        for key in ('summary', 'stimulus', 'rtl_log', 'ngspice_log'):
            path = (run / 'review_data' / case[key]).resolve()
            assert path.is_relative_to(run) and path.stat().st_mtime >= started - 2, path
    for condition in evidence['factorial']:
        for job in condition['jobs']:
            for key in ('log', 'deck'):
                path = (run / 'review_data' / job[key]).resolve()
                assert path.is_relative_to(run) and path.stat().st_mtime >= started - 2, path
    manifest = json.loads((work / 'runall_manifest.json').read_text())
    assert manifest['status'] == 'STANDALONE_FRESH_ANALOG_ADC_MHA_AND_COLD_PNR_COMPLETED'
    assert manifest['placement_routing'] == 'COLD_FROM_RTL'
    assert not manifest['old_results_reused'] and not manifest['old_routed_checkpoint_reused']
    summaries = list(work.glob('conversion_*/summary.json'))
    assert len(summaries) == 41, len(summaries)
    pex = list(work.glob('fresh_pex_*/measured.json'))
    assert len(pex) == 4, len(pex)
    assert len(list(work.glob('fresh_pex_*/sum*.log'))) == 8
    for directory in (p.parent for p in summaries):
        for name in ('case.json', 'ngspice.log', 'rtl.log', 'coupled.raw'):
            assert (directory / name).stat().st_size > 0, directory / name
    views = manifest['views']
    for key in ('gds', 'def', 'lef', 'spef', 'lib', 'sdc', 'top_png'):
        path = Path(views[key]['path']).resolve()
        assert path.is_relative_to(run) and path.stat().st_size > 0, (key, path)
        assert path.stat().st_mtime >= started - 2, (key, path)
    lvs = Path(views['signal_lvs']['path']).read_text()
    assert 'Final result: Circuits match uniquely.' in lvs
    pg = json.loads(Path(views['power']['path']).read_text())
    assert pg['rails'] == {'VPWR': 'PASS', 'VGND': 'PASS'}
    pnr = json.loads((work / 'cold_pnr/step.json').read_text())
    assert pnr['returncode'] == 0 and pnr['identity']['cold_start']
    routing = max((work / 'cold_pnr/design/runs/cold/logs/routing').glob('*-detailed.log'))
    violations = re.findall(r'Number of violations = (\d+)', routing.read_text())
    assert violations, 'Detailed routing result is missing'
    review = json.loads((run / 'review_results.json').read_text())
    assert review['integer_decode_mismatches'] == 0 and review['mha_relative_l2_quantized'] == 0
    assert review['fresh_klayout_render']
    escaping = [str(p) for name in ('inputs', 'pdks', 'tools', 'rtl', 'third_party', 'data')
                for p in (root / name).rglob('*')
                if p.is_symlink() and not p.resolve().is_relative_to(root)]
    assert not escaping, escaping
    report = {'status': 'VERIFIED_FRESH_STANDALONE_RUN', 'run': str(run),
              'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'code_cells': execution['code_cells'], 'elapsed_s': execution['elapsed_s'],
              'preserved_source_cells': sum(c['id'] in present for c in seed_cells),
              'retired_source_markdown_cells': [c['id'] for c in seed_cells if c['id'] not in present],
              'original_source_cells': len(seed_cells), 'total_cells': len(book.cells),
              'fresh_conversions': len(summaries), 'fresh_pex_jobs': 8,
              'cold_pnr_elapsed_s': pnr['elapsed_s'], 'review': review,
              'routing_drc_violations': int(violations[-1]),
              'top_gds': views['gds']['path'], 'top_def': views['def']['path'],
              'escaping_source_symlinks': escaping, 'old_checkout_required': False}
    (root / 'standalone_verification.json').write_text(json.dumps(report, indent=2) + '\n')
    (root / 'LATEST_RUN.json').write_text(json.dumps({'run': str(run),
        'manifest': str(work / 'runall_manifest.json'), 'top_gds': views['gds']['path']}, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', nargs='?', default=str(Path(__file__).resolve().parents[1]))
    verify(parser.parse_args().root)
