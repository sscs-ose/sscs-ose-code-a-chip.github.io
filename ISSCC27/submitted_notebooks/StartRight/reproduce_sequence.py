"""Reproduce the matched retained-state and normal-command lesson.
SPDX-License-Identifier: Apache-2.0
"""
import platform, sys
from check_reset_contract import checks
from sequence_evidence import audit
from reset_sequence import HERE, run_sequence, save


def main():
    tested = checks(); saved = audit()
    retained = run_sequence(command=False); commanded = run_sequence(command=True)
    assert retained['status'] == commanded['status'] == 'completed'
    assert [r['observed_pass'] for r in retained['cases']] == [True, True]
    assert all(r['declared_precondition_verified'] and not r['alternate_state_exercised'] and not r['sampled_restoration_observed'] for r in retained['cases'])
    assert [r['observed_pass'] for r in commanded['cases']] == [False, True]
    assert [r['sampled_restoration_observed'] for r in commanded['cases']] == [False, True]
    assert all(r['declared_precondition_verified'] and r['alternate_state_exercised'] and r['events'][0]['pass_contract'] for r in commanded['cases'])
    record = dict(status='passed', python=sys.version.split()[0], platform=platform.platform(), checks=tested, saved_waveform_pairs=len(saved['cases']),
                  retained=retained, commanded=commanded, scope='Four fresh TT simulations, six hand-computed monitor checks and 20 saved waveform-pair audits. Failed RC recovery is an expected reproduced result. Same host execution is not independent review.')
    save(HERE/'results/reproduction/sequence_short.json',record)
    print('PASS: fresh matched state-coverage regression.',flush=True)
    return record


if __name__ == '__main__':main()
