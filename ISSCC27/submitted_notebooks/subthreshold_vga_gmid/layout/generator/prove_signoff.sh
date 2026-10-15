#!/bin/bash
# Author: Vrinda Pandey (layout generator and sign-off scripts for this submission)
# SPDX-License-Identifier: Apache-2.0
# prove_signoff.sh - evidence that THIS GDS is DRC/LVS clean against THIS netlist with THESE sizes.
# Run from the 12T folder (or set GL12). Writes PROOF_<date>.txt. Nothing in layout/ is changed.
cd "${GL12:-$HOME/glayout/vga12t}" || exit 1
NET=layout/vga_core_12t.spice; JSN=layout/vga_core_12t_sizes.json; GDS=layout/vga_core_12t.gds; V=verify_proof
OUT=PROOF_$(date +%Y%m%d_%H%M).txt
{
echo "SIGN-OFF PROOF  $(date '+%Y-%m-%d %H:%M')  host $(hostname)"
echo; echo "== 1. Fingerprints (sha256) - compare these with the files you received =="
sha256sum "$NET" "$JSN" "$GDS"

echo; echo "== 2. Every device: netlist sizes vs JSON sizes =="
python - "$NET" "$JSN" <<'PY'
import json, re, sys
net, js = sys.argv[1], json.load(open(sys.argv[2])); fw = js["finger_width_um"]; bad = 0
print(f"{'dev':5s} {'netlist  W / L / nf / m':28s} {'JSON  W / L / nf / m':28s} ok")
for l in open(net):
    t = l.split()
    if not t or not t[0].upper().startswith("XM"): continue
    d = t[0][1:]; p = dict(kv.split("=", 1) for kv in t[6:] if "=" in kv)
    n = (float(p["W"]), float(p["L"]), int(p["nf"]), int(p.get("m", 1)))
    j = js["devices"][d]; jj = (j["nf"] * fw, j["L_um"], j["nf"], j["m"])
    ok = all(abs(a - b) < 1e-9 for a, b in zip(n, jj)); bad += not ok
    print(f"{d:5s} {'%g / %g / %d / %d' % n:28s} {'%g / %g / %d / %d' % jj:28s} {'OK' if ok else 'MISMATCH'}")
print("RESULT: netlist and JSON sizes", "IDENTICAL" if not bad else f"DIFFER on {bad} devices")
PY

echo; echo "== 3. Fresh DRC and LVS (previous results deleted; LVS reference = $NET) =="
rm -rf "$V"
python -c "
import verify12t as v
if '${SKIP_DRC:-0}' != '1': v.drc('$GDS', outdir='$V')
v.lvs('$GDS', '$NET', outdir='$V')" 2>&1 | grep -E "PASS|FAIL"
[ -f "$V/drc_report.txt" ] && grep -E "^\[|violations|RESULT" "$V/drc_report.txt"
sed -n '/^Subcircuit summary/,/^Final result/p' "$V/lvs_report.txt" | grep -v -E "^-+$"
grep -q "Property errors were found" "$V/lvs_report.txt" && echo "PROPERTY ERRORS FOUND" || echo "No property (W/L/nf/m) errors"

echo; echo "== 4. Negative controls: the same layout against a netlist with ONE change must FAIL =="
L="$V/vga_core_12t_lvs_extracted.spice"; S="$V/lvs_setup.tcl"
neg() {  # $1 description, $2 sed expression
  sed "$2" "$NET" > /tmp/neg.spice
  netgen -batch lvs "$L vga_core_12t" "/tmp/neg.spice vga_core_12t" "$S" /tmp/neg.out >/dev/null 2>&1
  if grep -q "Property errors were found" /tmp/neg.out || ! grep -q "Final result: Circuits match uniquely" /tmp/neg.out; then r="FAIL (correctly rejected)"; else r="PASS  <-- PROBLEM: change not detected"; fi
  printf "  %-40s -> %s\n" "$1" "$r"
}
neg "M5 copies m 14 -> 13"            '/^XM5 /s/ m=14/ m=13/'
neg "M10 copies m 2 -> 3"             '/^XM10 /s/ m=2/ m=3/'
neg "M1 length L 0.5 -> 1"            '/^XM1 /s/ L=0.5 / L=1 /'
neg "M2 width W 640 -> 600"           '/^XM2 /s/ W=640 / W=600 /'
neg "M6 fingers nf 4 -> 8 (W 20->40)" '/^XM6 /s/ W=20 nf=4 / W=40 nf=8 /'
neg "M11 drain v_out -> net4 (wiring)" '/^XM11 /s/^XM11 v_out /XM11 net4 /'
} 2>&1 | tee "$OUT"
echo; echo "Saved: $(pwd)/$OUT"
