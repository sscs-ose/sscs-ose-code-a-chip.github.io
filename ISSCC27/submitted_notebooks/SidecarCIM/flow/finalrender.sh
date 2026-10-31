#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
for d in dcim_core_ff dcim_8bit_ff sidecarcim_top_ff sidecarcim_top_ff_par mac_baseline; do
  bash flow/renderfull.sh $d results/gds/${d}_full.png
  top=$(python3 -c "import json;print(json.load(open('flow/$d/config.json'))['DESIGN_NAME'])")
  bash flow/render.sh ${d}_z $d $top   # old script: zoom only kept below
  mv results/gds/${d}_z_zoom.png results/gds/${d}_zoom.png
  rm -f results/gds/${d}_z_full.png results/gds/${d}_z_nofill.png results/gds/${d}_nofill.png
done
bash flow/modrender.sh sidecarcim_top_ff sidecarcim_top results/gds/sidecarcim_top_ff_modules.png
rm -f results/gds/sidecarcim_top_ff_regions.png
rm -rf results/gds_test
