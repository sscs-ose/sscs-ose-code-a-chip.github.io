"""Check the saved submission; this is not a fresh analog or physical signoff run."""
from pathlib import Path
import argparse
import json
import nbformat

def verify(root):
    root = Path(root).resolve()
    notebook = nbformat.read(root / 'AutoMX_CIM_Code_a_Chip.ipynb', as_version=4)
    nbformat.validate(notebook)
    cells = [c for c in notebook.cells if c.cell_type == 'code']
    assert len(notebook.cells) == 509 and len(cells) == 205
    assert len({c.id for c in notebook.cells}) == len(notebook.cells)
    assert all(c.execution_count is not None and c.outputs for c in cells)
    errors = [c.id for c in cells for o in c.outputs if o.output_type == 'error']
    assert not errors, errors
    images = sum(any(k.startswith('image/') for k in o.get('data', {})) for c in cells for o in c.outputs)
    assert images == 49, images
    authors = next(c.source for c in notebook.cells if c.id == 'project-authors')
    assert 'minh.nguyenduc1@hust.edu.vn' in authors
    team = json.loads((root / 'TEAM.json').read_text())
    assert team['contact_email'] == 'minh.nguyenduc1@hust.edu.vn'
    assert len(team['authors']) == 4
    assert next(a for a in team['authors'] if a['role'] == 'Lead')['email'] == team['contact_email']
    for name in ['README.md', 'LICENSE', 'NOTICE.md', 'CITATION.cff', 'requirements.txt',
                 'environment.yml', 'data/source_notebook_cell_ids.json', 'standalone.json',
                 'runtime_assets.json', 'run_all.sh', 'run_notebook.sh', 'execute_standalone.py',
                 'exports/AutoMX_CIM_five_block_top.gds.gz',
                 'exports/AutoMX_CIM_evaluated_candidate.gds.gz',
                 'exports/AutoMX_MHA_IP_20261028.tar.gz',
                 'results/execution/release_validation.json',
                 'results/execution/notebook_execution.json',
                 'docs/SUBMISSION_REQUIREMENTS.md', 'docs/REPRODUCIBILITY.md']:
        assert (root / name).is_file(), name
    execution = json.loads((root / 'results/execution/notebook_execution.json').read_text())
    assert execution['executed_cells'] == 205 and not execution['errors']
    assert not execution['empty_output_cells']
    release = json.loads((root / 'results/execution/release_validation.json').read_text())
    assert release['status'] == 'VERIFIED_MEASURED_PROTOTYPE_RELEASE'
    assert len(release['checks']) == 3 and all(c['returncode'] == 0 for c in release['checks'])
    from PIL import Image, ImageChops
    a = Image.open(root / 'exports/AutoMX_CIM_five_block_top_overview.png').convert('RGBA')
    b = Image.open(root / 'exports/AutoMX_CIM_five_block_top_overview_repeat.png').convert('RGBA')
    assert a.size == b.size and ImageChops.difference(a, b).getbbox() is None
    return {'status': 'PASS', 'total_cells': len(notebook.cells), 'code_cells': len(cells),
            'code_cells_with_saved_outputs': len(cells), 'execution_errors': 0,
            'embedded_images': images, 'lead_email': team['contact_email'],
            'repeated_overview_pixels_equal': True,
            'original_full_run_elapsed_s': execution['elapsed_s'],
            'scope': 'Saved notebook, team, packaged evidence and repeated render integrity; no fresh full Run All.'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = verify(args.root)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
