#!/usr/bin/env bash
set -euo pipefail

# ===========================================
# Config
# ===========================================
TOOLS_ROOT="${HOME}/tools"
BIN_DIR="${TOOLS_ROOT}/bin"
YOSYS_SRC_DIR="${TOOLS_ROOT}/yosys_src"
YOSYS_PREFIX="${TOOLS_ROOT}/yosys_install"
GTKWAVE_SRC_DIR="${TOOLS_ROOT}/gtkwave_src"

JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || nproc 2>/dev/null || echo 4)}"

# ===========================================
# Helpers
# ===========================================
msg() { printf "\033[1;32m[INFO]\033[0m %s\n" "$*"; }
warn(){ printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[ERR ]\033[0m %s\n" "$*" >&2; }

ensure_in_path() {
  local p="$1"
  case ":$PATH:" in *":$p:"*) : ;; *) export PATH="$p:$PATH";; esac
  grep -qs "export PATH=\"$p" "${HOME}/.bashrc" || echo "export PATH=\"$p:\$PATH\"" >> "${HOME}/.bashrc"
}

need_cmd() { command -v "$1" >/dev/null 2>&1 || return 1; }

# ===========================================
# Optional --clean to remove previous source builds
# ===========================================
if [[ "${1:-}" == "--clean" ]]; then
  msg "Cleaning previous source trees..."
  rm -rf "${YOSYS_SRC_DIR}" "${YOSYS_PREFIX}" "${GTKWAVE_SRC_DIR}"
  msg "Clean done."
  exit 0
fi

mkdir -p "${TOOLS_ROOT}" "${BIN_DIR}"

# ===========================================
# OS detect
# ===========================================
OS_ID="unknown"
if [[ -f /etc/os-release ]]; then
  # shellcheck source=/dev/null
  . /etc/os-release
  OS_ID="${ID:-unknown}"
fi

# ===========================================
# Install prerequisites (Ubuntu/Debian)
# ===========================================
apt_install_prereqs() {
  msg "Installing build prerequisites via APT..."
  sudo apt-get update
  sudo apt-get install -y --no-install-recommends \
    build-essential clang lld gcc g++ \
    bison flex libfl-dev \
    libreadline-dev gawk tcl-dev libffi-dev git \
    graphviz xdot pkg-config python3 python3-dev \
    libboost-system-dev libboost-python-dev libboost-filesystem-dev \
    zlib1g-dev ca-certificates \
    autoconf automake libtool \
    gtkwave || true
}

case "$OS_ID" in
  ubuntu|debian) apt_install_prereqs ;;
  *) warn "Non-Debian OS detected: ${OS_ID}. Please ensure deps are installed manually." ;;
esac

# ===========================================
# Install OpenSTA via APT (skip if already installed)
# ===========================================
install_opensta_via_apt() {
  if need_cmd sta; then
    msg "OpenSTA already present at: $(command -v sta). Skipping apt install."
    return
  fi
  msg "Installing OpenSTA via APT (package: opensta)..."
  if sudo apt-get install -y --no-install-recommends opensta; then
    if need_cmd sta; then
      msg "OpenSTA installed: $(command -v sta)"
    else
      warn "OpenSTA package installed but 'sta' not found in PATH. You may need to open a new shell or check /usr/bin/sta."
    fi
  else
    warn "APT does not provide 'opensta' on this system or installation failed. You can build from source if needed."
  fi
}

install_opensta_via_apt

# ===========================================
# Build Yosys (from source, with submodules) — skip if installed
# ===========================================
build_yosys() {
  if need_cmd yosys; then
    msg "yosys already present at: $(command -v yosys). Skipping build."
    return
  fi
  msg "Building Yosys from source..."
  if [[ ! -d "${YOSYS_SRC_DIR}" ]]; then
    git clone --recurse-submodules https://github.com/YosysHQ/yosys.git "${YOSYS_SRC_DIR}"
  else
    (cd "${YOSYS_SRC_DIR}" && git pull --ff-only && git submodule update --init --recursive)
  fi
  (
    cd "${YOSYS_SRC_DIR}"
    make clean || true

    if need_cmd clang; then
      msg "Configuring Yosys with clang"
      make config-clang
    else
      msg "Configuring Yosys with gcc"
      make config-gcc
    fi

    make -j"${JOBS}"
    make install PREFIX="${YOSYS_PREFIX}"
  )
  ensure_in_path "${YOSYS_PREFIX}/bin"
}

build_yosys

# ===========================================
# (Optional) Build GTKWave from source if not present — skip if installed
# ===========================================
build_gtkwave_from_source_if_needed() {
  if need_cmd gtkwave; then
    msg "gtkwave found at: $(command -v gtkwave). Skipping build."
    return
  fi
  msg "Building GTKWave from source..."
  if [[ ! -d "${GTKWAVE_SRC_DIR}" ]]; then
    git clone https://github.com/gtkwave/gtkwave.git "${GTKWAVE_SRC_DIR}"
  else
    (cd "${GTKWAVE_SRC_DIR}" && git pull --ff-only || true)
  fi
  (
    cd "${GTKWAVE_SRC_DIR}"
    ./configure --prefix="${TOOLS_ROOT}/gtkwave_install" || true
    make -j"${JOBS}"
    make install
  )
  ensure_in_path "${TOOLS_ROOT}/gtkwave_install/bin"
}

build_gtkwave_from_source_if_needed

# ===========================================
# Final report
# ===========================================
echo "======================================"
msg "Installation complete (Yosys + GTKWave + OpenSTA check)."

if need_cmd yosys; then
  yosys -V || true
else
  err "yosys not found in PATH"
fi

if need_cmd gtkwave; then
  gtkwave --version 2>/dev/null || true
else
  err "gtkwave not found in PATH"
fi

if need_cmd sta; then
  sta -version || true
else
  warn "OpenSTA (sta) not found in PATH. If 'opensta' package was unavailable, consider building from source."
fi
echo "======================================"
