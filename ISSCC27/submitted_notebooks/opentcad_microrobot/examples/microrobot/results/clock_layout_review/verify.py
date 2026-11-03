"""Check evidence integrity and numerical observations, not design acceptance."""
import hashlib
import json
from pathlib import Path

import numpy as np

DEST = Path(__file__).resolve().parent
report = json.loads((DEST/'review_metrics.json').read_text())
assert report['status'].startswith('PRELIMINARY')
assert 'NOT ACCEPTED' in report['status']
for name, record in report['cases'].items():
    assert record['full_completion'] and record['all_finite']
    assert record['columns'] == 8 and record['first_time_s'] == 0
    assert record['actual_stop_s'] == .004 and record['nondecreasing_time']
    assert not record['log_abort_markers']
    power = record['power_W']
    assert np.isclose(power['whole_clock_and_first_ff'], power['analog_clock'] +
                      power['first_ff_and_feedback'], rtol=1e-12, atol=1e-20)
    assert np.isclose(record['edges']['sustained_q_to_clock_frequency_ratio'], .5, atol=1e-5)
    assert set(record['edges']['clock_edges_between_successive_q_rises']) == {2}
    if name.startswith('extracted'):
        assert record['bench_metrics']['passed'] is False
        assert record['bench_metrics']['first_divider_output_Hz'] is None
        assert record['edges']['steady_q_rise_count'] == 2
    for file in ['clock.spice','receiver_cells.spice','ngspice.log']:
        assert hashlib.sha256((DEST/name/file).read_bytes()).hexdigest() == record['sha256'][file]
for comparison in report['timestep_comparison'].values():
    assert comparison['primary_frequency_and_whole_power_below_1_percent']
    assert comparison['decks_identical_except_comments_and_tran']
    assert comparison['tran_stop_and_start_identical']
    added_removed = [s for s in comparison['deck_diff'] if s.startswith(('+','-')) and not s.startswith(('+++','---'))]
    assert added_removed == ['-tran 5e-08 0.004 0 5e-08', '+tran 2.5e-08 0.004 0 2.5e-08']
canonical = DEST/'provenance/starved_clock.spice'
assert hashlib.sha256(canonical.read_bytes()).hexdigest() == 'dc606bcaa35616e6412c2b8d8c63e17175f6b53d6baad820a222b66b74dc29de'
assert report['capacitance']['resistor_count'] == 851
assert report['capacitance']['capacitor_count'] == 374
assert (DEST/'prototype_layout.png').is_file()
assert not [p for p in DEST.rglob('*') if p.suffix.lower() in {'.dat','.pdf'}]
manifest = json.loads((DEST/'sha256.json').read_text())
for name, digest in manifest.items():
    assert hashlib.sha256((DEST/name).read_bytes()).hexdigest() == digest, name
result = {'status':'Evidence checks passed; electrical acceptance remains pending',
          'cases':4,'full_transient_completion_checks':4,
          'matched_timestep_primary_criteria_below_1_percent':2,
          'exact_deck_step_only_diffs':2, 'export_hashes_verified':True,
          'no_raw_dat_or_pdf_export':True}
(DEST/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
