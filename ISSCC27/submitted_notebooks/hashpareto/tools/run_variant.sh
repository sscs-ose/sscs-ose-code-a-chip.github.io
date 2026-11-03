#!/usr/bin/env bash
# Run (or resume) the LibreLane flow for one UNROLL variant.
#   usage: tools/run_variant.sh <UNROLL> [run-tag] [extra librelane args...]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
U="${1:?usage: run_variant.sh <UNROLL> [run-tag] [librelane args...]}"
TAG="${2:-run_$(date +%Y%m%d_%H%M%S)}"
if [ "$#" -ge 2 ]; then shift 2; else shift 1; fi
EXTRA="$*"
D="$ROOT/flow/variants/u$U"
cd "$D"
echo "variant dir : $D"
echo "run tag     : $TAG"
echo "extra args  : $EXTRA"
bash "$ROOT/tools/run_librelane.sh" "librelane config.yaml --run-tag $TAG --condensed $EXTRA"
echo "FLOW_EXIT_OK"