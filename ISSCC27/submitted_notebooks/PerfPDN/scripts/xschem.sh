#!/usr/bin/env bash
set -euo pipefail
perfpdn_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$perfpdn_root/scripts/env.sh"
export PERFPDN_PROJECT_ROOT="$perfpdn_root"
command -v xschem >/dev/null || { printf 'Install Xschem as described in the notebook environment setup.\n' >&2; exit 1; }
if [[ ! -f "$PDK_ROOT/$PDK/libs.tech/xschem/xschemrc" ]]; then
  printf 'SKY130 Xschem configuration is missing. Run bash scripts/install_pdk.sh.\n' >&2
  exit 1
fi
perfpdn_command='perfpdn_configure_ngspice'
perfpdn_args=()
while (( $# )); do
  if [[ "$1" == '--command' ]]; then
    if (( $# < 2 )); then
      printf 'The --command option needs a Tcl command.\n' >&2
      exit 1
    fi
    perfpdn_command+="; $2"
    shift 2
  else
    perfpdn_args+=("$1")
    shift
  fi
done
exec xschem --rcfile "$perfpdn_root/config/xschemrc" "${perfpdn_args[@]}" --command "$perfpdn_command"
