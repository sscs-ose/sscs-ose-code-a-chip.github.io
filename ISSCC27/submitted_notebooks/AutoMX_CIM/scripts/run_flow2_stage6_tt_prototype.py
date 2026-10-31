#!/usr/bin/env python3
"""Fast TT-only numerical prototype from verified held-node training.

No new SPICE and no qualification gate changes. Failed PVT and the old
common-mode holdout remain failed; this benchmark is not an ADC/readout model.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from automx_cim.attention import run_stage1
from automx_cim.characterization import build_characterization,evaluate_mha
from automx_cim.characterization_v2 import HeldNodeMacroModel
from automx_cim.config import Sky130MHAConfig
from scripts import run_flow2_recovery_pvt_diagnostic as diagnostic
from scripts import run_flow2_remaining_measurements as campaign
from scripts import run_flow2_stage6_v2 as qualified
from scripts import run_flow2_adc_operating_point as operating


def run(root):
    root=Path(root).resolve()
    recovery,inputs,training,decoder,recovery_sha=diagnostic._source(root)
    config_path=root/'configs/sky130_mha_tiny.json'
    config=Sky130MHAConfig.from_json(config_path)
    base=build_characterization(root,config)
    points,conditioner_sources=operating.operating_points(root,'mixed_wrapper_20261020_01_cond')
    limitations=[
        'TT held-node training model only; no coupled core/conditioner/ADC simulation',
        'No accepted ADC conversion word or measured ADC transfer used',
        'Old common-mode holdout and failed PVT gates are retained, not waived',
        'Unmeasured patterns use training level centers; tiny-MHA is a benchmark, not fresh holdout',
        'Conditioner PEX points are recorded context and are not applied as an ADC model',
        'Energy/latency remain passive-core proxies; qualification and strict Stage8 stay blocked']
    characterization={
        'format':'automx-cim-stage6-held-node-characterization-v2',
        'status':'TT_HELD_NODE_DIAGNOSTIC_V2','qualification':'NOT_QUALIFIED',
        'source_recovery_sha256':recovery_sha,'config_sha256':campaign._sha(config_path),
        'pex_sha256':inputs['pex_sha'],'model_sha256':inputs['model_sha'],
        'decoder':decoder,'physical':base['physical'],
        'training_vectors':[{'case':j['case'],'phase':j['phase'],
            'activation_x2':j['activation_x2'],'ternary_weights':j['ternary_weights'],
            'held_differential_v':[campaign._held(j,lane)[0] for lane in range(4)]} for j in training],
        'operating_point':{'corner':'tt','vdd_v':config.vdd,'temperature_c':config.temperature_c,
            'sampling_turnoff_start_ns':2.100,'held_measure_time_ns':2.4},
        'limitations':limitations}
    model=HeldNodeMacroModel(characterization)
    comparison=evaluate_mha(run_stage1(config),model)
    historical_proxies={name:comparison.pop(name) for name in
        ('energy_j_upper_proxy','latency_s_serial_proxy_per_projection') if name in comparison}
    comparison.update(format='automx-cim-stage6-tt-prototype-comparison-v1',
        status='TT_ONLY_NUMERICAL_PROTOTYPE_NOT_QUALIFIED',qualification='NOT_QUALIFIED',
        measured_pattern_invocations=model.measured_pattern_invocations,
        estimated_pattern_invocations=model.estimated_pattern_invocations,
        source_recovery_sha256=recovery_sha,config_sha256=campaign._sha(config_path),
        conditioner_pilot_points=points,conditioner_source_proofs=conditioner_sources,
        unchanged_validation_status=recovery['status'],fresh_holdout=False,
        historical_passive_core_proxies=historical_proxies,
        wrapper_energy_and_latency='NOT_MEASURED',
        strict_stage8='BLOCKED_MEASURED_READOUT_AND_WRAPPER_CONTRACT',limitations=limitations)
    folder=root/'results/sky130/stage6_v2/tt_prototype'/('source_'+recovery_sha[:12]+'_runner_'+campaign._sha(Path(__file__))[:12])
    qualified._write_once(folder/'characterization.json',characterization)
    qualified._write_once(folder/'tiny_mha_comparison.json',comparison)
    return {'status':comparison['status'],'qualification':'NOT_QUALIFIED',
        'characterization':str((folder/'characterization.json').relative_to(root)),
        'comparison':str((folder/'tiny_mha_comparison.json').relative_to(root)),
        'metrics':comparison,'new_spice_jobs':0}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    print(json.dumps(run(parser.parse_args().root),indent=2))
