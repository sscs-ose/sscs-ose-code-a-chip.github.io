#!/usr/bin/env bash
set -e
if [[ $# == 1 && "$1" == -v ]]; then
  cat "$(dirname "$0")/../../reports/pnr/klayout_version.log"
else
  exec /tmp/chipnebula-pinned-tools/bin/klayout "$@"
fi
