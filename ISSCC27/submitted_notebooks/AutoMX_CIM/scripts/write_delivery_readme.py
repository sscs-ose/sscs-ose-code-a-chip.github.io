"""Write the entry instructions and headline results from the audited release."""
from pathlib import Path
import json


def write(root):
    root=Path(root).resolve()
    def read(path):return json.loads(Path(path).read_text())
    release=read(root/'experiments/closure_20261028/release_validation.json')
    run=Path(release['fresh_run']);work=run/'electrical_closure'
    application=read(run/'priority_application/application/application_metrics.json')
    metrics=application['models']['integer_mha'];float_metrics=application['models']['float']
    native=read(work/'electrical/verification.json');power=read(work/'clock_aware_power/verification.json')
    text=['# AutoMX-CIM: calibrated mixed-signal attention','',
        'Copyright 2026 EDABK Laboratory.','',
        'Open **[AutoMX_CIM_Code_a_Chip.ipynb](AutoMX_CIM_Code_a_Chip.ipynb)** with the **env_mamba** Python kernel. This is the complete source-visible laboratory, from MXFP4/ternary encoding and MOS branches through CIM, acquisition, SAR, calibration and an actual two-head MHA IP. The final application is six-class wearable activity recognition.','',
        f"The audited fresh execution contains **{release['total_cells']} cells / {release['code_cells']} code cells**. Every code cell executed with output and no notebook errors, in **{release['full_run_elapsed_s']/60:.2f} minutes**. All original 409 cells and the 481-cell intermediate laboratory are retained. Three independent artifact auditors pass. Main and executed notebooks are identical.",'',
        f"Actual execution root: `{root}`. Receipt: `experiments/closure_20261028/release_validation.json`. A published mirror records its execution root in `CURRENT_RELEASE.json`.",'',
        '## Measured results','',
        '| Evidence | Result |','|---|---|',
        f"| Application | {application['test_windows']:,} test windows, nine unseen subjects; accuracy {metrics['accuracy']*100:.3f}%, macro-F1 {metrics['macro_f1']*100:.3f}%; float macro-F1 {float_metrics['macro_f1']*100:.3f}%. |",
        '| Real RTL | Four application paths, 2,947 frames and 23,576 values each; zero mismatches. Exhaustive decoder: 98,304 cases. |',
        f"| Transistor/SAR/MHA partition | Six fixed class-selected frames; {native['logical_conversions']} conversions; {native['partial_decode_mismatches']} partial/output mismatches. Stimulus: {native['contract']['stimulus']}. |",
        f"| Calibration switching | {power['gating_child_energy_reduction_percent']:.6f}% additional reduction in matched child-digital energy, with actual clock-edge and ICG-enable timing checks. |",
        '| Calibration/operation | 312 nominal anchors; 88 held-out patterns plus eight anchor checks; seven transistor PVT conditions; four settling policies; boot, programming, retained idle/wake and sensor-duty accounting. |',
        '| Physical evidence | Newly routed five-block top; router DRC, rails, signal macro-boundary LVS, hierarchical TT timing and fixed-palette KLayout overview/detail with repeated-image pixel comparison. |','',
        '## Matched active cost','',
        '| Variant | µs/frame | Child-digital nJ/frame |','|---|---:|---:|']
    for row in power['results']:
        text.append(f"| {row['variant']} | {row['activity_window_s']/row['frames']*1e6:.6f} | {row['child_digital_energy_per_frame_j']*1e9:.6f} |")
    text+=['','Same six frames, 25 MHz, declared ADC response/settling profile, SKY130 TT 1.8 V / 25 °C and clock-aware OpenSTA 3.1 VCD/Liberty/SPEF estimates. Cell area, macro footprint and START–EOC analog energy have their own tables. The serial ternary sign/add baseline remains in the comparison.','',
        '## Restart Kernel & Run All','',
        'Keep the entire prepared directory together when moving it. Design sources, declared hard-IP views, PDK and tool inputs are supplied; a development checkout is unnecessary. The launchers select `/home/nam/anaconda3/envs/env_mamba/bin/python` on this server. Set `AUTOMX_PYTHON` to a compatible interpreter on another host.','',
        '```bash','./run_notebook.sh','# Select env_mamba, then Restart Kernel & Run All.','# Or execute all cells headlessly:','./run_all.sh','```','',
        'Every full run creates a new empty `runs/fresh_*` tree and acquires new circuit responses, predictions, routed parent views and activity. Source-matched hard-macro geometry/netlist/RC is reusable IP. Requirements are in `environment.yml` and `requirements.txt`; native dependencies include Linux, Docker, Icarus, Magic/Netgen, KLayout and the pinned OpenLane toolchain.','',
        'For a smaller declared review check:','',
        '```bash','conda run -n env_mamba python scripts/quick_review.py --root . --work /tmp/automx_quick_review','```','',
        'The notebook reports the exact coverage/runtime of the short check and of an independently extracted source-IP check. They complement the full laboratory acquisition.','',
        '## Results and reusable IP','',
        '- [Priority outcomes](docs/PRIORITY_CLOSURE_RESULTS_20261029.md), [operating contract](docs/CIM_SAR_MHA_OPERATING_CONTRACT.md), [measurement tools](docs/MEASUREMENT_TOOLCHAIN.md).',
        '- `exports/AutoMX_CIM_five_block_top.gds` and matching overview/detail PNGs: selected five-block top.',
        '- `ip/automx_mha/` and the source-IP archive in `exports/`: synthesizable digital/mixed targets, protocols, numerical contracts and actual extraction tests.',
        '- `runs/fresh_*/electrical_closure/`: current measured pulse, calibration/PVT, timing, cost, service, figures and full native transcripts.','']
    routed=release['native_stimulus']=='routed measured PWM'
    evaluation=release.get('evaluated_candidate')
    if evaluation:
        text+=[f"The separately evaluated pulse/range repair measured all 64 delivered-pulse cases and {evaluation['native_conversions']} signed native conversions, with {evaluation['native_unresolved']} unresolved. Its adoption decision is **{evaluation['status']}**; the notebook preserves its actual witness tables and separately named candidate GDS. "+('The selected routed-input transistor/SAR/MHA partition passes its separate six-frame acceptance gate.' if routed else 'The qualified ideal-stimulus partition remains explicit.'),'']
    if evaluation and evaluation.get('calibration'):
        wrong=sum(row.get('decoded')!=row['expected'] for row in evaluation['matched_sum'] if row['bank_has_valid_ordered_calibration'])
        text+=[f"The adjacent physical repair has {len(evaluation['failed_pulse_checks'])} failed pulse checks. Its {evaluation['additional_calibration_conversions']} newly acquired calibration conversions and {evaluation['additional_matched_sum_conversions']} same-sum checks expose {wrong} wrong decodes. The per-bank table explains the retained rejection despite successful pulse delivery.",'']
    text+=['The compute leaf is a register-programmed eight-NMOS product-discharge circuit; controller registers hold weights. Circuit experiments use the declared transistor/SAR partition and tagged RTL replay. Individual physical checks retain their stated scopes.','',
        'UCI HAR and upstream SAR/PDK/tool credits, citations and licenses are retained in the notebook references, `NOTICE.md`, `licenses/` and the IP documentation.','']
    (root/'README.md').write_text('\n'.join(text))
    print('DELIVERY_README_WRITTEN',root/'README.md',flush=True)
