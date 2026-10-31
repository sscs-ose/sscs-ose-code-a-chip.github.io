#!/usr/bin/env bash
# Installs what the live-simulation section needs on a fresh Linux machine (Colab, or a container):
# the SKY130 PDK at the exact version used in this project (via volare) and ngspice 47 (the version
# used in this project), built from source because Linux packages are older. Takes about 5 minutes
# on Colab; safe to re-run.
set -euo pipefail
PDK_HASH=c6d73a35f524070e85faff4a6a9eef49553ebc2b
NGSPICE_VERSION=47
TOOLS=${TOOLS:-$HOME/rffp-tools}
mkdir -p "$TOOLS"

python3 -m pip install -q "volare==0.20.6" numpy
# enable the pinned PDK version, also when a different SKY130 version is already installed and enabled
enabled=$(volare output --pdk sky130 2>/dev/null || true)
if [ "$enabled" != "$PDK_HASH" ] || [ ! -f "$HOME/.volare/sky130A/libs.tech/ngspice/sky130.lib.spice" ]; then
  volare enable --pdk sky130 "$PDK_HASH"
fi
if [ "$(volare output --pdk sky130)" != "$PDK_HASH" ] || ! grep -q "$PDK_HASH" "$HOME/.volare/sky130A/SOURCES"; then
  echo "SKY130 PDK version check failed: expected $PDK_HASH" >&2; exit 1
fi
echo "SKY130 PDK $PDK_HASH enabled"

if ! "$TOOLS/ngspice/bin/ngspice" -v 2>/dev/null | grep -q "ngspice-$NGSPICE_VERSION"; then
  if ! command -v bison >/dev/null || ! command -v flex >/dev/null || ! command -v make >/dev/null; then
    SUDO=$([ "$(id -u)" = 0 ] && echo "" || echo sudo)
    $SUDO apt-get update -qq && $SUDO apt-get install -y -qq build-essential bison flex >/dev/null
  fi
  src=$(mktemp -d)
  curl -sL "https://sourceforge.net/projects/ngspice/files/ng-spice-rework/$NGSPICE_VERSION/ngspice-$NGSPICE_VERSION.tar.gz/download" \
    | tar -xz -C "$src"
  (cd "$src/ngspice-$NGSPICE_VERSION" && ./configure -q --prefix="$TOOLS/ngspice" --with-x=no --with-readline=no \
      --enable-openmp --disable-debug >/dev/null && make -s -j"$(nproc)" >/dev/null 2>&1 && make -s install >/dev/null)
  rm -rf "$src"
fi
"$TOOLS/ngspice/bin/ngspice" -v | grep ngspice
echo "add to PATH: $TOOLS/ngspice/bin"
