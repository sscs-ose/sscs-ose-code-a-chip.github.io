"""Finite observable comparisons, with no energy ranking for failed circuits.
SPDX-License-Identifier: Apache-2.0
"""


def numerical_summary(rows):
    groups=['absolute_tt_sparse_a1e-14_v1e-06','absolute_tt_sparse_a1e-15_v1e-07','absolute_tt_sparse_a1e-15_v1e-07_dt1us']
    result=[]
    for index in range(6):
        cases=[next(r for r in rows if r['id']==f'{group}_{index:03d}') for group in groups]
        assert all(r['acquisition_status']=='measured' for r in cases)
        values=[r['result'] for r in cases];reference=values[1]
        for key in ['observed_pass','declared_precondition_verified','alternate_state_exercised','sampled_restoration_observed']:
            assert all(v[key]==reference[key] for v in values)
        timing=[]
        for value in values:
            for a,b in zip(value['events'],reference['events']):
                for criterion in ['state','release']:
                    x,y=a[criterion]['final_entry_s'],b[criterion]['final_entry_s'];assert (x is None)==(y is None)
                    if x is not None:timing.append(abs(x-y))
        work=None
        if reference['observed_pass'] and reference['declared_precondition_verified']:
            base=reference['source_work']['delivered_J']
            work=max(abs(v['source_work']['delivered_J']-base)/base for v in values)
        result.append(dict(case_index=index,observed_pass=reference['observed_pass'],maximum_entry_time_difference_s=max(timing),
                           maximum_relative_delivered_work_difference_for_working_case=work))
    return dict(cases=result,qualitative_outcomes_agree=True,
                scope='Observed differences over these three completed sparse configurations, not global error bounds or physical accuracy. Source-work comparisons are restricted to working matched cases. No cross-consumer energy ranking.')
