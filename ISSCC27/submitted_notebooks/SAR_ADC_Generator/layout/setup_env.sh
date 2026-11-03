#!/bin/bash
# Create the pinned gLayout environment used by the layout stage (separate from the simulation Python,
# because glayout 0.2.0 needs gdsfactory 7.7 / numpy 1.26). Run inside IIC-OSIC-TOOLS or on Colab.
#   bash layout/setup_env.sh [venv_dir]      default: /foss/designs/.venvs/sargen-glayout
set -e
unset PYTHONPATH        # the IIC-OSIC-TOOLS PYTHONPATH carries a newer gdsfactory
VENV=${1:-${SARGEN_LAYOUT_VENV:-/foss/designs/.venvs/sargen-glayout}}
HERE=$(cd "$(dirname "$0")" && pwd)
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import glayout" 2>/dev/null; then
    echo "gLayout environment ready: $VENV"
    echo "activate: unset PYTHONPATH; . $VENV/bin/activate; export PDK=sky130A PDK_ROOT=/foss/pdks PYTHONPATH=\$PWD"; exit 0
fi
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
# exact versions, no resolver: glayout's own pins (numpy<=1.24) do not build on Python 3.12
"$VENV/bin/pip" install -q --no-deps -r "$HERE/requirements-glayout.txt"
"$VENV/bin/python" -c "import glayout, gdsfactory; print('glayout ok, gdsfactory', gdsfactory.__version__)"
echo "gLayout environment ready: $VENV"
echo "activate: unset PYTHONPATH; . $VENV/bin/activate; export PDK=sky130A PDK_ROOT=/foss/pdks PYTHONPATH=\$PWD"
