#!/bin/bash
# The steps of env/Dockerfile with Apptainer / Singularity (for HPC clusters without Docker), then the notebook with papermill.
#   bash env/run_apptainer.sh <run folder> [quick|full] [load|quick|full]      (run from this package folder)
# Same steps as the Docker image: base image IIC-OSIC-TOOLS 2026.10 → venv + pip -r env/requirements.txt → volare PDK c6d73a35 → copy of this
# package → papermill. Everything is written under <run folder>: base.sif, home/ (PDK, package copy), venv/, out/ (executed notebook, work/).
# Compute nodes without direct internet: set http_proxy / https_proxy first (passed into the container below).
set -u
PKG=$(cd "$(dirname "$0")/.." && pwd)
R=$(mkdir -p "${1:?run folder}" && cd "$1" && pwd); MODE=${2:-quick}; TRAIN=${3:-load}
case "$R/" in "$PKG"/*) echo "use a run folder outside this package folder (e.g. ../cac_run)"; exit 1;; esac
CT=$(command -v apptainer || command -v singularity) || { echo "apptainer / singularity not found"; exit 1; }
mkdir -p "$R/home" "$R/venv" "$R/tmp" "$R/cache"
export APPTAINER_CACHEDIR=$R/cache SINGULARITY_CACHEDIR=$R/cache APPTAINER_TMPDIR=$R/tmp SINGULARITY_TMPDIR=$R/tmp
cat > "$R/env.list" <<'EOF'
TOOLS=/foss/tools
PATH=/opt/venv/bin:/foss/tools/bin:/foss/tools/klayout:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
LD_LIBRARY_PATH=/foss/tools/klayout:/foss/tools/ngspice/lib:/foss/tools/iverilog/lib:/foss/tools/openems/lib:/foss/tools/kactus2:/foss/tools/gtkwave/lib/x86_64-linux-gnu:/foss/tools/kepler-formal/lib:/foss/tools/libman/lib
HOME=/home/designer
QT_QPA_PLATFORM=offscreen
PYTHONDONTWRITEBYTECODE=1
EOF
for v in http_proxy https_proxy; do [ -n "${!v:-}" ] && { echo "$v=${!v}"; echo "${v^^}=${!v}"; }; done >> "$R/env.list"
S() { "$CT" exec --containall --cleanenv --env-file "$R/env.list" --home "$R/home:/home/designer" \
        -B "$R/venv:/opt/venv" -B "$R/tmp:/tmp" --pwd "$1" "$R/base.sif" bash -c "$2"; }
T() { date +%s; }
t0=$(T)
# FROM hpretl/iic-osic-tools:2026.10
[ -f "$R/base.sif" ] || "$CT" pull "$R/base.sif" docker://hpretl/iic-osic-tools:2026.10 || exit 1
# COPY . /home/designer/ep_cim_loop
mkdir -p "$R/home/ep_cim_loop" && cp -a "$PKG/." "$R/home/ep_cim_loop/"
# RUN venv + pip;  RUN volare enable
[ -x "$R/venv/bin/python3" ] || S /home/designer "python3 -m venv --system-site-packages /opt/venv" || exit 1
S /home/designer "/opt/venv/bin/pip install --no-cache-dir -q -r /home/designer/ep_cim_loop/env/requirements.txt" || exit 1
S /home/designer "/opt/venv/bin/volare enable --pdk sky130 --pdk-root /home/designer/pdk/volare c6d73a35f524070e85faff4a6a9eef49553ebc2b" || exit 1
echo "setup done in $(( $(T) - t0 )) s"
# notebook (same command as the README "without Jupyter" run)
mkdir -p "$R/home/out"
S /home/designer/ep_cim_loop "python3 -m papermill ep_cim_loop.ipynb /home/designer/out/ep_cim_loop_out.ipynb -k python3 --log-output --no-progress-bar \
  -p MODE $MODE -p TRAIN $TRAIN -p WORK /home/designer/out/work -p NJ $(nproc)"
rc=$?
echo "papermill rc $rc, total $(( $(T) - t0 )) s; outputs in $R/home/out"
grep -E "failed|Total" "$R/home/out/work/times.md" 2>/dev/null | tail -2
exit $rc
