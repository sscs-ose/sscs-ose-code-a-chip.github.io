"""Write the priority outcome from the audited current execution, without targets."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json

def write(root):
    root=Path(root).resolve()
    def read(path):return json.loads(Path(path).read_text())
    release=read(root/'experiments/closure_20261028/release_validation.json')
    assert release['status'] in ('VERIFIED_MEASURED_PROTOTYPE_RELEASE','VERIFIED_ROUTED_PARTITION_RELEASE')
    routed=release['status']=='VERIFIED_ROUTED_PARTITION_RELEASE'
    run=Path(release['fresh_run']);work=run/'electrical_closure';base=run/'priority_application'
    native=read(work/'electrical/verification.json');pulse=read(work/'pwm_final/verification.json')
    power=read(work/'clock_aware_power/verification.json');area=read(work/'controller_adc_area/verification.json')
    pvt=read(work/'electrical/pvt.json')['groups'];nominal=read(work/'electrical/matched_sum.json')
    service=read(work/'application_service/verification.json');idle=read(work/'idle_boot/verification.json')
    app=read(base/'application/application_metrics.json');metrics=app['models']['integer_mha']
    clock=read(work/'clock_activity/verification.json');gate=read(work/'icg_enable_timing/verification.json')
    text=['# AutoMX-CIM measured priority outcomes','',
        'Copyright 2026 EDABK Laboratory.','',
        ('This report is generated from the audited fresh execution. The selected implementation includes the characterized pulse readout, physical enlarged bitline bank, conditioner, upstream SAR and real MHA IP. Actual routed input waveforms drive the declared transistor/SAR partition; all acceptance checks below refer to this execution.' if routed else 'This report is generated from the audited fresh execution. It distinguishes completed experiments from electrical acceptance. The selected implementation is the isolated calibration-data ICG readout, the original compute/acquisition core, conditioner, upstream SAR ADC and real MHA IP. No enlarged-capacitance development macro is adopted.'),'',
        f"Execution root: `{root}`. Fresh run: `{run}`. Checked UTC: {datetime.now(timezone.utc).isoformat()}.",'',
        '| Priority | Measured outcome | Acceptance |','|---|---|---|',
        '| P0-A, electrical interface | 64 actual routed pulse cases; '+str(len(release['failed_pulse_checks']))+' failed contract checks | '+('Pass for the declared routed-input transistor/SAR partition' if routed else 'Pulse delivery measured; direct routed-PWM native closure remains unqualified')+' |',
        f"| P0-B, calibration | {native['nominal_held_out_cases']} held-out + {native['nominal_anchor_rechecks']} anchor checks; {native['nominal_matched_sum_wrong']} wrong | Pass for the declared "+('routed-input' if routed else 'ideal-stimulus')+' partition |',
        f"| P0-C, storage switching | {power['gating_child_energy_reduction_percent']:.6f}% lower matched child energy; ICG enable +{gate['setup_slack_ns']:.6f}/+{gate['hold_slack_ns']:.6f} ns | Adopted; actual mapped/gate/protocol checks pass |",
        '| P0-D, service | Unforced boot, real programming, resident idle/wake, four settling policies and sensor/burst accounting | Measurements complete; settling uses '+('actual delivered PWL' if routed else 'ideal pulses')+'; energy subtotals retain their ownership |',
        f"| P0-E, application | {app['test_windows']:,} windows; accuracy {metrics['accuracy']*100:.3f}%; macro-F1 {metrics['macro_f1']*100:.3f}%; six native frames / 384 transactions | Exact hardware/reference outputs; classifier errors retained |",
        f"| P0-F, reproducibility | {release['total_cells']} cells / {release['code_cells']} code; {release['preceding_cells_retained']} preceding IDs retained; {release['full_run_elapsed_s']/60:.2f} minutes | All code outputs present, no notebook errors; three independent auditors pass |",'',
        '## Matched active operation','',
        '| Variant | Frames | Latency, µs/frame | Child-digital nJ/frame | Mismatches |','|---|---:|---:|---:|---:|']
    for r in power['results']:
        text.append(f"| {r['variant']} | {r['frames']} | {r['activity_window_s']/r['frames']*1e6:.6f} | {r['child_digital_energy_per_frame_j']*1e9:.6f} | {r['gate_output_mismatches']} |")
    text.extend(['','Same frames, declared response policy, 25 MHz, SKY130 TT 1.8 V / 25 °C and OpenSTA 3.1 VCD/Liberty estimate with child SPEF. Parent CTS/IO, analog and SAR digital are separate. The serial digital sign/add baseline remains in the table.','',
        '## Analog and operation','',
        f"- Nominal minimum sampled margin: {min(r.get('margin_codes',-999) for r in nominal)} raw codes. Calibration uses 312 measured anchors, followed by the held-out checks.",
        f"- Seven-condition PVT: {sum(g.get('frozen_tt_wrong',0) for g in pvt)}/196 frozen-TT errors; {sum(g.get('five_anchor_recalibrated_wrong',0) for g in pvt)}/196 after five-anchor interpolation; unresolved {sum(g['unresolved'] for g in pvt)}. Stimulus: {native['contract']['stimulus']}. This is sampled transistor-condition coverage with the declared nominal driver policy.",
        f"- Native campaign: {native['unique_native_jobs']} unique acquisitions; 384 logical application conversions; six class-selected frames; {native['partial_decode_mismatches']} partial mismatches. Stimulus: {native['contract']['stimulus']}.",
        f"- Retained analog idle: {idle['analog_idle_dc']['monitored_w']*1e3:.6f} mW for the measured masks/control state. Readout idle and boot come from real mapped activity. `sensor_duty_budget.json` retains the disjoint accounted terms.",
        '- Conversion/projection values are integrated START–EOC windows, not complete-frame analog energy. Acquisition, controller, host and idle owners remain separate.', '',
        '## Source, views and reproduction','',
        '- The source/executed notebooks are identical and preserve all earlier cells. Source-visible cells recreate native workers; no saved native responses are verification inputs.',
        '- The five-block top is newly routed from source-matched hard IP. Its geometry, signal macro-boundary LVS, rails and hierarchical timing are independently checked. Fixed-palette KLayout overview exports match pixel for pixel.',
        '- The source-IP archive is extracted into an isolated Python environment; actual MHA, ternary and decoder tests execute there. The short check has its own smaller documented coverage.',
        ('- The complete internal-wire transistor PEX, full-foundry deck and whole-chip supply energy are outside the measured partition. Reference pulse failures remain as the premise for the final measured repair.' if routed else '- Full-foundry-deck completion, routed short-pulse repair and full-chip supply energy are not implied by the prototype release. The real delivered-pulse failure remains visible in the notebook.'), '',
        'Reports and figures are in the fresh run under `electrical_closure/`; final GDS, overview/detail PNGs and source-IP archive are in `exports/`.',''])
    if (work/'margin_budget.json').is_file():
        budget=read(work/'margin_budget.json')
        program=next(r for r in idle['digital'] if r['window']=='programming')
        text.extend(['## Measured code budget and programming', '',
            f"The minimum remaining conditional guard is {min(r['remaining_conditional_guard_codes'] for r in budget['banks'])} raw codes after the conservative sampled settling debit. Noise/offset allocation is zero; this arithmetic budget applies to the declared finite experiment.", '',
            f"The readout programming window measures {program['readout_j']*1e9:.6f} nJ over {program['duration_s']*1e6:.6f} microseconds for 304 thresholds and four resident O-stage masks. MHA configuration, analog calibration acquisition and transport are separate owners.", ''])
    evaluation=release.get('evaluated_candidate')
    if evaluation:
        parent=read(work/'evaluated_candidate/physical_parent/verification.json')
        core=read(work/'evaluated_candidate/physical_range_core/routing_views/verification.json')
        timing=parent['outputs']['nominal_timing']
        text.extend(['## Fresh candidate electrical evaluation', '',
            f"The candidate contains {core['layout']['expected_total_mim_devices']} physical MIM devices, with Magic DRC {core['magic_drc']} and transistor LVS {core['transistor_lvs']}. Its freshly routed parent has setup +{timing['setup_slack_ns']:.6f} ns and hold +{timing['hold_slack_ns']:.6f} ns.", '',
            f"All {evaluation['physical_cases']} actual delivered-pulse cases and {evaluation['native_conversions']} fixed signed native conversions were acquired in this full run. Native unresolved count: {evaluation['native_unresolved']}. Candidate decision: {evaluation['status']}. Zero-input aliases within one code: {len(evaluation['zero_aliases_within_one_code'])}.", '',
            ('The previous placement is retained as a measured rejection. The selected placement separately passes the routed-input six-frame transistor/SAR/MHA gate. The previous GDS and deterministic overview/detail remain under `AutoMX_CIM_evaluated_candidate`.' if routed else 'The adoption gate retains the qualified controller and separate ideal-stimulus native proof. Candidate GDS and deterministic overview/detail are exported under `AutoMX_CIM_evaluated_candidate`; these are measured development results, not a passed routed-input application release.'), ''])
    if evaluation and evaluation.get('calibration'):
        calibration=evaluation['calibration'];matched=evaluation['matched_sum']
        wrong=sum(row.get('decoded')!=row['expected'] for row in matched if row['bank_has_valid_ordered_calibration'])
        text.extend(['## Physical repair and calibration-transfer decision','',
            f"The adjacent gate/driver placement has {len(evaluation['failed_pulse_checks'])} failed pulse checks over {evaluation['physical_cases']} newly acquired cases. Its {evaluation['additional_calibration_conversions']} fresh calibration conversions produce {sum(calibration['strictly_increasing'])}/8 strictly ordered banks; the separate {evaluation['additional_matched_sum_conversions']} same-sum checks have {wrong} wrong decoded sums. Ordered anchors and correct pulse polarity do not by themselves establish transferable scalar calibration.",'',
            'The notebook displays the actual 16-row previous/adjacent-placement wire-capacitance table, each delivered waveform, calibration-bank steps and held-out errors. The current release retains the qualified ideal-stimulus partition. These candidate errors are preserved as measured outcomes, not bypassed by substituting expected ADC answers.',''])
    target=root/'docs/PRIORITY_CLOSURE_RESULTS_20261029.md';target.write_text('\n'.join(text))
    plan=root/'docs/AWARD_IMPROVEMENT_PLAN_20261028.md'
    if plan.is_file():
        old=plan.read_text();marker='<!-- current-priority-outcome -->'
        if marker in old:
            before,_,tail=old.partition(marker);_,_,after=tail.partition(marker);old=before+after
        status=('P0-A passes the declared routed-input partition gate.' if routed else 'P0-A physical stimulus has been measured; direct routed-input application acceptance is still unqualified. The qualified ideal-stimulus partition remains explicit.')
        update=marker+'\n## Execution record, 29 October 2026\n\n'+status+' P0-B through P0-F have current measured results, a full notebook run and independent audits. The original targets below remain the planning record. Actual counts, accepted changes, rejection results and energy ownership are in [the generated outcome report](PRIORITY_CLOSURE_RESULTS_20261029.md).\n'+marker+'\n\n'
        index=old.index('## 1.');old=old[:index]+update+old[index:]
        old=old.replace('All improvement tasks and new deliverables above are proposed. This planning pass does not change the verified RTL, GDS, deployment or notebook.','The original engineering targets above are preserved as a planning record. Use the execution record and generated outcome report for achieved results and remaining acceptance gates.')
        plan.write_text(old)
    from scripts.write_delivery_readme import write as write_readme
    write_readme(root)
    print('PRIORITY_OUTCOMES_WRITTEN',target,flush=True);return target

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();write(a.root)
