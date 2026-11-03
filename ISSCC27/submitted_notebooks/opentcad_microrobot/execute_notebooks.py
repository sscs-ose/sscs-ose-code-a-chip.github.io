"""Execute the portable front notebook and audit immutable packaged inputs."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import tempfile

import nbformat
from nbclient import NotebookClient


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execute(folder):
    folder = Path(folder).resolve()
    manifest = json.loads((folder / 'submission.json').read_text())
    expected = manifest['files_sha256']
    before = {name: digest(folder / name) for name in expected}
    drift = sorted(name for name in expected if expected[name] != before[name])
    if drift:
        raise AssertionError(f'Package differs from build manifest before execution: {drift}')
    runtime = folder / 'examples/microrobot/local_runs'
    prior_outputs = {str(p.relative_to(folder)) for p in runtime.rglob('*') if p.is_file()}
    report = {'python': platform.python_version(), 'platform': platform.platform(),
              'executed_at_UTC': datetime.now(timezone.utc).isoformat(),
              'source_checkout_required': False, 'colab_tested': False,
              'device_policy': ('Section 4: live OpenTCAD/DEVSIM solve of a generic 2-D cell; Section 5: actual '
                                'archived drift-diffusion IV tables and archived SPICE/layout evidence; '
                                'no fresh SPICE/layout run'),
              'notebooks': {}}
    with tempfile.TemporaryDirectory(prefix='opentcad-kernel-') as temporary:
        path = Path(temporary)
        kernel = path / 'kernels/opentcad-validation'
        kernel.mkdir(parents=True)
        (kernel / 'kernel.json').write_text(json.dumps({
            'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
            'display_name': 'OpenTCAD validation', 'language': 'python'}))
        os.environ.pop('PYTHONPATH', None)
        os.environ.update(JUPYTER_PATH=str(path), IPYTHONDIR=str(path / 'ipython'),
                          JUPYTER_RUNTIME_DIR=str(path / 'runtime'),
                          MPLCONFIGDIR=str(path / 'matplotlib'), PYTHONNOUSERSITE='1')
        name = 'submission.ipynb'
        notebook = nbformat.read(folder / name, as_version=4)
        nbformat.validate(notebook)
        client = NotebookClient(notebook, timeout=900, kernel_name='opentcad-validation',
                                resources={'metadata': {'path': str(folder)}})
        client.execute()
        root_text = str(folder)          # never leave the local checkout path in saved outputs
        for cell in notebook.cells:
            if cell.cell_type != 'code':
                continue
            for output in cell.outputs:
                if output.output_type == 'stream':
                    output['text'] = output['text'].replace(root_text, '<PROJECT_ROOT>')
                for mime in ('text/plain', 'text/html'):
                    if mime in output.get('data', {}):
                        output['data'][mime] = output['data'][mime].replace(root_text, '<PROJECT_ROOT>')
        nbformat.write(notebook, folder / name)
        code = [cell for cell in notebook.cells if cell.cell_type == 'code']
        report['notebooks'][name] = {
            'executed_code_cells': len(code),
            'errors': sum(output.output_type == 'error' for cell in code for output in cell.outputs),
            'embedded_plots': sum('image/png' in output.get('data', {})
                                  for cell in code for output in cell.outputs)}
    changed = sorted(name for name, checksum in before.items()
                     if name != 'submission.ipynb' and digest(folder / name) != checksum)
    report['archive_files_checked'] = sum('/results/' in name for name in before)
    report['archive_files_changed'] = [name for name in changed if '/results/' in name]
    report['source_files_changed'] = [name for name in changed if '/results/' not in name]
    report['input_files_checked'] = len(before) - 1
    report['pre_execution_front_notebook_sha256'] = before['submission.ipynb']
    report['executed_front_notebook_sha256'] = digest(folder / 'submission.ipynb')
    report['local_outputs_sha256'] = {str(p.relative_to(folder)): digest(p)
        for p in sorted(runtime.rglob('*')) if p.is_file()
        and str(p.relative_to(folder)) not in prior_outputs}
    report['manifest_seal_required'] = False
    (folder / 'execution_validation.json').write_text(json.dumps(report, indent=2) + '\n')
    if changed:
        raise AssertionError(f'Notebook changed packaged inputs: {changed}')
    # Explicitly seal only the two declared execution outputs, preserving every
    # immutable input checksum from the original build manifest.
    manifest['files_sha256']['submission.ipynb'] = digest(folder / 'submission.ipynb')
    manifest['files_sha256']['execution_validation.json'] = digest(folder / 'execution_validation.json')
    manifest['execution_note'] = 'Front notebook executed in this folder; immutable inputs verified unchanged'
    manifest['execution_validation_sha256'] = digest(folder / 'execution_validation.json')
    (folder / 'submission.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    print(json.dumps(execute(parser.parse_args().folder), indent=2))
