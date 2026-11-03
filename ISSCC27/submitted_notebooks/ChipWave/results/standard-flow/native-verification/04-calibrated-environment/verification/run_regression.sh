#!/usr/bin/env bash
set -e
source /tmp/chipnebula-pinned-tools/env.sh
export NEBULA_VERIFY_ENV1_STATUS=$?
source /opt/rh/gcc-toolset-13/enable
export NEBULA_VERIFY_ENV2_STATUS=$?
export NEBULA_VERIFY_SHELL_PID=$$
export NEBULA_VERIFY_CAPTURE="$PWD/build/verify/capture"
export PYTHONPATH="$PWD/verification${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONDONTWRITEBYTECODE=1
python3 -B verification/run_regression.py
