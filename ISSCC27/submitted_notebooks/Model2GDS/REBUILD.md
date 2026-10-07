# Optional fresh tool runs

The notebook and `--verify-package` need no EDA installation. These additional
commands run real tools and may take minutes to hours. They write to a fresh
directory outside the package and never replace bundled evidence. No historical
Git objects or repository remote are needed. A new output is a reproduction
attempt, not automatically an accepted new research result.

## RTL simulation

Use Linux/WSL with Verilator and a C++17 compiler. The captured accepted version
is recorded in the functional JSON and `environment/toolchain.lock.json`.

```bash
python scripts/build_submission.py --rerun-rtl --array-size 2 --work-dir /tmp/model2gds_rtl_s2_001
python scripts/build_submission.py --rerun-rtl --array-size 4 --work-dir /tmp/model2gds_rtl_s4_001
python scripts/build_submission.py --rerun-rtl --array-size 8 --work-dir /tmp/model2gds_rtl_s8_001
```

The helper compiles the bundled thin wrapper, PE/fabric and C++ harness, uses the
preserved text vectors, saves exact argv/stdout/stderr/return codes and compares
all new matrices, tile cycles and directed tests with the accepted observations.
Existing work directories are refused. The notebook never calls this option.

## Tiny-counter RTL-to-GDS

Install Docker and the open SKY130 PDK separately using the upstream supported
OpenLane/Volare setup. Required open_pdks revision: `0fe599b2afb6708d281543108caf8310912f54af`; PDK `sky130A`,
library `sky130_fd_sc_hd`. Set `MODEL2GDS_PDK_ROOT` to the directory containing
that `sky130A` installation. All source RTL/configuration is included here.

```bash
set -eu
MODEL2GDS_PACKAGE="$(pwd)"
MODEL2GDS_RUN=/tmp/model2gds_counter_001
mkdir "$MODEL2GDS_RUN"
cp phase0/smoke/openlane/config.json "$MODEL2GDS_RUN/config.json"
python -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d["VERILOG_FILES"]=["/work/phase0/smoke/rtl/phase0_counter.v"]; open(p,"w").write(json.dumps(d,indent=2)+"\n")' "$MODEL2GDS_RUN/config.json"
docker run --rm --user "$(id -u):$(id -g)" --env HOME=/tmp --env PDK_ROOT=/pdk \
  --volume "$MODEL2GDS_PACKAGE:/work:ro" --volume "$MODEL2GDS_PDK_ROOT:/pdk:ro" \
  --volume "$MODEL2GDS_RUN:/out" --workdir /work \
  ghcr.io/efabless/openlane2@sha256:37c3bd4ea0534a276cb2deb88d601044857bad2807b9bc5b36efe9d02c62624e \
  openlane --manual-pdk --pdk-root /pdk --pdk sky130A --scl sky130_fd_sc_hd \
  --flow Classic --jobs 2 --run-tag REBUILD_001 --hide-progress-bar /out/config.json
```

The sole transformation above relocates the input path; it changes no RTL or
backend setting. OpenLane writes reports and the layout under the fresh output
mount. Preserve failures as well as successful outputs. These optional commands
are supplied for reproduction; they are not run by package generation.
