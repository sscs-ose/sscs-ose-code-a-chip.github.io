#!/bin/bash
# Fast tool install for ep_cim_loop.ipynb on Google Colab (Ubuntu 22.04 x86_64), or any Ubuntu 22.04 x86_64 machine.
#   bash env/colab_setup.sh [ENV folder]        (default ~/oss_env)   then put ENV/bin first on PATH
# No compiling: Xyce 7.10 comes from a prebuilt bundle, the rest from public binaries.
#   tools   : prebuilt bundle (Xyce 7.10 + Trilinos 14.4) from env/tools/ (or $TOOLS_URL),
#             sha256 checked, unpacked to ENV/ep_dr_tools (binaries carry their own .so files, RUNPATH $ORIGIN/../lib);
#   openroad: root (Colab): apt-get install of the public OpenROAD .deb (Precision Innovations 2024-12-14, Ubuntu 22.04) + its apt deps
#             not root    : env/setup.sh parts mamba eda openroad (user space, same as the full install)
#   eda     : micromamba envs ENV/eda (conda-forge Magic 8.3.678) and ENV/netgen (litex-hub Netgen 1.5)
#   dig     : micromamba env ENV/dig (conda-forge Yosys + Icarus Verilog) for the digital blocks
#   py      : pip install env/requirements.txt (on Colab the Jupyter packages are left as Colab ships them)
#   pdk     : volare enable sky130A c6d73a35 in $EP_PDK_ROOT (default ~/pdk/volare)
# ENV/bin then holds magic netgen openroad Xyce (the tools the notebook looks for on PATH) and yosys iverilog vvp.
# Environment: TOOLS_URL (bundle URL; file:// works), TOOLS_SHA256 (expected sha256; "skip" = do not check), EP_PDK_ROOT, PYTHON (default python3).
# Each part prints "PART <name> <seconds> <ok|fail>"; a part that is already installed returns at once.
set -o pipefail
E=$(mkdir -p "${1:-$HOME/oss_env}" && cd "${1:-$HOME/oss_env}" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
# The bundle ships in this folder (env/tools/, also in the official Code-a-Chip repository); TOOLS_URL overrides it.
LOCAL_TOOLS=$HERE/tools/ep_dr_tools_ubuntu22.tar.gz
if [ -f "$LOCAL_TOOLS" ]; then TOOLS_URL=${TOOLS_URL:-file://$LOCAL_TOOLS}
else TOOLS_URL=${TOOLS_URL:-https://raw.githubusercontent.com/sscs-ose/sscs-ose-code-a-chip.github.io/main/ISSCC27/submitted_notebooks/ep_cim_loop/env/tools/ep_dr_tools_ubuntu22.tar.gz}; fi
TOOLS_SHA256=${TOOLS_SHA256:-b49b91562246a8789d4b4147952f40b08930373ba53ff47cbe5d6852aea683ad}   # sha256 of ep_dr_tools_ubuntu22.tar.gz (bundle v1)
PR=${EP_PDK_ROOT:-$HOME/pdk/volare}
PY=${PYTHON:-python3}
PDK_REV=c6d73a35f524070e85faff4a6a9eef49553ebc2b
OR_DEB=https://github.com/Precision-Innovations/OpenROAD/releases/download/2024-12-14/openroad_2.0-17598-ga008522d8_amd64-ubuntu-22.04.deb
export MAMBA_ROOT_PREFIX=$E/mamba PIP_DISABLE_PIP_VERSION_CHECK=1 DEBIAN_FRONTEND=noninteractive
mkdir -p "$E/bin" "$E/logs" "$E/tmp"
export TMPDIR=${TMPDIR:-$E/tmp}      # pip and micromamba scratch (a small /tmp is a common failure)
MM=$E/bin/micromamba
ROOT=0; [ "$(id -u)" = 0 ] && command -v apt-get > /dev/null && ROOT=1
COLAB=0; { [ -n "${COLAB_RELEASE_TAG:-}" ] || [ -d /content ]; } && COLAB=1

part() {   # part <name> <function>
  local n=$1 f=$2 s rc
  s=$(date +%s%N)
  if $f > "$E/logs/colab_$n.log" 2>&1; then rc=ok; else rc=fail; tail -25 "$E/logs/colab_$n.log"; fi
  local ms=$(( ($(date +%s%N) - s) / 1000000 ))
  printf 'PART %s %d.%01d %s\n' "$n" $((ms / 1000)) $((ms % 1000 / 100)) "$rc"
  [ $rc = ok ]
}
wrap() {   # wrap <name> <target>: small launcher in ENV/bin
  printf '#!/bin/bash\nexec %s "$@"\n' "$2" > "$E/bin/$1"; chmod +x "$E/bin/$1"
}

do_base() {   # curl, bzip2 (micromamba), ca-certificates; Colab has them, a bare Ubuntu image may not
  local miss=""
  for c in curl bzip2 tar sha256sum; do command -v $c > /dev/null || miss="$miss $c"; done
  [ -z "$miss" ] && return 0
  [ $ROOT = 1 ] || { echo "missing:$miss (install them, no root here)"; return 1; }
  apt-get update -qq && apt-get install -y -qq --no-install-recommends curl ca-certificates bzip2 coreutils tar
}

do_tools() {
  local T=$E/ep_dr_tools f=$E/tmp/ep_dr_tools_ubuntu22.tar.gz
  if [ ! -f "$T/.installed" ]; then
    curl -fL --retry 5 --retry-delay 3 -o "$f" "$TOOLS_URL" || return 1
    if [ "$TOOLS_SHA256" != skip ] && [ "$TOOLS_SHA256" != @TOOLS_SHA256@ ]; then
      echo "$TOOLS_SHA256  $f" | sha256sum -c - || return 1
    fi
    sha256sum "$f"
    rm -rf "$T" "$E/.x_tools" && mkdir -p "$E/.x_tools" && tar -xzf "$f" -C "$E/.x_tools" && mv "$E/.x_tools/ep_dr_tools" "$T" && rmdir "$E/.x_tools" || return 1
    sed -i "s#@NGSPICE_LIB@#$T/ngspice/lib/ngspice#g" "$T/ngspice/share/ngspice/scripts/spinit"
    rm -f "$f"; touch "$T/.installed"
  fi
  # same place as env/setup.sh (ENV/xyce/bin/Xyce); the bundle also holds ngspice and OpenVAF, which the notebook does not use
  ln -sfn ep_dr_tools/xyce "$E/xyce"
  ln -sf "$T/xyce/bin/Xyce" "$E/bin/Xyce"
  "$E/bin/Xyce" -v
}

do_openroad() {
  if [ $ROOT = 1 ]; then
    [ -x /usr/bin/openroad ] || {
      curl -fsSL --retry 5 -o "$E/tmp/openroad.deb" "$OR_DEB" || return 1
      apt-get update -qq && apt-get install -y -qq --no-install-recommends "$E/tmp/openroad.deb" || return 1
      rm -f "$E/tmp/openroad.deb"; }
    wrap openroad "env QT_QPA_PLATFORM=offscreen /usr/bin/openroad"
  else
    bash "$HERE/setup.sh" "$E" mamba eda openroad || return 1     # user space: unpacked .deb + libraries from the conda env "eda"
  fi
  "$E/bin/openroad" -version
}

do_eda() {
  if [ ! -x "$MM" ]; then curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/2.3.0 | tar -xj -C "$E" bin/micromamba || return 1; fi
  [ -x "$E/eda/bin/magic" ] || "$MM" create -y -q -p "$E/eda" -c conda-forge magic=8.3.678 || return 1
  [ -x "$E/netgen/bin/netgen" ] || "$MM" create -y -q -p "$E/netgen" -c litex-hub -c conda-forge 'litex-hub::netgen>=1.5' || return 1
  "$MM" clean -y -a -q > /dev/null 2>&1
  wrap magic "$E/eda/bin/magic"; wrap netgen "$E/netgen/bin/netgen"
  "$E/bin/magic" -dnull -noconsole --version && echo exit | "$E/bin/netgen" -batch 2>&1 | head -2
}

do_dig() {   # Yosys (synthesis) + Icarus Verilog (RTL / gate simulation) for the digital blocks: conda-forge env ENV/dig
  if [ ! -x "$MM" ]; then curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/2.3.0 | tar -xj -C "$E" bin/micromamba || return 1; fi
  [ -x "$E/dig/bin/yosys" ] && [ -x "$E/dig/bin/iverilog" ] || "$MM" create -y -q -p "$E/dig" -c conda-forge yosys iverilog || return 1
  "$MM" clean -y -a -q > /dev/null 2>&1
  wrap yosys "$E/dig/bin/yosys"; wrap iverilog "$E/dig/bin/iverilog"; wrap vvp "$E/dig/bin/vvp"
  "$E/bin/yosys" -V && { "$E/bin/iverilog" -V 2>&1 || true; } | head -1   # iverilog -V exits 1 (no input file)
}

do_py() {
  local req=$E/tmp/requirements.txt U=""
  if [ $COLAB = 1 ]; then grep -Ev '^(ipykernel|jupyterlab|nbconvert|papermill)' "$HERE/requirements.txt" > "$req"; else cp "$HERE/requirements.txt" "$req"; fi
  [ "$(id -u)" = 0 ] || U=--user
  PIP_BREAK_SYSTEM_PACKAGES=1 "$PY" -m pip install -q $U -r "$req" || return 1
  "$PY" -c "import sys, torch, klayout, numpy, matplotlib, volare; print('python', sys.version.split()[0], 'torch', torch.__version__, 'klayout', klayout.__version__, 'numpy', numpy.__version__)"
}

do_pdk() {
  [ -f "$PR/sky130A/libs.tech/magic/sky130A.tech" ] || "$PY" -m volare enable --pdk sky130 --pdk-root "$PR" $PDK_REV || return 1
  head -2 "$PR/sky130A/SOURCES"
}

. /etc/os-release 2>/dev/null; [ "${ID:-}-${VERSION_ID:-}" = ubuntu-22.04 ] || echo "warning: built and checked for Ubuntu 22.04 x86_64, this is ${PRETTY_NAME:-unknown} $(uname -m)"
echo "colab_setup: ENV=$E root=$ROOT colab=$COLAB python=$("$PY" -c 'import sys; print(sys.version.split()[0])') cores=$(nproc)"
ok=1
for p in base tools openroad eda dig py pdk; do
  # without root, setup.sh (called by the openroad part) already makes the conda envs eda and netgen; eda then only adds the launchers
  part "$p" "do_$p" || ok=0
done
echo "PATH_ADD $E/bin"
ls "$E/bin"
[ $ok = 1 ]
