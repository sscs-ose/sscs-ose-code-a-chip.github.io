#!/bin/bash
# gate-level power for the dense variants dcim_w8a4_ff / dcim_w6a4_ff (run after their flow), real + random stimulus.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
for v in w8a4 w6a4; do
  d=dcim_${v}_ff
  [ -d flow/$d/runs ] || continue
  bash flow/gl_npz.sh $d dcim_core $v python/vectors/${v}_real_layer.npz real 2>&1 | grep -E "compared|Total"
  [ -f python/vectors/${v}_random.npz ] && bash flow/gl_npz.sh $d dcim_core $v python/vectors/${v}_random.npz random 2>&1 | grep -E "compared|Total"
done
