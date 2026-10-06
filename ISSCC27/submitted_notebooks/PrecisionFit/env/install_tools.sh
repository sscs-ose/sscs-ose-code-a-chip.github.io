#!/usr/bin/env bash
# PrecisionFit -- environment setup (guide section 1).
#
# Everything here is open source and runs locally: no license server, no
# Cadence install. That is deliberate -- a reviewer must be able to reproduce
# the notebook without any licensed tools.
#
# Usage:  bash env/install_tools.sh
#
# Licensed under the Apache License, Version 2.0. See the repo LICENSE file.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== PrecisionFit environment setup =="

# ---- 1.1 Python environment ------------------------------------------------
python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip
pip install numpy scipy matplotlib jupyter jupyterlab pandas jinja2 tqdm nbformat nbclient ipykernel
python - <<'PY'
import numpy, scipy, matplotlib, pandas, jinja2, tqdm
print(f"numpy {numpy.__version__}  scipy {scipy.__version__}  "
      f"pandas {pandas.__version__}  jinja2 {jinja2.__version__}")
PY

# ---- 1.2 open-source simulators -------------------------------------------
# Verilator is the preferred (faster) simulation backend; Icarus Verilog is
# the fallback and is enough to reproduce every result in the notebook.
# The build script auto-detects whichever is present.
echo
echo "Checking simulators:"
if command -v verilator >/dev/null 2>&1; then
    echo "  verilator $(verilator --version)"
else
    echo "  verilator: NOT FOUND (optional; Icarus fallback will be used)"
    echo "    install: sudo apt-get install -y verilator"
fi
if command -v iverilog >/dev/null 2>&1; then
    echo "  $(iverilog -V 2>&1 | head -1)"
else
    echo "  iverilog: NOT FOUND -- required"
    echo "    install: sudo apt-get install -y iverilog"
fi

# ---- 1.3 Yosys (open-source synthesis) ------------------------------------
echo
if command -v yosys >/dev/null 2>&1; then
    echo "yosys: $(yosys -V)"
else
    echo "yosys: NOT FOUND -- required for area numbers"
    echo "  install: sudo apt-get install -y yosys"
fi

# ---- 1.4 OpenROAD + OpenSTA + SKY130 (Week 4, OPTIONAL) -------------------
echo
echo "Optional physical flow (guide section 6, not required for submission):"
echo "  git clone --depth 1 https://github.com/The-OpenROAD-Project/OpenLane2.git openlane2"
echo "  cd openlane2 && pip install openlane && openlane --smoke-test"
echo "  (several GB container + PDK; only needed to reproduce the SKY130 area/timing table)"

# ---- 1.5 verify the toolchain ---------------------------------------------
echo
if command -v yosys >/dev/null 2>&1; then
    echo "Toolchain smoke test (throwaway adder through Yosys):"
    TMP="$(mktemp -d)"
    cat > "$TMP/adder.v" <<'EOF'
module adder(input [7:0] a, b, output [8:0] sum);
  assign sum = a + b;
endmodule
EOF
    yosys -q -p "read_verilog $TMP/adder.v; synth -top adder; stat" | tail -3
    rm -rf "$TMP"
fi

echo
echo "Done. Next:"
echo "  source venv/bin/activate"
echo "  cd src/python && python sanity_check.py   # golden-model convergence"
echo "  jupyter nbconvert --to notebook --execute --inplace precisionfit.ipynb"
