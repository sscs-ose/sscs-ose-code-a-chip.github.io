#!/usr/bin/env bash
# Run notebook 07 end-to-end and assert the headline metrics are in range.
# Exits non-zero if any claim regresses.
set -euo pipefail

cd "$(dirname "$0")/.."
NB="notebooks/07_SPICE_Validation.ipynb"
EXPORT="data/exports/spice_validation.json"
MC_EXPORT="data/exports/metastability_mc.json"

echo "[validate_spice] executing $NB ..."
jupyter nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=1800 "$NB"

python - <<'PY'
import json, sys
m = json.load(open('data/exports/spice_validation.json'))['metrics']
mc = json.load(open('data/exports/metastability_mc.json'))
print('R2_vdac           =', m['R2_vdac'])
print('R2_vcomp_diff     =', m['R2_vcomp_diff'])
print('code_match_rate   =', m['code_match_rate'])
print('tail_p99_rel_err  =', mc['tail_p99_rel_err'])
fail = False
if m['R2_vdac'] < 0.95: print('FAIL: R2_vdac < 0.95'); fail = True
if m['R2_vcomp_diff'] < 0.90: print('FAIL: R2_vcomp_diff < 0.90'); fail = True
if m['code_match_rate'] < 0.95: print('FAIL: code match < 0.95'); fail = True
if mc['tail_p99_rel_err'] > 0.30: print('FAIL: tail P99 rel err > 0.30'); fail = True
sys.exit(1 if fail else 0)
PY

echo "[validate_spice] all claims in range."
