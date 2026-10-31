"""Prerequisite summaries reject stale, missing or merely asserted safety passes."""
import json
import tempfile
from pathlib import Path

from qualify_capacity_receipts import properties
from study_protocol import digest, write_json


def check():
    with tempfile.TemporaryDirectory(prefix='capacity-receipts-check-') as tmp:
        root = Path(tmp)
        for task in ('A1', 'A2', 'B1', 'B2'):
            source = root / 'tasks' / task / 'grader/reference.sv'
            source.parent.mkdir(parents=True)
            source.write_text('module fixture; endmodule\n')
            folder = 'inductive-queue-invariants-v2' if task == 'B2' else 'properties-depth12'
            path = root / 'tasks' / task / 'qualification' / folder / 'qualification.json'
            write_json(path, dict(passed=True, source_sha256=digest(source), bounded_depth=12,
                                 safety_passed=True, result_reachable=True, original_reference_unchanged=True,
                                 results=dict(base=dict(passed=True), induction=dict(passed=True))))
        assert properties(root)['passed']
        row = json.loads(path.read_text())
        for change in ({'passed': False}, {'original_reference_unchanged': False}, {'source_sha256': 'wrong'},
                       {'results': dict(base=dict(passed=True), induction=dict(passed=False))}):
            write_json(path, dict(row, **change))
            try:
                properties(root)
            except ValueError:
                pass
            else:
                raise AssertionError('Unqualified reference accepted')
        write_json(path, row)
        source.write_text('module changed; endmodule\n')
        try:
            properties(root)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed source accepted')
    return dict(passed=True, model_calls=0, physical_runs=0,
                scope='Synthetic summary-validation fixture, not a formal hardware proof.')


if __name__ == '__main__':
    result = check()
    write_json(Path(__file__).resolve().parents[1] / 'checks/prerequisite-summaries.json', result)
    print(json.dumps(result))
