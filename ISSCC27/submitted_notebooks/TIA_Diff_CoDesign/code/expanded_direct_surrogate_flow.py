"""Expanded direct-exit surrogate co-design inside an explicit trained geometry domain.

Transformer S data and checkpoints retain physical P/Pbar/S/Sbar port order.
The requested permutation is applied once, at the circuit interface. Surrogate
results are proposals: only a later independent, full-grid EM circuit replay can
qualify the resulting circuit.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np
import xfmr_schema as XG
import campaign_history as H
import terminal_policy as TP
from joint_passives import GeometryRejected,PredictionRejected,SpiralModels,feature_range,proposal_binding

HERE = Path(__file__).absolute().parent
DEFAULT_GEOMETRY = dict(w=6., wp=6., s=3., np=2, ns=2, D=90.,
                        topology=3, gap=25., ring_w=30., port_backing=1)
DEFAULT_PERMUTATION = (3, 2, 0, 1)
CANDIDATE_REPLAY_STEP_GHZ = 1.0


def stamp():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    for attempt in range(6):
        try:
            os.replace(temp, path)
            break
        except PermissionError:
            if os.name != 'nt' or attempt == 5:
                raise
            time.sleep(.05 * (attempt + 1))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def input_hashes(args):
    """Bind restart reuse to executable sources and every passive/geometry input."""
    names = H.SOURCE_FILES
    result = {'source': {name: sha256(HERE / name) for name in names}, 'passives': {}}
    result['passives']['spiral_checkpoint'] = sha256(args.smodel)
    result['spiral_domain'] = sha256(args.spiral_domain)
    for name in ('joint_passives.py','spiral_gen.py','features14.py','section21_parameters.py','multiturn_experiment.py'):
        result['source'][name] = sha256(HERE / name)
    result['geometry'] = sha256(args.geometry) if args.geometry else None
    result['data_domain'] = sha256(args.domain)
    result['active_domain'] = sha256(args.active_domain)
    result['campaign_record'] = sha256(args.campaign_record) if args.campaign_record else None
    result['stage_observations'] = H.report_hashes(args)
    return result


def direct_geometry(geometry):
    """Validate the generator's physical direct-exit size/clearance restrictions."""
    g = XG.normalize(geometry)
    if g['topology'] != 3 or not g['port_backing']:
        raise ValueError('Direct co-design requires topology=3 with EM-backed ports')
    p, width = max(g['w'], g['wp']) + g['s'], max(g['w'], g['wp'])
    turns = max(g['np'], g['ns'])
    if g['D'] / 2 - turns * p - max(5., width) / 2 - width / 2 < g['s']:
        raise ValueError('D too small for the direct generator winding and via clearance')
    if g['gap'] < width + 2 * g['s'] + 5.:
        raise ValueError('Ground gap too small for the Metal5 jumper vias')
    return g


def validate_physical_candidate(geometry):
    """Reject real spacing/via/connectivity failures before circuit optimization."""
    return _validate_physical_candidate(json.dumps(XG.normalize(geometry), sort_keys=True))


from functools import lru_cache


@lru_cache(maxsize=12000)
def _validate_physical_candidate(encoded):
    import tempfile
    import direct_generator_snapshot as G
    geometry = json.loads(encoded)
    try:
        lib, _, nets, ports, settings = G.build_from_geometry(geometry, name='CANDIDATE')
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'candidate.gds'
            lib.write_gds(str(path))
            G.check(path, nets, ports, settings)
    except (AssertionError, ValueError) as exc:
        raise ValueError('Physical geometry check failed: ' + str(exc)) from exc
    return True


GEOMETRY_DIMENSIONS = ('w', 'wp', 's', 'D', 'gap', 'np', 'ns', 'ring_w')
INTEGER_DIMENSIONS = ('np', 'ns')


def domain_spec(value, key):
    """Normalize numeric fixed values, choices, or explicit numeric ranges."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value = {'value': value}
    if isinstance(value, (tuple, list)):
        value = {'choices': list(value)}
    if not isinstance(value, dict):
        raise ValueError(f'{key}: domain must be numeric, choices, or a range')
    if 'value' in value:
        result = dict(kind='fixed', value=value['value'])
        numbers = [result['value']]
    elif 'choices' in value:
        choices = list(dict.fromkeys(value['choices']))
        if not choices:
            raise ValueError(f'{key}: choices cannot be empty')
        result = dict(kind='choices', choices=choices)
        numbers = choices
    else:
        kind = value.get('kind', value.get('type', 'int'))
        low, high = value.get('low', value.get('min')), value.get('high', value.get('max'))
        if kind not in ('int', 'float', 'log') or low is None or high is None or low > high:
            raise ValueError(f'{key}: require kind int/float/log and ordered low/high')
        if kind == 'int' and (int(low) != low or int(high) != high):
            raise ValueError(f'{key}: integer bounds must be integral')
        result = dict(kind=kind, low=low, high=high)
        if 'step' in value:
            step = value['step']
            if step <= 0 or kind == 'log' or (kind == 'int' and int(step) != step):
                raise ValueError(f'{key}: invalid range step')
            result['step'] = step
        numbers = [low, high]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool)
               and math.isfinite(v) and v > 0 for v in numbers):
        raise ValueError(f'{key}: all dimensions must be finite and positive')
    if key in INTEGER_DIMENSIONS and (any(int(v) != v for v in numbers)
                                      or result['kind'] in ('float', 'log')):
        raise ValueError(f'{key}: winding counts require integer or discrete domains')
    return result


def normalize_domain(record, base=None):
    """The JSON defines permitted interpolation bounds, never a training-EM ranking."""
    if not isinstance(record, dict) or record.get('schema_version', 1) != 1:
        raise ValueError('Expected geometry domain schema_version=1')
    topology = record.get('topology', 3)
    if topology not in (3, 'series_direct'):
        raise ValueError('Expanded surrogate search requires direct topology=3')
    params = record.get('parameters', record.get('bounds'))
    if not isinstance(params, dict) or not params:
        raise ValueError('Geometry domain requires a parameters mapping')
    unknown = set(params) - set(GEOMETRY_DIMENSIONS) - {'topology', 'port_backing'}
    if unknown:
        raise ValueError(f'Unknown geometry domain keys: {sorted(unknown)}')
    defaults = direct_geometry(base or DEFAULT_GEOMETRY)
    normalized = {key: domain_spec(params.get(key, defaults[key]), key)
                  for key in GEOMETRY_DIMENSIONS}
    tied = record.get('tied_widths', False)
    if not isinstance(tied, bool):
        raise ValueError('tied_widths must be true or false')
    for key, expected in (('topology', 3), ('port_backing', 1)):
        if key in params:
            spec = domain_spec(params[key], key)
            if spec != dict(kind='fixed', value=expected):
                raise ValueError(f'{key} must be fixed at {expected}')
    return dict(schema_version=1, topology=3, tied_widths=tied, parameters=normalized)


def domain_contains(spec, value):
    kind = spec['kind']
    if kind == 'fixed':
        return math.isclose(value, spec['value'], rel_tol=0, abs_tol=1e-9)
    if kind == 'choices':
        return value in spec['choices']
    if not spec['low'] - 1e-9 <= value <= spec['high'] + 1e-9:
        return False
    if kind == 'int' and int(value) != value:
        return False
    if 'step' in spec:
        fraction = (value - spec['low']) / spec['step']
        return math.isclose(fraction, round(fraction), rel_tol=0, abs_tol=1e-8)
    return True


def domain_bounds(domain):
    return {f'x_{key}': spec for key, spec in domain['parameters'].items()
            if spec['kind'] != 'fixed' and not (key == 'wp' and domain['tied_widths'])}


def geometry_from_params(params, base, domain):
    g = dict(base)
    for key, spec in domain['parameters'].items():
        if key == 'wp' and domain['tied_widths']:
            continue
        g[key] = spec['value'] if spec['kind'] == 'fixed' else params[f'x_{key}']
    if domain['tied_widths']:
        g['wp'] = g['w']
    for key, spec in domain['parameters'].items():
        if not domain_contains(spec, g[key]):
            raise ValueError(f'{key}: geometry lies outside the explicit data domain')
    return direct_geometry(g)


def permutation(values):
    p = tuple(int(i) for i in values)
    if len(p) != 4 or set(p) != set(range(4)):
        raise ValueError('Port permutation must contain 0,1,2,3 exactly once')
    return p


def permute_ports(s, order=DEFAULT_PERMUTATION):
    order = permutation(order)
    return np.take(np.take(np.asarray(s), order, axis=-2), order, axis=-1)


def load_network(path, nports):
    """Read complete raw EM data; do not project, average or change polarity."""
    import skrf
    n = skrf.Network(str(path))
    if n.nports != nports or not np.all(np.isfinite(n.s)):
        raise ValueError(f'{path}: invalid {nports}-port network')
    if len(n.f) != 1001 or not np.allclose(n.f, np.arange(1001) * 1e8, rtol=1e-9, atol=1.):
        raise ValueError(f'{path}: expected 0..100 GHz at 0.1 GHz spacing')
    if not np.allclose(n.z0, 50., rtol=0, atol=1e-6):
        raise ValueError(f'{path}: expected 50-ohm reference')
    return n.f, n.s


class DirectPredictor:
    """Shared geometry contract for surrogate prediction and later GDS generation."""
    def __init__(self, checkpoint, order=DEFAULT_PERMUTATION):
        from surrogate import Surrogate
        self.model = Surrogate(str(checkpoint))
        if self.model.geometry_schema != 'unified' or getattr(self.model.kind, 'feature_version', 1) < 2:
            raise ValueError('Direct geometry requires a unified transformer feature-v2 checkpoint')
        self.order = permutation(order)
        self.freq = self.model.freq

    def predict(self, geometries, circuit_order=True):
        geometries = [direct_geometry(g) for g in geometries]
        values = self.model.predict(geometries)
        return permute_ports(values, self.order) if circuit_order else values


@contextmanager
def circuit_grid(step_ghz):
    """Change only this process's runtime grid, then restore the circuit function."""
    import tia_sim as T
    original = T.netlist
    n_ac, n_noise = round(99 / step_ghz) + 1, round(49 / step_ghz) + 1
    if not math.isclose((n_ac - 1) * step_ghz, 99., abs_tol=1e-9) or not math.isclose((n_noise - 1) * step_ghz, 49., abs_tol=1e-9):
        raise ValueError('Circuit grid must divide both the AC and noise frequency intervals')
    def netlist(*args, **kwargs):
        text = original(*args, **kwargs)
        # Accept both original and the direct-experiment's already fine runtime wrapper.
        import re
        text, a = re.subn(r'ac lin \d+ 1G 100G', f'ac lin {n_ac} 1G 100G', text)
        text, b = re.subn(r'noise v\(outp,outn\) Iin lin \d+ 1G 50G',
                         f'noise v(outp,outn) Iin lin {n_noise} 1G 50G', text)
        if a != 1 or b != 1:
            raise ValueError('Circuit analysis commands changed; review the grid policy')
        return text
    T.netlist = netlist
    try:
        yield
    finally:
        T.netlist = original


def constraint_values(params, metrics, gain_margin_db=.2):
    """Nonpositive means feasible, including every transistor current density."""
    from active_constraint_search import constraints
    values = [float(v) if np.isfinite(v) else 1e6 for v in constraints(params, metrics)]
    values[0] += gain_margin_db
    if metrics is not None and np.isfinite(metrics.get('bw_ghz', np.nan)):
        values[1] = (34.0 - metrics['bw_ghz']) / 5.0
    return values


def summarize(params, metrics):
    import tia_sim as T
    if metrics is None:
        return None
    out = {k: float(metrics[k]) for k in T.SPEC}
    out.update(op={k: float(v) for k, v in metrics['op'].items()},
               headroom_v=float(T.headroom(metrics['op'])), jc=T.jc_of(params, metrics['op']))
    # Strict JSON leaves failed or non-finite simulations as explicit failures.
    return out if all(np.isfinite(out[k]) for k in T.SPEC) else None


def run_candidate(job):
    """Public worker; custom module:function runners support additive active connections."""
    params, geometry, models, stages, step, runner_name, gain_margin = job
    try:
        module_name, function_name = runner_name.rsplit(':', 1)
        runner = getattr(importlib.import_module(module_name), function_name)
        with circuit_grid(step):
            metrics = runner(params, *models, stages=stages)
        values = constraint_values(params, metrics, gain_margin)
        compact = summarize(params, metrics)
        if compact is None:
            values = constraint_values(params, None, gain_margin)
        feasible = compact is not None and all(v <= 0 for v in values)
        violation = sum(max(0., v) for v in values)
        objective = -compact['bw_ghz'] if compact else 1e6
        return dict(params=params, geometry=geometry, metrics_surrogate=compact,
                    constraints=values, feasible=feasible, objective=objective,
                    violation=violation, source='surrogate', status='complete' if compact else 'failed')
    except Exception as exc:
        return dict(params=params, geometry=geometry, metrics_surrogate=None,
                    constraints=constraint_values(params, None, gain_margin), feasible=False,
                    objective=1e6, violation=1e6, source='surrogate', status='failed',
                    error=f'{type(exc).__name__}: {exc}')


def active_space(stages, domain):
    """Read the independent engineering bounds; no previous design is required."""
    if stages!='123':raise ValueError('The joint search requires all three circuit stages')
    config=json.loads(Path(domain).read_text())
    expected={'N1','N2','N3','R1','R2','R3','R4','RF','C1','VB','IT'}
    if config.get('schema_version')!=1 or set(config.get('parameters',{}))!=expected:
        raise ValueError('The active domain requires three fixed multiplicities and eight circuit variables')
    bounds={}
    for key,value in config['parameters'].items():
        spec=domain_spec(value,key)
        if key in ('N1','N2','N3'):
            target={'N1':2,'N2':2,'N3':3}[key]
            if spec!=dict(kind='fixed',value=target):raise ValueError('Unexpected transistor multiplicity')
            bounds[key]=('int',target,target)
        else:
            if spec['kind'] not in ('float','log') or spec['low']>=spec['high']:
                raise ValueError('Circuit search variables require nonzero float/log ranges')
            bounds[key]=(spec['kind'],spec['low'],spec['high'])
    return bounds


def suggest(trial, bounds):
    result = {}
    for key, descriptor in bounds.items():
        if isinstance(descriptor, tuple):
            kind, low, high = descriptor
            result[key] = (trial.suggest_int(key, low, high) if kind == 'int' else
                           trial.suggest_float(key, low, high, log=kind == 'log'))
        elif descriptor['kind'] == 'choices':
            result[key] = trial.suggest_categorical(key, descriptor['choices'])
        elif descriptor['kind'] == 'int':
            result[key] = trial.suggest_int(key, descriptor['low'], descriptor['high'], step=descriptor.get('step', 1))
        else:
            result[key] = trial.suggest_float(key, descriptor['low'], descriptor['high'],
                log=descriptor['kind'] == 'log', step=descriptor.get('step'))
    return result


def optimize(args):
    """Constrained, reproducible ask/tell batches; checkpoints after each batch."""
    import optuna
    out = Path(args.output).absolute()
    out.mkdir(parents=True, exist_ok=True)
    hashes = input_hashes(args)
    saved_path = out / 'result.json' if (out / 'result.json').exists() else out / 'trials.json'
    previous = None
    if saved_path.exists():
        previous = json.loads(saved_path.read_text(encoding='utf-8-sig'))
        current_config = json.loads(json.dumps(vars(args)))
        if not (previous.get('config') == current_config
                and previous.get('xmodel_sha256') == sha256(args.xmodel)
                and previous.get('input_hashes') == hashes
                and previous.get('optuna_version') == optuna.__version__
                and previous.get('numpy_version') == np.__version__):
            raise FileExistsError('Existing result has different configuration, inputs or dependency versions; choose a fresh output directory')
        if previous.get('status') in ('complete', 'no_candidate'):
            return previous
        count = len(previous.get('rows', []))
        if count > args.trials or (count != args.trials and count % args.jobs):
            raise ValueError('Checkpoint is not a complete ask/tell batch for this budget and job count')
    base = direct_geometry(json.loads(Path(args.geometry).read_text(encoding='utf-8-sig')) if args.geometry else DEFAULT_GEOMETRY)
    domain = normalize_domain(json.loads(Path(args.domain).read_text(encoding='utf-8-sig')), base)
    predict = DirectPredictor(args.xmodel, args.permutation)
    spiral_model = SpiralModels(args.smodel,args.spiral_domain)
    bounds = active_space(args.stages,args.active_domain)
    bounds.update(domain_bounds(domain))
    bounds.update(spiral_model.bounds())
    inherited,history_info=H.observations(args,bounds,base,domain,hashes)
    inherited_count=len(inherited)
    sampler = optuna.samplers.TPESampler(seed=args.seed, multivariate=True, n_startup_trials=inherited_count+args.startup_trials,
        constraints_func=lambda t: t.user_attrs.get('constraints', [1e6]))
    study = optuna.create_study(direction='minimize', sampler=sampler)
    H.add_observations(study,inherited,bounds)
    report = previous or dict(status='running', created=stamp(), schema_version=1,
        source='surrogate_proposal_requires_independent_em', config=vars(args),
        candidate_origin='surrogate_optimizer', allows_em_dataset_fallback=False,
        data_domain=domain,
        surrogate_gain_margin_db=args.gain_margin_db,
        surrogate_gain_minimum_dbohm=59. + args.gain_margin_db,
        independent_em_gain_minimum_dbohm=59.,
        base_geometry=base, permutation=list(predict.order), xmodel_sha256=sha256(args.xmodel),
        initialization=dict(method='random',startup_trials=args.startup_trials,prior_design=None),
        within_campaign=history_info,
        input_hashes=hashes, optuna_version=optuna.__version__, numpy_version=np.__version__,
        final_grid_ghz=CANDIDATE_REPLAY_STEP_GHZ, rows=[])
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    # Recreate every batch before continuing. Suggestions must match recorded
    # params exactly; only their saved metrics are reused, never a new simulation.
    done = 0
    while done < len(report['rows']):
        count = min(args.jobs, len(report['rows']) - done)
        trials = [study.ask() for _ in range(count)]
        batch_params = []
        for trial in trials:
            params = {}
            params.update(suggest(trial, bounds))
            batch_params.append(params)
        # Every suggestion must be drawn before telling any result, matching
        # the parallel batch that originally ran.
        for trial, params, row in zip(trials, batch_params, report['rows'][done:done + count]):
            if row.get('trial') != trial.number-inherited_count or row['params'] != params:
                raise ValueError(f'Checkpoint sampler replay mismatch at trial {trial.number}')
            trial.set_user_attr('constraints', row['constraints'])
            study.tell(trial, row['objective'])
        done += count
    if done:
        print(f'direct surrogate restored {done} completed trials without rerunning them', flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        while len(report['rows']) < args.trials:
            trials = [study.ask() for _ in range(min(args.jobs, args.trials - len(report['rows'])))]
            proposals, jobs, valid_trials = [], [], []
            for trial in trials:
                params = {}
                params.update(suggest(trial, bounds))
                g = dict(base)
                basis=spiral_model.source_basis(spiral_model.geometries(params))
                try:
                    # Only the physical-generator boundary converts ValueError
                    # into an expected geometric rejection.
                    try:
                        g = geometry_from_params(params, base, domain)
                    except ValueError as exc:
                        raise GeometryRejected(str(exc)) from exc
                    TP.require_integer_geometry(g)
                    try:
                        validate_physical_candidate(g)
                    except ValueError as exc:
                        raise GeometryRejected(str(exc)) from exc
                    if spiral_model:
                        feature_range(predict.model,[g])
                        geos = spiral_model.geometries(params)
                        spiral_model.validate(geos)
                except GeometryRejected as exc:
                    row = dict(params=params, geometry=g, feasible=False, status='invalid_geometry',
                               objective=1e6, violation=1e6, constraints=constraint_values(params, None), error=str(exc),spiral_source_basis=basis)
                    proposals.append((trial, row))
                    continue
                # Inference and schema failures terminate the search. They must
                # never masquerade as an invalid layout or trigger expansion.
                sx = predict.predict([g])[0]
                if sx.shape!=(len(predict.freq),4,4) or not np.isfinite(sx).all():
                    raise ValueError('Transformer prediction has invalid shape or nonfinite values')
                try:
                    spirals = [
                        (spiral_model.freq,s) for s in spiral_model.predict(geos)]
                except PredictionRejected as exc:
                    row=dict(params=params,geometry=g,feasible=False,status='invalid_prediction',objective=1e6,
                        violation=1e6,constraints=constraint_values(params,None),error=str(exc),spiral_source_basis=basis)
                    proposals.append((trial,row));continue
                models = [('sp', predict.freq, sx)] + [('sp', f, s) for f, s in spirals]
                jobs.append((params, g, models, args.stages, args.optimization_step_ghz,
                             args.active_runner, args.gain_margin_db))
                valid_trials.append(trial)
            proposals.extend(zip(valid_trials, pool.map(run_candidate, jobs)))
            for trial, row in sorted(proposals, key=lambda item: item[0].number):
                if args.optimize_spirals and row.get('status')=='failed' and row.get('error'):
                    raise RuntimeError('Joint circuit evaluation failed: '+row['error'])
                trial.set_user_attr('constraints', row['constraints'])
                study.tell(trial, row['objective'])
                row['trial'] = trial.number-inherited_count
                if spiral_model:row['spiral_source_basis']=spiral_model.source_basis(spiral_model.geometries(row['params']))
                row['sampler_trial'] = trial.number
                if history_info['campaign_id'] is not None:
                    row['origin_stage']=args.stage_index
                    row['evaluation_id']=f"{history_info['campaign_id']}:{args.stage_index}:{row['trial']}"
                report['rows'].append(row)
            report['updated'] = stamp()
            atomic_json(out / 'trials.json', report)
            count = sum(r['feasible'] for r in report['rows'])
            print(f"expanded direct surrogate {len(report['rows'])}/{args.trials}, feasible={count}", flush=True)
    feasible = sorted((r for r in report['rows'] if r['feasible']), key=lambda r: r['objective'])
    report['best_feasible'] = feasible[0] if feasible else None
    report['best_diagnostic'] = min(report['rows'], key=lambda r: (r['violation'], r['objective']))
    # Candidate replay uses surrogate passives on their 1 GHz prediction grid.
    report.setdefault('fine_grid_replays', [])
    done_fine = {r['trial'] for r in report['fine_grid_replays']}
    for best in feasible[:5]:
        if best['trial'] in done_fine:
            continue
        p, g = best['params'], best['geometry']
        sx = predict.predict([g])[0]
        try:
            sp = [(spiral_model.freq,s) for s in spiral_model.predict(spiral_model.geometries(p))]
        except PredictionRejected as exc:
            replay=dict(params=p,geometry=g,feasible=False,status='invalid_prediction',objective=1e6,violation=1e6,
                constraints=constraint_values(p,None),error=str(exc),trial=best['trial'],spiral_source_basis=best['spiral_source_basis'])
            report['fine_grid_replays'].append(replay);report['updated']=stamp()
            atomic_json(out/'trials.json',report);continue
        models = [('sp', predict.freq, sx)] + [('sp', f, s) for f, s in sp]
        replay = run_candidate((p, g, models, args.stages, CANDIDATE_REPLAY_STEP_GHZ,
                                args.active_runner, args.gain_margin_db))
        if args.optimize_spirals and replay.get('status')=='failed' and replay.get('error'):
            raise RuntimeError('Joint candidate replay failed: '+replay['error'])
        replay['trial'] = best['trial']
        if spiral_model:replay['spiral_source_basis']=spiral_model.source_basis(spiral_model.geometries(p))
        report['fine_grid_replays'].append(replay)
        report['updated'] = stamp()
        atomic_json(out / 'trials.json', report)
    fine = sorted((r for r in report['fine_grid_replays'] if r['feasible']), key=lambda r: r['objective'])
    if fine:
        report['fine_grid_replay'] = fine[0]
        best = dict(fine[0], permutation=list(predict.order), xmodel=str(args.xmodel),
                    xmodel_sha256=report['xmodel_sha256'], circuit_grid_ghz=CANDIDATE_REPLAY_STEP_GHZ,
                    proposal_grid_ghz=CANDIDATE_REPLAY_STEP_GHZ,
                    requires_independent_em=True, stages=args.stages,
                    candidate_origin='surrogate_optimizer', allows_em_dataset_fallback=False,
                    data_domain_sha256=sha256(args.domain),
                    surrogate_gain_margin_db=args.gain_margin_db,
                    independent_em_gain_minimum_dbohm=59.)
        best.update(TP.markers())
        if spiral_model:
            best.update(joint_search=True,spiral_geometries=dict(zip(('L1','LB'),spiral_model.geometries(best['params']))),
                        spiral_model_sha256=sha256(args.smodel),spiral_domain_sha256=sha256(args.spiral_domain),
                        spiral_port_order=[0,1])
            best['spiral_source_basis']=spiral_model.source_basis(spiral_model.geometries(best['params']))
            best['joint_binding_sha256']=proposal_binding(best)
        atomic_json(out / 'best.json', best)
    report.update(status='complete' if fine else 'no_candidate', completed=True,
                  candidate_status='requires_independent_em' if fine else 'no_candidate', updated=stamp())
    atomic_json(out / 'result.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default=str(HERE))
    parser.add_argument('--xmodel', required=True)
    parser.add_argument('--domain', required=True, help='Explicit geometry domain JSON from the verified training-data pipeline')
    parser.add_argument('--smodel', required=True)
    parser.add_argument('--optimize-spirals',action='store_true',required=True,help='Search L1/Lb geometry with spiral surrogates')
    parser.add_argument('--spiral-domain',required=True,help='Explicit five-variable spiral bounds and initial geometries')
    parser.add_argument('--geometry', help='Canonical direct geometry JSON or generator sidecar')
    parser.add_argument('--active-domain',required=True,help='Explicit circuit bounds in SI units')
    parser.add_argument('--startup-trials',type=int,default=256,help='New random proposals before adaptive TPE in each stage')
    parser.add_argument('--campaign-record',help='Immutable record in the fresh stage-parent directory')
    parser.add_argument('--stage-index',type=int)
    parser.add_argument('--permutation', default='3,2,0,1')
    parser.add_argument('--stages', choices=('123',), default='123',
                        help='The constrained direct flow checks all four transistor current densities')
    parser.add_argument('--trials', type=int, default=600)
    parser.add_argument('--jobs', type=int, default=12)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--optimization-step-ghz', type=float, default=1.)
    parser.add_argument('--gain-margin-db', type=float, default=.2,
                        help='Surrogate-only gain safety margin above 59 dBohm; independent EM still checks 59')
    parser.set_defaults(optimize_geometry=True)
    parser.add_argument('--active-runner', default='tia_sim:run', help='Module:function additive active circuit runner')
    parser.add_argument('--output', '--work-dir', dest='output', required=True,
                        help='Fresh output directory; checkpoints and result saved here')
    args = parser.parse_args()
    try:
        args.permutation = permutation(args.permutation.split(','))
        if args.jobs < 1 or args.trials < 1 or args.seed < 0 or args.startup_trials<1 or args.optimization_step_ghz <= 0:
            raise ValueError('Jobs/trials/grid must be positive and seed nonnegative')
        if not math.isfinite(args.gain_margin_db) or args.gain_margin_db < 0:
            raise ValueError('Surrogate gain margin must be finite and nonnegative')
        if args.optimize_spirals and not args.spiral_domain:
            raise ValueError('Joint spiral search requires --spiral-domain')
    except ValueError as exc:
        parser.error(str(exc))
    os.environ.setdefault('TIA_TMP', '/tmp')
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    report = optimize(args)
    return 0 if report.get('fine_grid_replay', {}).get('feasible') else 2


if __name__ == '__main__':
    raise SystemExit(main())
