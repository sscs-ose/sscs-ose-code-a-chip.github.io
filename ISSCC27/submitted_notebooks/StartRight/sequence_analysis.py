"""Independent ideal-RC explanation and matched working cold-window costs.
SPDX-License-Identifier: Apache-2.0
"""
from pathlib import Path
import numpy as np
from reset_contract import source_work, segment
from sequence_circuits import extended_history


def ideal_rc(points, resistance, capacitance, t):
    t = np.asarray(t, dtype=float)
    if resistance <= 0 or capacitance <= 0 or not np.isfinite([resistance, capacitance]).all():
        raise ValueError('Positive finite R and C required')
    if t.min() < points[0][0] or t.max() > points[-1][0]:
        raise ValueError('Prediction outside declared supply history')
    tau = resistance*capacitance; initial = 0.; result = np.full_like(t, np.nan)
    for (start, v0), (stop, v1) in zip(points[:-1], points[1:]):
        slope = (v1-v0)/(stop-start); mask = (t >= start) & (t <= stop); u = t[mask]-start
        one_minus = -np.expm1(-u/tau)
        result[mask] = initial*(1-one_minus)+v0*one_minus+slope*(u-tau*one_minus)
        u = stop-start; one_minus = -np.expm1(-u/tau)
        initial = initial*(1-one_minus)+v0*one_minus+slope*(u-tau*one_minus)
    if not np.isfinite(result).all():raise ValueError('Invalid prediction')
    return result


def explain(record):
    from reset_sequence import specification
    points, windows = extended_history(record['scenario'], record['contract'])
    rows = []
    for row in record['cases']:
        if row['status'] != 'measured':continue
        raw = Path(record['output_dir'])/'raw'/row['case']; d = np.loadtxt(raw/'cold.dat',skiprows=1); f = np.loadtxt(raw/'interface.dat',skiprows=1)
        # Cost is counted only over the identical working cold interval before
        # either command. The failed complete sequence has no eligible ranking.
        vectors = dict(vdd=d[:,5], i_vdd=d[:,4], v_input=f[:,6], i_input=f[:,7], v_marker=f[:,8], i_marker=f[:,9])
        tc, vc = segment(d[:,0],vectors,windows[0]['start_s'],windows[0]['stop_s'])
        work = source_work(tc,dict(VDD=(vc['vdd'],vc['i_vdd']),functional_input=(vc['v_input'],vc['i_input']),command_marker=(vc['v_marker'],vc['i_marker'])))
        result = dict(variant=row['configuration']['id'], cold_pass=row['events'][0]['pass_contract'], working_cold_delivered_J=work['delivered_J'])
        if row['configuration']['id'] == 'frozen_rc_sr':
            c = row['configuration']; predicted = ideal_rc(points,c['resistance_ohm'],c['capacitance_F'],d[:,0])
            start = windows[1]['start_s']; stop = windows[1]['ramp_end_s']; mask = (d[:,0]>=start)&(d[:,0]<=stop)
            result.update(ideal_recovery_initial_c_V=float(np.interp(start,d[:,0],predicted)),
                          measured_recovery_initial_c_V=float(np.interp(start,d[:,0],d[:,3])),
                          ideal_peak_recovery_VSG_V=float(np.max((d[:,5]-predicted)[mask])),
                          measured_peak_recovery_VSG_V=float(np.max((d[:,5]-d[:,3])[mask])),
                          maximum_ideal_gate_error_V=float(np.max(abs(predicted-d[:,3]))))
        rows.append(result)
    if not all(r['cold_pass'] for r in rows):
        for r in rows:r['working_cold_delivered_J']=None
    return dict(evidence_kind='fresh vectors plus separate ideal unloaded-RC calculation',cases=rows,
                scope='Cold cost uses only matched working pre-command intervals and every independent source. The RC prediction omits MOS loading; agreement is not silicon accuracy or a state-write guarantee.')
