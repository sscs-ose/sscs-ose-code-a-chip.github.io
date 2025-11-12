#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "   EDA Tool Installation Script (Ubuntu)  "
echo "=========================================="

# -------- Utils --------
NPROC="$(command -v nproc >/dev/null 2>&1 && nproc || echo 2)"
PREFIX="/usr/local"
CUDD_PREFIX="/opt/cudd"
CUDD_LOCAL_TGZ="$(realpath ./src/cudd-3.0.0.tar.gz)"
CUDD_SRC_DIR="/tmp/cudd-3.0.0"

# ------------------------------
# Global setup
# ------------------------------
echo "[INFO] Updating system packages..."
sudo apt-get update -y
sudo apt-get install -y \
  git wget curl build-essential cmake g++ gcc make bison flex autoconf gperf \
  libreadline-dev libffi-dev libboost-system-dev libboost-filesystem-dev libboost-python-dev \
  python3 tcl-dev tk-dev libx11-dev libxft-dev libxext-dev libedit-dev pkg-config libfl-dev \
  libgmp-dev libmpfr-dev libmpc-dev zlib1g-dev \
  libeigen3-dev \
  gtkwave

# ------------------------------
# Clean old build trees
# ------------------------------
cd /tmp
rm -rf iverilog yosys OpenSTA "${CUDD_SRC_DIR}"

# ------------------------------
# Install CUDD 3.0.0 (from local ./src)
# ------------------------------
if [ -f "${CUDD_PREFIX}/include/cudd/cudd.h" ]; then
  echo "[INFO] CUDD already present at ${CUDD_PREFIX}, skipping build."
else
  if [ ! -f "${CUDD_LOCAL_TGZ}" ]; then
    echo "[ERR] Cannot find ./src/cudd-3.0.0.tar.gz"
    echo "Please make sure the tarball exists under ./src/ next to this script."
    exit 1
  fi

  echo "[INFO] Using local CUDD tarball: ${CUDD_LOCAL_TGZ}"
  tar xvfz "${CUDD_LOCAL_TGZ}" -C /tmp

  cd "${CUDD_SRC_DIR}"
  ./configure --prefix="${CUDD_PREFIX}"
  make -j"${NPROC}"
  sudo make install

  echo "${CUDD_PREFIX}/lib" | sudo tee /etc/ld.so.conf.d/cudd.conf >/dev/null
  sudo ldconfig

  cd /tmp
  echo "[OK] CUDD installed to ${CUDD_PREFIX}."
fi

# ------------------------------
# Install OpenSTA (with CUDD)
# ------------------------------
echo "[INFO] Cloning and building OpenSTA..."
git clone https://github.com/The-OpenROAD-Project/OpenSTA.git
cd OpenSTA
mkdir -p build && cd build

cmake -DCMAKE_INSTALL_PREFIX="${PREFIX}" -DCUDD_DIR="${CUDD_PREFIX}" ..
make -j"${NPROC}"
sudo make install
cd ../..
echo "[OK] OpenSTA installed successfully."

# ------------------------------
# Install Icarus Verilog
# ------------------------------
echo "[INFO] Cloning and building Icarus Verilog..."
git clone https://github.com/steveicarus/iverilog.git
cd iverilog
sh autoconf.sh
./configure --prefix="${PREFIX}"
make -j"${NPROC}"
sudo make install
cd ..
echo "[OK] Icarus Verilog installed successfully."

# ------------------------------
# Install Yosys
# ------------------------------
echo "[INFO] Cloning and building Yosys..."
git clone --recursive https://github.com/YosysHQ/yosys.git
cd yosys
git submodule update --init --recursive
make -j"${NPROC}" PREFIX="${PREFIX}"
sudo make install PREFIX="${PREFIX}"
cd ..
echo "[OK] Yosys installed successfully."

# ------------------------------
# Add to bash environment
# ------------------------------
echo "[INFO] Updating ~/.bashrc ..."

if ! grep -qE '(^|:)/usr/local/bin($|:)' <<< "${PATH}"; then
  if ! grep -q '/usr/local/bin' ~/.bashrc; then
    echo 'export PATH=$PATH:/usr/local/bin' >> ~/.bashrc
    echo "[OK] Added /usr/local/bin to PATH."
  fi
fi

if ! grep -q "alias opensta=" ~/.bashrc; then
  echo "alias opensta='sta'" >> ~/.bashrc
  echo "[OK] Added alias: opensta -> sta"
fi

if ! grep -q "${CUDD_PREFIX}/bin" ~/.bashrc; then
  echo "export PATH=\$PATH:${CUDD_PREFIX}/bin" >> ~/.bashrc
  echo "[OK] Added ${CUDD_PREFIX}/bin to PATH."
fi

if ! grep -q "LD_LIBRARY_PATH" ~/.bashrc; then
  echo "export LD_LIBRARY_PATH=\${LD_LIBRARY_PATH:-}:${CUDD_PREFIX}/lib" >> ~/.bashrc
  echo "[OK] Added ${CUDD_PREFIX}/lib to LD_LIBRARY_PATH."
fi

# ------------------------------
# Refresh current shell (best effort)
# ------------------------------
set +e
source ~/.bashrc 2>/dev/null || true
set -e

# ------------------------------
# Summary
# ------------------------------
echo
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo "  • Icarus Verilog : $(command -v iverilog || echo 'not found in PATH (open a new shell)')"
echo "  • GTKWave        : $(command -v gtkwave  || echo 'not found in PATH (open a new shell)')"
echo "  • Yosys          : $(command -v yosys    || echo 'not found in PATH (open a new shell)')"
echo "  • OpenSTA        : $(command -v sta      || echo 'not found in PATH (open a new shell)')"
echo
echo "You can now run: yosys, iverilog, gtkwave, opensta"
echo "=========================================="
