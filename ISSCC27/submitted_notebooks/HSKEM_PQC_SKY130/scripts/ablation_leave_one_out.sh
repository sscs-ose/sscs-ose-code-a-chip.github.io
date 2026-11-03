#!/usr/bin/env bash
# Leave-one-out ablation of the decapsulation steps A to H (Section 8): the final design H (single-port SRAM,
# one-round Keccak, 6,856 cycles) built with the defines of ONE step removed, in the full-system testbench.
# Steps A, C and D are one define each, B is the one-round Keccak (the row-serialized core is the ASIC choice),
# E to H are groups of 8, 4, 5 and 9 defines (scripts/run_streamed_system.sh). A second family, def_<DEFINE>,
# removes one single define of E to H. Results: results/ablation/<case>.log (build output and testbench log)
# and results/ablation/summary.json. Nothing outside results/ablation is written.
# usage: ablation_leave_one_out.sh [-j N] case...      cases: full step_A..step_H def_<NAME> steps all
#        ablation_leave_one_out.sh summary             (only rewrite summary.json from the logs)
# SPDX-License-Identifier: Apache-2.0
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
export PATH=/root/colabtest/oss-cad-suite/bin:$PATH
A="PACKED_NTT"; C="HASH_OVERLAP"; D="STREAM_IO"
E="FAST_BASEMUL FAST_FEED STREAM_OUT FOLD_READBACK PREFETCH TIGHT_LOOPS FAST_CHECK FAST_Y"
F="PACKED2 FAST_PRF FUSED_CMP FAST_READ"
G="PIPE_CHECK PAIR_PORT DEFER_J PIPE_MAC FAST_HASH"
H="DEC_STREAM SEG_CHECK BG_PRF STREAM_INV STREAM_FWD PRF_TO_NTT STREAM_DEC_INV PRF_FINE_HOLD POLY_GUARD"
ALL="$A $C $D $E $F $G $H"
OUT=results/ablation; WORK=$OUT/work; mkdir -p "$WORK"
JOBS=4; [ "${1:-}" = "-j" ] && { JOBS=$2; shift 2; }

# a patched copy of run_system_sim.sh that writes into the ablation directory (the original stays untouched)
SIM="$WORK/run_system_sim_ablation.sh"
sed -e "s#^ROOT=.*#ROOT=\"$ROOT\"#" \
    -e 's#"\$ROOT/results/system_sim/packed_system.diff"#"$SYS_TMP/packed_system.diff"#' \
    -e "s#results/system_sim#$OUT/work#g" scripts/run_system_sim.sh > "$SIM"

build() {  # case name -> run
  local c=$1 cfg=sram_only drop="" defs="" d
  case $c in
    full) ;;
    step_A) drop=$A;; step_B) cfg=asic;; step_C) drop=$C;; step_D) drop=$D;;
    step_E) drop=$E;; step_F) drop=$F;; step_G) drop=$G;; step_H) drop=$H;;
    def_*) drop=${c#def_};;
    *) echo "unknown case $c"; return 2;;
  esac
  for d in $ALL; do case " $drop " in *" $d "*) ;; *) defs="$defs -DTRUSTEDGE_$d";; esac; done
  local chk=1  # the contract checker probes the pair port of packed2, so it is off when A or PACKED2 is dropped
  case " $drop " in *" PACKED_NTT "*|*" PACKED2 "*) chk=0;; esac
  echo "case=$c config=$cfg defines=$defs" > "$OUT/$c.log"
  CAC_PACKED_SYSTEM=1 CAC_EXTRA_DEFS="$defs" CAC_SIM_TAG="_$c" CAC_PACKED_CHECK=$chk \
    bash "$SIM" $cfg >> "$OUT/$c.log" 2>&1
  { echo "===== testbench log ====="; cat "$WORK/tb_trustedge_spi_${cfg}_$c.log" 2>/dev/null; } >> "$OUT/$c.log"
  rm -f "$WORK/tb_trustedge_spi_${cfg}_$c.log" "$WORK/tb_${cfg}_$c.vvp"
}

summary() {
python3 - "$OUT" <<'PY'
import json, re, sys
from pathlib import Path
out = Path(sys.argv[1]); res = {}
for f in sorted(out.glob("*.log")):
    t = f.read_text(errors="replace")
    head = t.splitlines()[0]
    m = re.search(r"U1 Decaps busy latency valid/implicit-rejection=(\d+) cycles", t)
    ok = re.search(r"TB_TRUSTEDGE_SPI_RESULT: ALL PASS", t) is not None
    g = re.search(r"(?:PASS|FAIL) t1g: decaps .*?cycles=(\d+)", t)     # a failing build own count, informational
    fails = len(re.findall(r"\bFAIL\b", t))
    if "===== testbench log =====" not in t: status = "incomplete"
    elif "TB_TRUSTEDGE_SPI_RESULT" not in t: status = "build_or_run_error"
    else: status = "pass" if ok and m and not fails else "testbench_fail"
    res[f.stem] = {"config": re.search(r"config=(\S+)", head)[1],
                   "defines": re.findall(r"-DTRUSTEDGE_(\w+)", head),
                   "status": status, "tb_all_pass": ok, "fail_lines": fails,
                   "decaps_cycles": int(m[1]) if m else None,
                   "decaps_cycles_unverified": int(g[1]) if g and not m else None}
(out / "summary.json").write_text(json.dumps(res, indent=1) + "\n")
for k, v in res.items(): print(f"{k:24s} {v['status']:18s} {v['decaps_cycles']} {v['decaps_cycles_unverified'] or ''}")
PY
}

cases=()
for a in "$@"; do
  case $a in
    summary) ;;
    steps) cases+=(step_A step_B step_C step_D step_E step_F step_G step_H);;
    all) cases+=(full step_A step_B step_C step_D step_E step_F step_G step_H); for d in $E $F $G $H; do cases+=(def_$d); done;;
    *) cases+=("$a");;
  esac
done
export -f build summary; export ROOT OUT WORK SIM A C D E F G H ALL
[ ${#cases[@]} -gt 0 ] && printf '%s\n' "${cases[@]}" | xargs -P "$JOBS" -I{} bash -c 'build {}'
summary
