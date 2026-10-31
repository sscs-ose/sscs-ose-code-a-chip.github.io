#!/bin/bash
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"  # repo root
cd "$ROOT" && source .venv/bin/activate
d=$1
python3 flow/sync_clock.py
start=$(date +%s)
librelane --docker-no-tty --dockerized flow/$d/config.json > flow/logs/flow_$d.log 2>&1
echo "EXIT $? ELAPSED $(( $(date +%s)-start )) s" >> flow/logs/flow_$d.log
