#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
python3 flow/scaling.py gen
python3 flow/scaling.py gen   >/dev/null
L="dcim_core_n32 dcim_core_n64 dcim_core_n128 dcim_core_n256 sidecarcim_top_n32 sidecarcim_top_n64 sidecarcim_top_n128 sidecarcim_top_n256 dcim_8bit_n32 dcim_8bit_n64 dcim_8bit_n128 dcim_8bit_n256 sidecarcim_topk_n64 sidecarcim_topk_n128 sidecarcim_topk_n256 sidecarcim_topkk4_n128 sidecarcim_topkk4_n256 sidecarcim_topkk8_n256"
for d in $L; do python3 flow/scaling.py run synthcg $d; done
python3 flow/scaling.py run layoutcg dcim_core_n128 sidecarcim_top_n128
python3 flow/scaling.py csv
echo done > flow/logs/scalecg.done
