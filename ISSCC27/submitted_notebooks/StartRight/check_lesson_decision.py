"""Exercise and decision checks against the audited measured cases.
SPDX-License-Identifier: Apache-2.0
"""
from lesson_decision import PRESETS, decision, questions, feedback, browser_payload, summary_markdown


def checks(record):
    expected = dict(limited='original', nominal_reset='digital_guard',
                    expanded='reference_supervisor', unmeasured=None)
    results = {name: decision(record, required)['selected'] for name, required in PRESETS.items()}
    assert results == expected
    bank = questions(record)
    assert {q['id']: q['expected'] for q in bank} == dict(
        cold_original='setup_missing', hot_original='reset_missed',
        hot_reference='restoration_observed', storage_control='storage_preserved')
    # The dangerous interpretation is to call a cold Q=0 a successful exercised reset.
    wrong = feedback(record, dict(cold_original='restoration_observed'))
    assert 'Recheck.' in wrong and '0/1 attempted' in wrong
    unanswered = feedback(record, {})
    assert '0/0 attempted' in unanswered and 'Correct.' not in unanswered
    right = feedback(record, {q['id']: q['expected'] for q in bank})
    assert '4/4 attempted' in right
    storage = next(q for q in bank if q['id'] == 'storage_control')
    assert storage['witnesses']['prior_Q1_verified'] and storage['witnesses']['requirement_met']
    assert storage['witnesses']['final_Q_V'] > 1.44 and not storage['witnesses']['recovery_state_met']
    # Missing evidence forces abstention even when a low-cost working anchor exists.
    missing = decision(record, ['nominal_storage', 'unmeasured_short_zero'])
    assert missing['selected'] is None and all(not c['eligible'] for c in missing['candidates'])
    payload = browser_payload(record)
    assert payload['expected_choices'] == expected
    assert len(payload['questions']) == 4
    assert '| 27 C storage | 0.894466 | 0.906937 | 1.255022 |' in summary_markdown(record)
    for answers in [dict(nonexistent='setup_missing'), dict(cold_original='looks_good')]:
        try:
            feedback(record, answers)
        except ValueError:
            pass
        else:
            raise AssertionError('Unknown exercise input was scored')
    return dict(status='passed', scope='Measured-data lesson checks; no new transistor run or human-learning evidence',
                choices=results, questions=len(bank), bad_cold_interpretation_rejected=True,
                unattempted_not_scored=True, storage_distinct_from_restoration=True,
                missing_evidence_abstains=True, unknown_inputs_rejected=True)


if __name__ == '__main__':
    import json
    from reference_evidence import audit
    print(json.dumps(checks(audit()), indent=2))
