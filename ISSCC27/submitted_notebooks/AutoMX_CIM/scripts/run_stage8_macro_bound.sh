#!/usr/bin/env bash
# Run only after the clocked wrapper's independent sign-off receipt exists.
# This script does not convert an OpenLane exit code into a PPA/silicon claim.
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
design="$root/openlane/automx_cim_tile_controller"
tag="${1:-stage8_$(date -u +%Y%m%dT%H%M%SZ)}"
if [[ ! "$tag" =~ ^[A-Za-z0-9_-]+$ ]]; then
    echo "OpenLane tag must contain only letters, digits, underscores or hyphens" >&2
    exit 2
fi
python_bin="${AUTOMX_PYTHON_BIN:-$(command -v python3 || command -v python || true)}"
if [[ -z "$python_bin" ]]; then
    echo "Python is required for preflight and final audit" >&2
    exit 127
fi
if ! "$python_bin" -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null; then
    echo "Stage-8 preflight/audit require Python 3.10 or newer; set AUTOMX_PYTHON_BIN to a compatible interpreter" >&2
    exit 127
fi
if [[ -e "$design/runs/$tag" ]]; then
    echo "OpenLane run tag already exists; choose a new tag: $tag" >&2
    exit 1
fi

flow="${OPENLANE_FLOW_TCL:-}"
if [[ -z "$flow" && -x /openlane/flow.tcl ]]; then
    flow=/openlane/flow.tcl
fi
if [[ -z "$flow" ]]; then
    flow="$(command -v flow.tcl || true)"
fi
if [[ ! -x "$flow" ]]; then
    echo "OpenLane flow.tcl is unavailable; run this script inside the OpenLane container or set OPENLANE_FLOW_TCL" >&2
    exit 127
fi
export OPENLANE_FLOW_TCL="$flow"
"$python_bin" "$root/scripts/run_stage8_preflight.py" --root "$root"

"$flow" -design "$design" -tag "$tag"
gds="$design/runs/$tag/results/final/gds/automx_cim_tile_controller.gds"
if [[ ! -s "$gds" ]]; then
    echo "OpenLane returned without a nonempty final GDS: $gds" >&2
    exit 1
fi
echo "Final GDS produced: $gds"
"$python_bin" "$root/scripts/audit_stage8_openlane.py" --root "$root" --tag "$tag"
echo "Stage-8 implementation estimate passed the configured report audit; this is not silicon measurement."
