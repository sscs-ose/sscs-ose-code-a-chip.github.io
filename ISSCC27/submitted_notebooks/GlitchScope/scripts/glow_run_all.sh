#!/bin/bash
# Run GLOW on every exported case (scripts/glow_compare.py export ...), smallest first.
#   bash scripts/glow_run_all.sh <GLOW-ICCAD26 checkout> [time limit per case, s]
# Needs: pip install gurobipy pydot networkx, and a full Gurobi licence (free for academics).
# Afterwards: python scripts/glow_compare.py import <lib> <name> [--factor F] for each case,
# or send data/glow/*/glow_*.dot and *.log back for the import.
set -uo pipefail
G=${1:?path to GLOW checkout}; TL=${2:-3600}
ROOT=$(cd "$(dirname "$0")/.." && pwd)
for d in $(for x in "$ROOT"/data/glow/*/; do echo "$(grep -c -- '->' "$x"/*.dot 2>/dev/null | tail -1) $x"; done | sort -n | cut -d' ' -f2); do
  echo "== $(basename "$d")  $(date +%H:%M)"
  sed -i "s/--time_limit [0-9.]*/--time_limit $TL/" "$d/run_glow.sh"
  bash "$d/run_glow.sh" "$G" > "$d/run.out" 2>&1 && echo "   done" || echo "   FAILED (see $d/run.out)"
  grep -hiE "optimal|time limit|infeasible|objective" "$d"/glow_*.log 2>/dev/null | tail -2 | sed 's/^/   /'
done
