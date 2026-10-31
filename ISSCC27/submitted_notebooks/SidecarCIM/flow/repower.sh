#!/bin/bash
# re-run OpenSTA power (6 digits) on the saved busy-window VCDs; no re-simulation
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
rd() { python3 -c "import csv;print([x['run_dir'] for x in csv.DictReader(open('results/ppa.csv')) if x['design']=='$1'][0])"; }
pw() { # design tag vcd
  r=$(rd $1)
  POW_TAG=$2 bash flow/power.sh $1 $r flow/vcd_compute/$3 tb/dut >/dev/null
}
for d in dcim_core_ff sidecarcim_top_ff dcim_8bit_ff dcim_w8a4_ff dcim_w6a4_ff; do
  pw $d real ${d}_real.busy.vcd
  pw $d random ${d}_random.busy.vcd
done
pw sidecarcim_top_ff_par real sidecarcim_top_ff_par_real.busy.vcd
r=$(rd mac_baseline); bash flow/power.sh mac_baseline $r flow/vcd_compute/mac_baseline.gl.busy.vcd tb/dut > /dev/null
grep "^Total" $(rd dcim_w6a4_ff)/power_real.rpt
python3 flow/extract_ppa.py > /dev/null
.venv/bin/python flow/extract_activity.py > /dev/null
