#!/usr/bin/env bash
# NeuroSAR — evaluation and export
# Usage: bash scripts/evaluate.sh [CHECKPOINT_PATH]

set -euo pipefail

CHECKPOINT="${1:-data/checkpoints/best_model.pt}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "============================================="
echo "  NeuroSAR Evaluation"
echo "  Checkpoint: $CHECKPOINT"
echo "============================================="

python src/evaluate.py --checkpoint "$CHECKPOINT" --export

echo ""
echo "Evaluation complete. Exports: data/exports/"
