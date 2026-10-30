#!/usr/bin/env bash
set -euo pipefail
perfpdn_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$perfpdn_root"
source scripts/env.sh
perfpdn_revision="$(uv run --locked python -c 'import json; print(json.load(open("config/pdk.lock.json"))["open_pdks_revision"])')"
[[ "$perfpdn_revision" =~ ^[0-9a-f]{40}$ ]] || { printf 'Invalid PDK revision in config/pdk.lock.json\n' >&2; exit 1; }
uv run --locked ciel enable \
  --data-source static-web:https://fossi-foundation.github.io/ciel-releases \
  --pdk-root "$PERFPDN_PDK_ROOT" --pdk-family sky130 \
  --include-libraries sky130_fd_pr "$perfpdn_revision"
printf '\nPinned SKY130 primitive library is available at %s/sky130A\n' "$PERFPDN_PDK_ROOT"
