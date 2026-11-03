"""Fresh external-consumer checks, including a declared no-dip control.
SPDX-License-Identifier: Apache-2.0
"""
import platform,sys
from external_consumer import HERE,run_external,save
from external_evidence import audit
from check_external import checks


def main():
    saved=audit();fixture_checks=checks()
    retained=run_external(command=False);normal=run_external(command=True)
    # This control is declared before acquisition: D=1 and the same clock pulse,
    # but VDD remains at its nominal value. It is outside the reset-history
    # requirement and must retain Q=1 rather than accidentally clear on D's fall.
    no_dip=run_external(command=True,low_V=1.8)
    assert all(r['status']=='completed' for r in [retained,normal,no_dip])
    assert [r['observed_pass'] for r in retained['cases']]==[True,True]
    assert all(r['declared_precondition_verified'] and not r['alternate_state_exercised'] for r in retained['cases'])
    assert [r['observed_pass'] for r in normal['cases']]==[False,True]
    assert all(r['declared_precondition_verified'] and r['alternate_state_exercised'] and r['events'][0]['pass_contract'] for r in normal['cases'])
    assert [r['observed_pass'] for r in no_dip['cases']]==[False,False]
    assert all(r['minimum_q_final_hold_V']>=1.44 for r in no_dip['cases'])
    assert all(r['declared_precondition_verified'] and r['alternate_state_exercised'] and not r['sampled_restoration_observed'] for r in no_dip['cases'])
    record=dict(status='passed',python=sys.version.split()[0],platform=platform.platform(),fixture_checks=fixture_checks,
                saved_complete=sum(r['acquisition_status']=='measured' for r in saved['cases']),saved_unresolved=sum(r['acquisition_status']=='unresolved' for r in saved['cases']),
                retained=retained,normal=normal,no_dip=no_dip,
                scope='Six fresh TT acquisitions on one upstream consumer: two retained-state, two ordinary Q=1 power-cycle and two no-dip controls. No-dip failures are expected outside-envelope observations, not in-envelope circuit failures. Existing caches are checked, no independent-machine/human claim.')
    save(HERE/'results/reproduction/external_short.json',record);print('PASS: fresh external-consumer regression and no-dip controls.',flush=True)
    return record


if __name__=='__main__':main()
