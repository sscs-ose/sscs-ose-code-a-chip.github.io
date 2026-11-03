"""Preview resource ceilings or create a new, unqualified experiment workspace."""
import argparse
import json
import shutil
from pathlib import Path

from capacity_protocol import PHYSICAL_LIMITS, protocol
from study_protocol import digest, write_json


def budget():
    rules = protocol()
    return dict(pilot_sessions=len(rules['pilot_jobs']), formal_sessions=len(rules['formal_jobs']),
                logical_tokens_per_session=rules['token_limit'],
                retained_invalid_design_session_allowance=rules['token_limit'],
                combined_design_session_token_ceiling=rules['design_session_token_ceiling'],
                pilot_scoring_tokens=8 * rules['token_limit'],
                formal_scoring_tokens=84 * rules['token_limit'],
                physical_attempts_per_session=2, physical_attempts_global=rules['physical_total'],
                active_seconds_per_session=rules['active_seconds'],
                physical_wait_hours_max=rules['physical_total'] *
                    (rules['physical_seconds'] + rules['postprocess_seconds']) / 3600,
                warning='Ceilings, not forecasts or invoice limits. Qualification model calls, '
                        'in-flight Token excess and offline grading are separately accounted.')


def initialize(destination, source_scripts=None):
    source = Path(source_scripts or Path(__file__).parent).resolve()
    destination = Path(destination).expanduser().resolve()
    if destination.exists():
        raise ValueError('Use a new workspace; existing experiments are never reset')
    if source.is_relative_to(destination) or destination.is_relative_to(source.parent):
        raise ValueError('Create the new experiment outside the source experiment')
    files = sorted(source.glob('*.py'))
    if not files or any(p.is_symlink() for p in files):
        raise ValueError('Expected ordinary, public Python source files')
    destination.mkdir(parents=True)
    (destination / 'scripts').mkdir()
    for path in files:
        shutil.copy2(path, destination / 'scripts' / path.name)
    write_json(destination / 'protocol.json', protocol())
    write_json(destination / 'physical-ledger.json',
               dict(limits=PHYSICAL_LIMITS, absolute_total=194, attempts=[]))
    receipt = dict(initialized=True, qualified=False, model_calls=0, physical_runs=0,
                   budget=budget(),
                   sources={p.name: digest(p) for p in files},
                   scope='Code and fresh allocation only. No historical receipts, reference '
                         'measurements, model credentials, trial results or campaign freeze copied.')
    write_json(destination / 'initialization.json', receipt)
    (destination / 'README.md').write_text(
        '# New WorkflowCapacity experiment\n\n'
        'This workspace is not qualified to launch scored trials. Follow the public '
        '`experiments/capacity/NEW_EXPERIMENT.md` guide in the accompanying case. '
        'Set `CHIPNEBULA_CASE_ROOT` to that case, qualify the local tools and models, '
        'build and check the tasks, measure references, and create a new campaign freeze. '
        'Do not copy previous qualification receipts or unlock protocol flags manually.\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path,
                        help='Create a fresh workspace; omission only prints budgets')
    args = parser.parse_args()
    print(json.dumps(initialize(args.workspace) if args.workspace else budget(), indent=2))
