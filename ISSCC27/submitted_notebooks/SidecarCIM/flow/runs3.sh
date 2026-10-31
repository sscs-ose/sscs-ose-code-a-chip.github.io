#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
python3 flow/sync_clock.py >/dev/null
bash flow/runflow.sh sidecarcim_top_ff_pipe_s3
echo done > flow/logs/s3.done
