#!/bin/bash
# gate-level power for sidecarcim_top_ff_pipe (PIPE_MERGE=1): valid/y one edge later.
# real / random = busy window + 1 trailing cycle (includes the y-register update, 5 cycles per dot);
# real4 = busy window only (4 cycles), for comparison with the other designs.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
d=sidecarcim_top_ff_pipe
PIPE=1 WINDOW_EXTRA_PS=30000 bash flow/gl_npz.sh $d sidecarcim_top top python/vectors/sidecar_real_layer.npz real 2>&1 | grep -E "compared|Total|window"
PIPE=1 WINDOW_EXTRA_PS=30000 bash flow/gl_npz.sh $d sidecarcim_top top python/vectors/sidecar_random.npz random 2>&1 | grep -E "compared|Total|window"
PIPE=1 WINDOW_EXTRA_PS=0 bash flow/gl_npz.sh $d sidecarcim_top top python/vectors/sidecar_real_layer.npz real4 2>&1 | grep -E "compared|Total|window"
python3 flow/extract_ppa.py > /dev/null
.venv/bin/python flow/extract_activity.py > /dev/null
bash flow/cgcheck.sh $d 2>&1 | python3 flow/cgcsv.py $d
grep sidecarcim_top_ff_pipe results/ppa.csv | cut -d, -f1-13,15
grep sidecarcim_top_ff_pipe results/energy_activity.csv | cut -d, -f1-5
