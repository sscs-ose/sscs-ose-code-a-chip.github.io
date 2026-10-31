#!/usr/bin/env python3
"""Check pilot preparation and offline statistics without any model calls."""
import json
import hashlib
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch
import run_comparison
import summarize_comparison

ROOT=Path(__file__).resolve().parents[1]


def check():
    expected=json.loads((ROOT/'results/comparison/direct-1/result.json').read_text())['input_sha256']
    original=json.loads((ROOT/'results/comparison/summary.json').read_text())['treatments']
    with tempfile.TemporaryDirectory(prefix='chipwave-pilot-check-') as directory:
        root=Path(directory)
        seed=root/'source/generation_seed/tb';seed.mkdir(parents=True)
        shutil.copy2(ROOT/'generation_seed/tb/npu_smoke_tb.sv',seed/'npu_smoke_tb.sv')
        # The isolated source has no private design/ directory.
        with patch.object(run_comparison,'ENTRY',root/'source'):
            for mode in ('direct','platform'):
                project=root/mode;project.mkdir()
                run_comparison.prepare(project,mode)
                for name,sha in expected.items():
                    assert hashlib.sha256((project/name).read_bytes()).hexdigest()==sha,name
        for mode in ('direct','platform'):
            for number in range(1,6):
                folder=root/'results/comparison'/f'{mode}-{number}';folder.mkdir(parents=True)
                for name in ('result.json','usage.json'):
                    shutil.copy2(ROOT/'results/comparison'/f'{mode}-{number}'/name,folder/name)
        with patch.object(Path,'home',side_effect=AssertionError('offline statistics must not read HOME')):
            summarize_comparison.summarize(root)
        observed=json.loads((root/'results/comparison/summary.json').read_text())['treatments']
        assert observed==original
        broken=root/'results/comparison/direct-1/usage.json'
        data=json.loads(broken.read_text());data['sessions'].append(data['sessions'][0]);broken.write_text(json.dumps(data))
        try:summarize_comparison.trial_usage(broken,'direct',1)
        except AssertionError:pass
        else:raise AssertionError('duplicate model session must be rejected')
    print('PILOT_PREPARATION_AND_OFFLINE_USAGE_SELF_CHECK_PASS; model_calls=0')


if __name__=='__main__':check()
