#!/bin/bash
# PicoRV32 (ISC licence, YosysHQ) at a pinned commit; the source and the mapped netlist stay local (not redistributed).
set -e
D=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$D/../external/picorv32"; D="$D/../external/picorv32"; [ -d "$D/src" ] || git clone -q https://github.com/YosysHQ/picorv32 "$D/src"
git -C "$D/src" checkout -q ef203c2b0a3fb793280f5114941416c425c5b461
