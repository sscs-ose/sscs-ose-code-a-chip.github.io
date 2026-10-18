#!/usr/bin/env bash
# STA of a T3 global-route result at the three sign-off corners (global-route parasitics).
# usage: t3_grt_sta.sh <results dir containing 5_1_grt.odb> <out dir>
set -uo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"; OR=/opt/eda/orfs-6101364b/tools/install/OpenROAD/bin/openroad
RUN="${1:?results dir}"; OUT="${2:?out dir}"; mkdir -p "$OUT"
export MIN_ROUTING_LAYER=met1 MIN_CLK_ROUTING_LAYER=met3 MAX_ROUTING_LAYER=met5
for c in ss_100C_1v60 tt_025C_1v80 ff_n40C_1v95; do
  RUN="$RUN" CORNER=$c "$OR" -no_splash -exit "$HERE/flow_chip/grt_sta.tcl" > "$OUT/grt_sta_$c.log" 2>&1
  echo "$c $(grep RESULT "$OUT/grt_sta_$c.log" | tr '\n' ' ')"
done
python3 - "$OUT" <<'PY'
import re, sys, glob, collections
for f in sorted(glob.glob(sys.argv[1] + "/grt_sta_*.log")):
    rows = []
    for l in open(f):
        m = re.match(r'(\S+) \(\S+\)\s+(\S+) \(\S+\)\s+(-?[\d.]+)\s*$', l.strip())
        if m: rows.append((m[1], m[2], float(m[3])))
    neg = [r for r in rows if r[2] < 0]
    blk = lambda n: (lambda p: p[0] if p[0].startswith(('u_', 'g_')) else 'top-level regs')(n.replace('u_common.', '').split('.'))
    c = collections.defaultdict(list)
    for s, e, sl in neg: c[blk(e)].append(sl)
    print(f.split('grt_sta_')[1][:-4], len(neg), 'violating endpoints listed')
    for k, v in sorted(c.items(), key=lambda kv: min(kv[1])): print(f'   {k:34s} n={len(v):4d} worst={min(v):7.2f} median={sorted(v)[len(v)//2]:7.2f}')
PY
