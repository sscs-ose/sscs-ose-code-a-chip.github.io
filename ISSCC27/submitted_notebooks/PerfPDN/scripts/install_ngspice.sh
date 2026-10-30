#!/usr/bin/env bash
set -euo pipefail
perfpdn_root="$(cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$perfpdn_root"
perfpdn_tools="$HOME/.local/share/perfpdn/tools"
perfpdn_binary="$perfpdn_tools/ngspice-47/bin/ngspice"
if [[ ! -x "$perfpdn_binary" ]]; then
  read -r perfpdn_url perfpdn_sha < <(
    "$HOME/.local/bin/uv" run --locked python - <<'PYCODE'
import json
from pathlib import Path
pin=json.loads(Path("config/ngspice.lock.json").read_text())["ngspice"]
print(pin["url"],pin["archive_sha256"])
PYCODE
  )
  mkdir -p "$perfpdn_tools/build"
  perfpdn_archive="$perfpdn_tools/build/ngspice-47.tar.gz"
  [[ -f "$perfpdn_archive" ]] || curl --fail --location --retry 2 "$perfpdn_url" -o "$perfpdn_archive"
  printf '%s  %s\n' "$perfpdn_sha" "$perfpdn_archive" | sha256sum --check
  tar -xzf "$perfpdn_archive" -C "$perfpdn_tools/build"
  (
    cd "$perfpdn_tools/build/ngspice-47"
    ./configure --prefix="$perfpdn_tools/ngspice-47" --enable-osdi --enable-xspice \
      --disable-debug --with-readline=yes --without-x >configure-perfpdn.log 2>&1
    make -j4 >make-perfpdn.log 2>&1
    make install >install-perfpdn.log 2>&1
  )
fi
"$perfpdn_binary" --version
