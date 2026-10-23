#!/usr/bin/env bash
# The RTL regressions of Sections 4 and 7 on a much larger set of golden-model vectors: every NTT engine
# (original with both stores, the three iterations and their variants, the stream mode) and both Keccak cores.
# The vectors are generated into a work directory, not into vectors/. Result: results/sim_large/summary.json.
#   usage: scripts/run_sim_large.sh [n_ntt] [n_keccak] [seed]       (default 10000 NTT polynomials, 2000 states)
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
[ -z "${CAC_NO_LOCAL_IV:-}" ] && [ -d "$HOME/eda/iverilog12/bin" ] && export PATH="$HOME/eda/iverilog12/bin:$PATH"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; R="$ROOT/rtl"; TB="$ROOT/tb"
NN="${1:-10000}"; NK="${2:-2000}"; SEED="${3:-4242}"
W="${CAC_LARGE_WORK:-/tmp/cac_sim_large}"; OUT="$ROOT/results/sim_large"; mkdir -p "$W" "$OUT"
(cd "$ROOT/golden" && python3 gen_vectors.py --out "$W/vec" --ntt "$NN" --keccak "$NK" --seed "$SEED" --more-corners)
cd "$W/vec"
run() { local name=$1; shift
  iverilog -g2012 -I . -o "$W/$name.vvp" "$@" && vvp -n "$W/$name.vvp" > "$OUT/$name.log"; rm -f "$W/$name.vvp"
  echo "$name: $(grep -E 'RESULT' "$OUT/$name.log" | tail -1)"; }
run ntt_dualport   "$R/kyber_pkg.sv" "$R/barrett_reduce.v" "$R/kyber_ntt_engine.sv" "$TB/tb_ntt.sv"
run ntt_singleport -DTRUSTEDGE_ASIC_SRAM "$R/kyber_pkg.sv" "$R/barrett_reduce.v" "$R/te_sram_models.sv" "$R/kyber_ntt_engine.sv" "$TB/tb_ntt.sv"
while read -r name b1 pipe cw; do
  run "$name" -DNTT_OPT -DB1C=$b1 -DPIPE=$pipe -DCW=$cw "$R/kyber_pkg.sv" "$R/barrett_reduce.v" "$R/barrett_reduce_1c.v" \
      "$R/te_sram_models.sv" "$R/kyber_ntt_engine_opt.sv" "$TB/tb_ntt.sv"
done <<'LIST'
opt_b1_w12   1 0 12
opt_pipe_w12 1 1 12
LIST
for x in 0 1; do
  run packed_x$x -DNTT_PACKED -DXSTAGE=$x "$R/kyber_pkg.sv" "$R/barrett_reduce_1c.v" "$R/kyber_ntt_engine_packed.sv" "$TB/tb_ntt.sv"
  run packed2_x$x -DNTT_PACKED2 -DXSTAGE=$x "$R/kyber_pkg.sv" "$R/barrett_reduce_1c.v" "$R/kyber_ntt_engine_packed.sv" \
      "$R/kyber_ntt_engine_packed2.sv" "$TB/tb_ntt.sv"
  run packed2_stream_x$x -DXSTAGE=$x "$R/kyber_pkg.sv" "$R/barrett_reduce_1c.v" "$R/kyber_ntt_engine_packed.sv" \
      "$R/kyber_ntt_engine_packed2.sv" "$TB/tb_ntt_stream.sv"
done
run keccak_round  -DSERIAL=0 "$R/keccak_f1600_iter.sv" "$TB/tb_keccak.sv"
run keccak_serial -DSERIAL=1 "$R/keccak_f1600_iter.sv" "$TB/tb_keccak.sv"
python3 - "$OUT" "$NN" "$NK" "$SEED" <<'PY'
import json, pathlib, re, sys
out, nn, nk, seed = pathlib.Path(sys.argv[1]), *map(int, sys.argv[2:5])
res = {}
for f in sorted(out.glob("*.log")):
    t = f.read_text()
    m = re.search(r"(?:NTT|KECCAK|NTT_STREAM)_RESULT.*", t)
    d = {k: int(v) for k, v in re.findall(r"(\w+)=(\d+)", m[0])} if m else {}
    d["pass_lines"] = len(re.findall(r"^PASS$", t, re.M)); d["violations"] = t.count("NTT_STREAM_VIOLATION")
    res[f.stem] = d
json.dump({"ntt_random_polynomials": nn, "keccak_random_states": nk, "seed": seed, "runs": res}, open(out / "summary.json", "w"), indent=1)
bad = [k for k, v in res.items() if v.get("errors", 1) != 0 or v.get("timing_variations", 1) != 0 or v["violations"]]
print("runs:", len(res), "failing:", bad)
PY
