#!/usr/bin/env bash
# Thin wrapper to run a single command inside the LibreLane devshell AppImage,
# non-interactively. Usage:
#
#   tools/run_librelane.sh 'librelane config.yaml --run-tag demo'
#
# Override the AppImage location with LIBRELANE_APPIMAGE if needed.
#
# NOTE: the interactive devshell prints ANSI control sequences; callers that
# parse stdout should pipe through:
#   sed -E 's/\x1b\[[0-9;?]*[a-zA-Z]//g'
set -euo pipefail

APPIMAGE="${LIBRELANE_APPIMAGE:-$HOME/librelane-devshell-x86_64.AppImage}"
if [ ! -x "$APPIMAGE" ]; then
  echo "run_librelane.sh: LibreLane AppImage not found or not executable: $APPIMAGE" >&2
  exit 1
fi

if [ "$#" -eq 0 ]; then
  echo "run_librelane.sh: no command given" >&2
  echo "usage: $0 '<command to run inside devshell>'" >&2
  exit 2
fi

CMD="$*"
printf '%s\n' "$CMD" 'exit' | script -qec "$APPIMAGE" /dev/null
