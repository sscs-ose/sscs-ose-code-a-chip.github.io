#!/bin/bash
# Author: Vrinda Pandey (layout generator and sign-off scripts for this submission)
# SPDX-License-Identifier: Apache-2.0
# prove_signoff.sh - evidence that THIS GDS is DRC/LVS clean against THIS netlist with THESE sizes.
# Run inside the gLayout environment (the python must import glayout), from the 12T folder (or set GL12). verify12t.py must sit next to this script, in that folder, or on PYTHONPATH.
# Writes PROOF_<date>.txt and keeps every tool log in verify_proof/. Nothing in layout/ is changed.
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${GL12:-$HOME/glayout/vga12t}" || { echo "cannot cd to ${GL12:-$HOME/glayout/vga12t}"; exit 1; }
export PYTHONPATH="$HERE:$(pwd):$(pwd)/generator:${PYTHONPATH}"
NET=layout/vga_core_12t.spice; JSN=layout/vga_core_12t_sizes.json; GDS=layout/vga_core_12t.gds; V=verify_proof
OUT=PROOF_$(date +%Y%m%d_%H%M).txt
TMP=$(mktemp -d)
{
echo "SIGN-OFF PROOF  $(date '+%Y-%m-%d %H:%M')  host $(hostname)"
echo "tools: $(klayout -v 2>/dev/null | head -1) | magic $(magic --version 2>/dev/null | head -1) | $(netgen -batch quit 2>&1 | grep -o 'Netgen [0-9.]*' | head -1) | PDK_ROOT=${PDK_ROOT:-unset}"

echo; echo "== 0. Pre-flight =="
pre=0
for f in "$NET" "$JSN" "$GDS"; do [ -s "$f" ] || { echo "MISSING: $f (run from the folder whose layout/ holds the three files, or set GL12)"; pre=1; }; done
for t in python magic netgen; do command -v $t >/dev/null || { echo "MISSING on PATH: $t"; pre=1; }; done
python -c "import verify12t, sys; print('verify12t:', verify12t.__file__)" 2>&1 || { echo "MISSING: verify12t.py is not importable (put it next to this script)"; pre=1; }
if python -c "import glayout" 2>/dev/null; then echo "glayout: importable ($(python -c 'import glayout,os;print(os.path.dirname(glayout.__file__))'))"
elif [ "${SKIP_GLAYOUT:-0}" = "1" ]; then echo "glayout: NOT importable, SKIP_GLAYOUT=1 -> the gLayout KLayout deck will be missing from this proof"
else echo "MISSING: this python cannot import glayout, so the third DRC deck would not run."
     echo "         Activate the environment you generate layouts in (e.g. source ~/glayout/.venv/bin/activate) and run again."; pre=1; fi
[ $pre = 0 ] || { echo "ABORTED in pre-flight: nothing below was run"; exit 1; }

echo; echo "== 1. Fingerprints (sha256) - compare these with the files you received =="
sha256sum "$NET" "$JSN" "$GDS"
sha256sum "$(python -c 'import verify12t; print(verify12t.__file__)')"

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
rm -rf "$V"; mkdir -p "$V"
if [ "${SKIP_DRC:-0}" != "1" ]; then
  python -c "import verify12t as v; v.drc('$GDS', outdir='$V')" > "$V/run_drc.log" 2>&1
  rc=$?; grep -E "^DRC: (PASS|FAIL)" "$V/run_drc.log"
  if [ -f "$V/drc_report.txt" ]; then grep -E "^\[|violations|RESULT" "$V/drc_report.txt"
  else echo "DRC DID NOT RUN (exit $rc). Last lines of $V/run_drc.log:"; tail -n 25 "$V/run_drc.log" | sed 's/^/    /'; fi
fi
python -c "import verify12t as v; v.lvs('$GDS', '$NET', outdir='$V')" > "$V/run_lvs.log" 2>&1
rc=$?; grep -E "^LVS: (PASS|FAIL)" "$V/run_lvs.log"
L="$V/vga_core_12t_lvs_extracted.spice"; S="$V/lvs_setup.tcl"
if [ ! -s "$V/lvs_report.txt" ] || [ ! -s "$L" ] || [ ! -s "$S" ]; then
  echo "LVS DID NOT RUN (exit $rc). Last lines of $V/run_lvs.log:"; tail -n 25 "$V/run_lvs.log" | sed 's/^/    /'
  [ -s "$V/lvs_report.txt" ] && { echo "    lvs_report.txt says:"; head -n 5 "$V/lvs_report.txt" | sed 's/^/    /'; }
  echo; echo "ABORTED: no LVS, so the controls below cannot run. Send this file and the $V/ folder."
  exit 1
fi
sed -n '/^Subcircuit summary/,/^Final result/p' "$V/lvs_report.txt" | grep -v -E "^-+$"
grep -q "Final result: Circuits match uniquely" "$V/lvs_report.txt" || echo "LVS DID NOT MATCH UNIQUELY"
grep -q "Property errors were found" "$V/lvs_report.txt" && echo "PROPERTY ERRORS FOUND" || echo "No property (W/L/nf/m) errors"

echo; echo "== 4. Controls: the unchanged netlist must PASS; each netlist with ONE change must FAIL =="
lvs_one() {  # $1 netlist to compare -> report in $TMP/r.out, netgen's own output in $TMP/r.log
  rm -f "$TMP/r.out" "$TMP/r.log"                  # never read the previous control's verdict
  netgen -batch lvs "$L vga_core_12t" "$1 vga_core_12t" "$S" "$TMP/r.out" > "$TMP/r.log" 2>&1
  [ -s "$TMP/r.out" ]
}
matched() { grep -q "Final result: Circuits match uniquely" "$TMP/r.out" && ! grep -q "Property errors were found" "$TMP/r.out"; }
cp "$NET" "$TMP/pos.spice"
if ! lvs_one "$TMP/pos.spice"; then
  printf "  %-40s -> %s\n" "unchanged netlist (positive control)" "ERROR: netgen wrote no report. Its output:"
  tail -n 15 "$TMP/r.log" | sed 's/^/    /'; echo "ABORTED: the controls cannot be trusted"; exit 1
elif matched; then printf "  %-40s -> %s\n" "unchanged netlist (positive control)" "PASS (correctly accepted)"
else printf "  %-40s -> %s\n" "unchanged netlist (positive control)" "FAIL  <-- PROBLEM: the unchanged netlist is rejected"
  grep -E "^Final result|Property errors" "$TMP/r.out" | sed 's/^/    /'; echo "ABORTED: the controls cannot be trusted"; exit 1
fi
neg() {  # $1 description, $2 sed expression
  sed "$2" "$NET" > "$TMP/neg.spice"
  cmp -s "$TMP/neg.spice" "$NET" && { printf "  %-40s -> %s\n" "$1" "ERROR: the edit changed nothing"; return; }
  lvs_one "$TMP/neg.spice" || { printf "  %-40s -> %s\n" "$1" "ERROR: netgen wrote no report"; tail -n 5 "$TMP/r.log" | sed 's/^/    /'; return; }
  if matched; then r="PASS  <-- PROBLEM: change not detected"; else r="FAIL (correctly rejected)"; fi
  printf "  %-40s -> %s\n" "$1" "$r"
}
neg "M5 copies m 14 -> 13"            '/^XM5 /s/ m=14/ m=13/'
neg "M10 copies m 2 -> 3"             '/^XM10 /s/ m=2/ m=3/'
neg "M1 length L 0.5 -> 1"            '/^XM1 /s/ L=0.5 / L=1 /'
neg "M2 width W 640 -> 600"           '/^XM2 /s/ W=640 / W=600 /'
neg "M6 fingers nf 4 -> 8 (W 20->40)" '/^XM6 /s/ W=20 nf=4 / W=40 nf=8 /'
neg "M11 drain v_out -> net4 (wiring)" '/^XM11 /s/^XM11 v_out /XM11 net4 /'
} 2>&1 | tee "$OUT"
rm -rf "$TMP"
echo; echo "Saved: $(pwd)/$OUT"
