ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
V=python/vectors
run() { RUN=flow/scale/$1/runs/layoutcg NCASES=${NCASES:-50} bash flow/gl_npz.sh scale/$1 $2 $3 $V/$4 real 2>&1 | grep -E "compared|Total|rror"; }
for a in "$@"; do
  case $a in
   w4) run dcim_core_n128 dcim_core dense r128_w4a4_real_layer.npz;;
   w6) run dcim_w6a4_n128 dcim_core w6a4 r128_w6a4_real_layer.npz;;
   w8) run dcim_w8a4_n128 dcim_core w8a4 r128_w8a4_real_layer.npz;;
   k2) run sidecarcim_top_n128 sidecarcim_top top r128_sidecar_k2_real_layer.npz;;
   k4) run sidecarcim_topkk4_n128 sidecarcim_top top r128_sidecar_k4_real_layer.npz;;
  esac
done
python3 flow/extract_ppa128.py | cut -c1-150
