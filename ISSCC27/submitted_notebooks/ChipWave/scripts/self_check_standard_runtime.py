"""Check the released standard-flow assets without executing agents or EDA."""
from pathlib import Path
import hashlib
import json
import chip_nebula
from chip_nebula.taskgraph.static_cli import load_compiled_recipe
from chip_nebula.taskgraph.specification_flow import confirm_prepare_page

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'runtime/src'
manifest = json.loads((ROOT / 'runtime/used-components.json').read_text())
for row in manifest['files']:
    assert hashlib.sha256((source / row['path']).read_bytes()).hexdigest() == row['sha256']
package = Path(chip_nebula.__file__).parent
compiled = load_compiled_recipe(
    package / 'configs/recipes/specification-to-gds.yaml',
    workflow_id='public-standard-check', goal='asset validation only',
    parameters={'source': 'not-executed-source'}, framework='codex', model='gpt-6.1-sol',
    reasoning_effort='high', baseline_commit='0' * 40, workers=2)
assert len(compiled.tasks) == 20
assert len({task.id for task in compiled.tasks}) == 20
assert callable(confirm_prepare_page)
print('PUBLIC_STANDARD_RUNTIME_PASS: manifest hashes, 20 unique compiled Tasks, confirmation API; no model/tool runs')
