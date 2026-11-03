"""Check the public name and entry points while preserving historical source identities."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]

def run():
    config = tomllib.loads((ROOT/'runtime/pyproject.toml').read_text())
    assert config['project']['name'] == 'chipwave-case-runtime'
    assert config['project']['scripts']['chipwave'] == config['project']['scripts']['chip-nebula']
    for item in json.loads((ROOT/'runtime/used-components.json').read_text())['files']:
        assert hashlib.sha256((ROOT/'runtime/src'/item['path']).read_bytes()).hexdigest() == item['sha256']
    result = subprocess.run([sys.executable, '-m', 'chip_nebula.cli.commands', '--help'], capture_output=True, text=True, check=True)
    assert 'usage: chipwave' in result.stdout and 'ChipWave' in result.stdout
    book = json.loads((ROOT/'ChipWave.ipynb').read_text())
    assert book['metadata']['title'].startswith('ChipWave: ')
    assert book['metadata']['chipwave_submission']['authors'][0] == 'Xiang Li'
    for name in ['ChipWave.ipynb','ChipWave.html','README.md','figures/ChipWave_Workflow.html']:
        text = (ROOT/name).read_text()
        assert 'ChipWave' in text
        assert 'ChipNebula_CPU' not in text and 'ChipNebula_Workflow' not in text
    assert not (ROOT/'ChipNebula_CPU.ipynb').exists()
    assert not (ROOT/'ChipNebula_CPU.html').exists()
    print('CHIPWAVE_BRANDING_PASS: public names, authors, CLI aliases and runtime source hashes; no model or physical calls')

if __name__ == '__main__':
    run()
