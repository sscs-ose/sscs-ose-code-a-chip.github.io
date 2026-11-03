#!/usr/bin/env python3
"""Run the standard surrogate flow with an explicitly bound 1.6-V PDK policy."""
import argparse
import importlib
import json
from pathlib import Path
import sys

import expanded_direct_surrogate_flow as F
import vce_policy as V


def bind_work(out, policy_path, policy, binding):
    """A new policy cannot adopt an unqualified optimizer checkpoint."""
    out, policy_path = Path(out), Path(policy_path)
    marker = out / 'voltage_policy_binding.json'
    if marker.exists():
        if json.loads(marker.read_text(encoding='utf-8-sig')) != binding:
            raise ValueError('Voltage policy/model/source binding changed; use a fresh optimizer directory')
    elif any((out / name).exists() for name in ('trials.json', 'result.json', 'best.json')):
        raise FileExistsError('Existing optimizer evidence has no matching voltage-policy binding')
    if policy_path.exists():
        if json.loads(policy_path.read_text(encoding='utf-8-sig')) != policy:
            raise ValueError('The supplied voltage policy differs from the actual PDK policy')
    else:
        F.atomic_json(policy_path, policy)
    if not marker.exists():
        F.atomic_json(marker, binding)


def install_policy_hooks(flow, policy):
    """Apply before every constraint and summary, including parent fine-grid replay."""
    import tia_sim as T
    V.apply_voltage_policy(T, policy)
    original_constraints, original_summary = flow.constraint_values, flow.summarize
    def constraints(params, metrics, gain_margin_db=.2):
        # Custom circuit runners may reload tia_sim before returning their raw OP.
        V.apply_voltage_policy(importlib.import_module('tia_sim'), policy)
        values = list(original_constraints(params, metrics, gain_margin_db))
        values.append(V.search_constraint((metrics or {}).get('op'), policy))
        return values
    def summarize(params, metrics):
        V.apply_voltage_policy(importlib.import_module('tia_sim'), policy)
        result = original_summary(params, metrics)
        if result is not None:
            result['voltage_policy_sha256'] = policy['policy_sha256']
            result['voltage_audit'] = V.audit_op(result.get('op'), policy)
        return result
    flow.constraint_values, flow.summarize = constraints, summarize
    def restore():
        flow.constraint_values, flow.summarize = original_constraints, original_summary
    return restore


def initialize_worker(policy, original_initializer=None, original_initargs=()):
    if original_initializer is not None:
        original_initializer(*original_initargs)
    import tia_sim as T
    import expanded_direct_surrogate_flow as flow
    if V.sha256(policy['model_card_path']) != policy['model_card_sha256']:
        raise ValueError('Actual PDK model changed before the policy worker initialized')
    importlib.reload(T)
    V.apply_voltage_policy(T, policy)
    # A forked worker inherits parent hooks; a spawned worker imports original ones.
    originals = getattr(flow, '_vce_original_hooks', None)
    if originals is not None:
        flow.constraint_values, flow.summarize = originals
    install_policy_hooks(flow, policy)


def make_binding(args, policy, policy_path):
    return dict(schema_version=1, policy=policy, policy_path=str(Path(policy_path).absolute()),
                model_path=str(Path(args.xmodel).absolute()), model_sha256=F.sha256(args.xmodel),
                wrapper_source_sha256=V.sha256(__file__), policy_source_sha256=V.sha256(V.__file__),
                actual_model_card_sha256=V.sha256(policy['model_card_path']),
                input_hashes=F.input_hashes(args), config=json.loads(json.dumps(vars(args))),
                initialization=dict(method='random',startup_trials=args.startup_trials))


def policy_optimizer(original_optimize, policy_file=None, search_buffer_v=.001):
    def optimize(args):
        import tia_sim as T
        root, out = Path(args.root).absolute(), Path(args.output).absolute()
        policy = V.policy_from_pdk(root, search_buffer_v=search_buffer_v)
        policy_path = Path(policy_file).absolute() if policy_file else out / 'voltage_policy.json'
        binding = make_binding(args, policy, policy_path)
        bind_work(out, policy_path, policy, binding)
        original_pool, original_save = F.ProcessPoolExecutor, F.atomic_json
        original_bv = T.BV_CE
        originals = F.constraint_values, F.summarize
        previous_originals = getattr(F, '_vce_original_hooks', None)
        F._vce_original_hooks = originals
        restore_hooks = install_policy_hooks(F, policy)
        def pool(*args, **kwargs):
            initializer = kwargs.pop('initializer', None)
            initargs = kwargs.pop('initargs', ())
            return original_pool(*args, initializer=initialize_worker,
                                 initargs=(policy, initializer, initargs), **kwargs)
        def save(path, value):
            if isinstance(value, dict) and Path(path).name in ('best.json', 'trials.json', 'result.json'):
                value = dict(value, voltage_policy=policy, voltage_policy_sha256=policy['policy_sha256'])
                if Path(path).name == 'best.json':
                    audit = V.audit_op((value.get('metrics_surrogate') or {}).get('op'), policy)
                    if not audit['qualified'] or not audit['search_passed']:
                        raise ValueError('Optimizer best proposal violates the explicit PDK voltage policy')
                    value['voltage_audit'] = audit
            return original_save(path, value)
        F.ProcessPoolExecutor, F.atomic_json = pool, save
        try:
            result = original_optimize(args)
            if make_binding(args, policy, policy_path) != binding:
                raise ValueError('Optimizer inputs or executable sources changed during the policy-bound run')
            # Reused complete checkpoints also retain the explicit policy in the return value.
            result = dict(result, voltage_policy=policy, voltage_policy_sha256=policy['policy_sha256'])
            F.atomic_json(out / 'result.json', result)
            best = out / 'best.json'
            if best.exists():
                F.atomic_json(best, json.loads(best.read_text(encoding='utf-8-sig')))
            return result
        finally:
            restore_hooks()
            F.ProcessPoolExecutor, F.atomic_json = original_pool, original_save
            T.BV_CE = original_bv
            if previous_originals is None:
                delattr(F, '_vce_original_hooks')
            else:
                F._vce_original_hooks = previous_originals
    return optimize


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--voltage-policy', '--policy-file', dest='policy_file', type=Path)
    parser.add_argument('--search-voltage-buffer', type=float, default=.001)
    wrapper, forwarded = parser.parse_known_args()
    for flag, value in (('--trials', '6000'), ('--jobs', '8')):
        if not any(item == flag or item.startswith(flag + '=') for item in forwarded):
            forwarded += [flag, value]
    original_optimize, original_argv = F.optimize, sys.argv
    F.optimize = policy_optimizer(original_optimize, wrapper.policy_file, wrapper.search_voltage_buffer)
    sys.argv = [str(Path(F.__file__).absolute())] + forwarded
    try:
        return F.main()
    finally:
        F.optimize, sys.argv = original_optimize, original_argv


if __name__ == '__main__':
    raise SystemExit(main())
