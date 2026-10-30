#!/bin/bash
# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: scripts/formal.sh
# Type: Script: run every formal proof (SymbiYosys)
# Author: Paul Vincent Bezzina
# Language: Bash
# Description:
# =============================================================================
set -e
cd "$(dirname "$0")/../formal"
fail=0
for f in *.sby; do
  name=${f%.sby}
  if sby -f "$f" > "$name.log" 2>&1; then
    echo "PASS  $name (prove and cover)"
  else
    echo "FAIL  $name, see formal/$name.log"
    fail=1
  fi
done
exit $fail
