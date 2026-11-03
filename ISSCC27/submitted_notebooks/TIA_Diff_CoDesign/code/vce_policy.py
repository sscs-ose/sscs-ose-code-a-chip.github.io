"""Explicit PDK-derived VCE qualification without editing the shared testbench."""
import hashlib
import json
import math
import os
from pathlib import Path
import re


DEVICE_NODES = dict(Q1=('v(c1)', 'v(e1)'), Q2=('v(b2)', 'v(e2)'),
                    Q3=('v(cn)', 'v(t)'), Q4=('v(cp)', 'v(t)'))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def policy_digest(policy):
    value = {key: item for key, item in policy.items() if key != 'policy_sha256'}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def policy_from_pdk(root, search_buffer_v=.001):
    """Read the actual npn13G2 model used by run_ngspice.sh and bind its bytes."""
    root = Path(root).absolute()
    from environment import pdk_root as configured_pdk
    pdk_root = configured_pdk()
    card = pdk_root / 'ihp-sg13g2/libs.tech/ngspice/models/sg13g2_hbt_mod.lib'
    text = card.read_text(encoding='utf-8', errors='replace')
    subcircuit = re.search(r'^\s*\.subckt\s+npn13G2\s+[^\n]*\n(.*?)^\s*\.ends\s+npn13G2\s*$',
                           text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if subcircuit is None:
        raise ValueError('The actual PDK npn13G2 subcircuit was not found')
    values = re.findall(r'^\s*\+\s*vce_max\s*=\s*([-+\d.eE]+)\s*$',
                        subcircuit.group(1), flags=re.IGNORECASE | re.MULTILINE)
    if len(values) != 1:
        raise ValueError('The npn13G2 model must define exactly one explicit vce_max')
    limit, buffer = float(values[0]), float(search_buffer_v)
    if not math.isfinite(limit) or limit != 1.6:
        raise ValueError('This qualification policy expects the actual npn13G2 vce_max of 1.6 V')
    if not math.isfinite(buffer) or not 0 <= buffer < limit:
        raise ValueError('Search voltage buffer must be finite, nonnegative and below the model limit')
    policy = dict(schema_version=1, device='npn13G2', model='npn13G2_NX_vbic',
                  model_card_path=str(card), model_card_sha256=sha256(card),
                  policy_source_sha256=sha256(__file__), model_vce_max_v=limit,
                  limit_v=limit, runtime_bv_ce_v=limit, search_buffer_v=buffer,
                  search_vce_limit_v=limit - buffer,
                  qualification='Every measured Q1/Q2/Q3/Q4 collector-emitter voltage must be <= 1.6 V',
                  search_rule='An additional explicit max-VCE constraint applies the recorded search buffer; the shared headroom formula is unchanged')
    policy['policy_sha256'] = policy_digest(policy)
    return policy


def validate_policy(policy):
    if (policy.get('schema_version') != 1 or policy.get('device') != 'npn13G2'
            or policy.get('model_vce_max_v') != 1.6 or policy.get('limit_v') != 1.6
            or policy.get('runtime_bv_ce_v') != 1.6
            or policy.get('policy_sha256') != policy_digest(policy)):
        raise ValueError('Voltage policy identity or hash is invalid')
    buffer = policy.get('search_buffer_v')
    if (not isinstance(buffer, (int, float)) or not math.isfinite(buffer) or not 0 <= buffer < 1.6
            or policy.get('search_vce_limit_v') != 1.6 - buffer):
        raise ValueError('Voltage policy search buffer is inconsistent')
    return policy


def apply_voltage_policy(testbench, policy):
    validate_policy(policy)
    testbench.BV_CE = policy['runtime_bv_ce_v']
    return testbench


def audit_op(op, policy):
    """Qualify the saved operating point exactly; missing nodes never become zero."""
    validate_policy(policy)
    op = op if isinstance(op, dict) else {}
    missing = sorted({node for pair in DEVICE_NODES.values() for node in pair
                      if not isinstance(op.get(node), (int, float)) or isinstance(op.get(node), bool)
                      or not math.isfinite(op[node])})
    vce = {device: float(op[collector] - op[emitter])
           if collector not in missing and emitter not in missing else None
           for device, (collector, emitter) in DEVICE_NODES.items()}
    complete = not missing
    maximum = max(vce.values()) if complete else None
    excess = {device: max(0., value - policy['limit_v']) if value is not None else None
              for device, value in vce.items()}
    total = sum(excess.values()) if complete else None
    passed = bool(complete and all(value <= policy['limit_v'] for value in vce.values()))
    return dict(qualified=passed, passed=passed, all_vce_pass=passed, complete=complete,
                vce_by_device=vce, vce_v=vce, max_vce_v=maximum, excess_v=excess,
                violation_sum=total, violation_sum_v=total, missing_nodes=missing,
                limit_v=policy['limit_v'], search_vce_limit_v=policy['search_vce_limit_v'],
                search_passed=bool(complete and maximum <= policy['search_vce_limit_v']),
                policy_sha256=policy['policy_sha256'])


def search_constraint(op, policy):
    audit = audit_op(op, policy)
    return ((audit['max_vce_v'] - policy['search_vce_limit_v']) / .1
            if audit['complete'] else 1e6)
