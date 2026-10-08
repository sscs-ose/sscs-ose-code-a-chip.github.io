#!/usr/bin/env bash
# Package the exact OpenROAD-flow-scripts build used for Section 6 (commit 6101364b,
# OpenROAD f5522624, Yosys 0.68) into a relocatable tarball that runs on a stock
# Ubuntu 22.04 machine such as a Colab session: the OpenROAD/OpenSTA/Yosys binaries,
# the ORFS flow scripts with the sky130hd platform only, and every shared library the
# binaries need except the C library itself. The build uses no CPU-specific
# instruction-set flags (no -march=native), so it runs on any x86-64 host.
# usage: make_orfs_bundle.sh <out.tar.xz>
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
OUT=${1:?output tarball}
O="${ORFS_ROOT:-/opt/eda/orfs-6101364b}"
B="$(mktemp -d)/orfs"; mkdir -p "$B/tools/install" "$B/flow/platforms" "$B/lib"
cp -a "$O/tools/install/OpenROAD" "$O/tools/install/yosys" "$B/tools/install/"
( cd "$O/flow" && cp -a Makefile settings.mk scripts util "$B/flow/" )
cp -aL "$O/flow/platforms/sky130hd" "$B/flow/platforms/"   # -L: sky130hd links some files from sky130hs
[ -d "$O/flow/platforms/common" ] && cp -a "$O/flow/platforms/common" "$B/flow/platforms/"
# shared libraries: everything the binaries resolve, except glibc's own libraries and the loader
for f in "$B"/tools/install/OpenROAD/bin/* "$B"/tools/install/yosys/bin/yosys "$B"/tools/install/yosys/bin/yosys-abc; do
  ldd "$f" | awk '/=>/ {print $3}'
done | sort -u | grep -v -E '/(libc|libm|libpthread|libdl|librt|libresolv|libutil)\.so|ld-linux' |
  while read -r l; do cp -L "$l" "$B/lib/"; done
# the embedded Python interpreter of OpenROAD needs its standard library
PYV=$(ldd "$O/tools/install/OpenROAD/bin/openroad" | grep -oE 'libpython3\.[0-9]+' | head -1 | sed 's/libpython//')
if [ -n "$PYV" ]; then mkdir -p "$B/lib/python$PYV"; cp -a /usr/lib/python$PYV/. "$B/lib/python$PYV/"; rm -rf "$B/lib/python$PYV/test" "$B/lib/python$PYV/__pycache__"; fi
# Qt's headless platform plugin, used when the final report saves layout images
QTP=$(ls -d /usr/lib/x86_64-linux-gnu/qt5/plugins 2>/dev/null || true)
if [ -n "$QTP" ]; then
  mkdir -p "$B/lib/qt5/plugins/platforms"; cp -L "$QTP/platforms/libqoffscreen.so" "$B/lib/qt5/plugins/platforms/"
  ldd "$QTP/platforms/libqoffscreen.so" | awk '/=>/ {print $3}' |
    grep -v -E '/(libc|libm|libpthread|libdl|librt|libresolv|libutil)\.so|ld-linux' | while read -r l; do cp -Ln "$l" "$B/lib/" 2>/dev/null || true; done
fi
# Tcl's own script library (init.tcl and friends), needed by OpenROAD and Yosys at start-up
TCLDIR=$(ls -d /usr/share/tcltk/tcl8.6 2>/dev/null || true)
[ -n "$TCLDIR" ] && cp -a "$TCLDIR" "$B/lib/tcl8.6"
# wrappers that set the library path, placed first on PATH by the notebook
mkdir -p "$B/bin"
for t in openroad sta; do
  printf '#!/bin/sh\nD=$(cd "$(dirname "$0")/.." && pwd)\nLD_LIBRARY_PATH="$D/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" PYTHONHOME="$D" TCL_LIBRARY="$D/lib/tcl8.6" QT_QPA_PLATFORM_PLUGIN_PATH="$D/lib/qt5/plugins/platforms" QT_QPA_PLATFORM=offscreen exec "$D/tools/install/OpenROAD/bin/%s" "$@"\n' "$t" > "$B/bin/$t"
done
for t in yosys yosys-abc; do
  printf '#!/bin/sh\nD=$(cd "$(dirname "$0")/.." && pwd)\nLD_LIBRARY_PATH="$D/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" TCL_LIBRARY="$D/lib/tcl8.6" exec "$D/tools/install/yosys/bin/%s" "$@"\n' "$t" > "$B/bin/$t"
done
chmod +x "$B"/bin/*
cat > "$B/README.txt" <<EOF
OpenROAD-flow-scripts 6101364b (OpenROAD f5522624, Yosys 0.68), repackaged for the HSKEM Code-a-Chip
notebook. OpenROAD and ORFS: BSD-3-Clause; Yosys: ISC. The shared libraries in lib/ are unmodified copies
from Ubuntu 22.04 packages and ORFS's dependency build, each under its own license (e.g. Qt 5: LGPL-3.0,
OR-Tools and Abseil: Apache-2.0, Tcl: BSD, Python: PSF).
File list with sizes: MANIFEST.txt
EOF
( cd "$B" && find . -type f -printf '%s %p\n' | sort -k2 > MANIFEST.txt )
tar -C "$(dirname "$B")" -cf - orfs | xz -T0 -6 > "$OUT"
du -sh "$B" "$OUT"
