#!/usr/bin/env bash
# NeuroSAR — full training run
# Usage: bash scripts/train.sh [EPOCHS]

set -euo pipefail

EPOCHS="${1:-500}"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "============================================="
echo "  NeuroSAR Training"
echo "  Epochs: $EPOCHS"
echo "============================================="

# Ensure dataset exists
if [ ! -f data/processed/sar_dataset.pt ]; then
    echo "[train.sh] Generating dataset first ..."
    python -c "
import sys; sys.path.insert(0, '.')
from src.dataset import generate_synthetic_dataset, save_dataset
data = generate_synthetic_dataset()
save_dataset(data)
"
fi

# Train
python src/train_pinn.py --epochs "$EPOCHS"

echo ""
echo "Training complete. Checkpoint: data/checkpoints/best_model.pt"
