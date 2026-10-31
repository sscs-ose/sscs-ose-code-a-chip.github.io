ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT"
L=flow/loadpow.sh; V=python/vectors
bash $L sidecarcim_top_ff_pipe_s3 sidecarcim_top top $V/sidecar_s3_real_layer.npz w_load_en SBITS=3 PIPE=1
bash $L dcim_w6a4_ff dcim_core w6a4 $V/w6a4_real_layer.npz load_en X=1
bash $L dcim_w8a4_ff dcim_core w8a4 $V/w8a4_real_layer.npz load_en X=1
# W4A4+mig+wclip weights (until Oct 17 this read the naive real_layer.npz; that run is power_load_nomig.rpt)
bash $L dcim_core_ff dcim_core dense $V/w4a4_real_layer.npz load_en X=1
bash $L sidecarcim_top_ff sidecarcim_top top $V/sidecar_real_layer.npz w_load_en X=1
