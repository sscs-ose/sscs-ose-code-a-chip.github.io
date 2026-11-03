"""Ordinary constrained selection from audited matched evidence.
SPDX-License-Identifier: Apache-2.0
"""
import math
def choose(audit, *, required, anchor):
    required = tuple(required)
    if audit.get('status') != 'audited' or not required or anchor not in required:
        raise ValueError('Audited evidence and an anchor within required histories are needed')
    if len(set(required)) != len(required):
        raise ValueError('Duplicate histories are ambiguous')
    rows = audit['rows']
    index = {(r['condition'], r['variant']): r for r in rows}
    if len(index) != len(rows):
        raise ValueError('Duplicate circuit/history evidence')
    eligible = []
    for variant in sorted({r['variant'] for r in rows}):
        cases = [index.get((name, variant)) for name in required]
        if not all(r is not None and r['status'] == 'completed' and r.get('cold_pass')
                   and r.get('prior_verified') and r.get('functional_requirement_met')
                   for r in cases):
            continue
        work = index[(anchor, variant)]['source_work_delivered_J']
        if not isinstance(work, (int, float)) or isinstance(work, bool) or not math.isfinite(work) or work < 0:
            continue
        eligible.append((work, variant))
    return min(eligible)[1] if eligible else None
