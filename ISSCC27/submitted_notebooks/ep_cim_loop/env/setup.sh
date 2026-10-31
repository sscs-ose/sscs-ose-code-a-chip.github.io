#!/bin/bash
# Tool setup for ep_cim_loop.ipynb (Code-a-Chip, equilibrium-propagation chip). Called by notebook cell (1); can also be run by hand.
#   bash env/setup.sh <ENV folder> [part ...]     parts = mamba eda dig openroad py pdk xyce  (default: all)
# Docker image (env/Dockerfile): all EDA tools are already on PATH -> with no parts given, only "py" and "pdk" are checked (both return at once).
# Otherwise everything is installed in user space (no root; needs python3 >= 3.10, curl, tar, bzip2 on x86_64 Linux):
#   mamba   : micromamba binary (conda-forge package manager)
#   eda     : two conda envs - eda (conda-forge: Magic 8.3.678 + python 3.10, Qt5, tclreadline for OpenROAD), netgen (litex-hub: Netgen 1.5 for LVS)
#   dig     : conda env dig (conda-forge: Yosys + Icarus Verilog) for the digital blocks
#   openroad: public OpenROAD release (Precision Innovations, Ubuntu 22.04 .deb), unpacked only, run through $E/bin/openroad with the eda env libraries
#   py      : pip install --user -r env/requirements.txt (numpy, torch CPU, klayout, matplotlib, volare, papermill, ...)
#   pdk     : volare -> open_pdks sky130A (c6d73a35) in $EP_PDK_ROOT (default ~/pdk/volare)
#   xyce    : Trilinos 14.4 + Xyce 7.10 from source (Xyce is not in conda); compilers, cmake, BLAS from the conda env xybuild
# Each part prints "PART <name> <seconds> <ok|fail>"; a part that is already installed returns at once.
set -o pipefail
E=$(mkdir -p "${1:?ENV folder}" && cd "$1" && pwd); shift
HERE=$(cd "$(dirname "$0")" && pwd)
PR=${EP_PDK_ROOT:-$HOME/pdk/volare}
ONPATH=1; for t in magic netgen openroad Xyce; do command -v $t > /dev/null || ONPATH=0; done
if [ $# = 0 ] && [ $ONPATH = 1 ]; then echo "EDA tools found on PATH (container): checking Python packages and PDK only"; PARTS="py pdk"; else PARTS=${*:-"mamba eda dig openroad py pdk xyce"}; fi
NJ=${NJ:-$(nproc)}
BT=${BUILD_TMP:-$E/xybuild/src}      # source and build trees of ngspice, Trilinos, Xyce (can be deleted). On a slow shared file system use a local disk: BUILD_TMP=/local/dir
export MAMBA_ROOT_PREFIX=$E/mamba TMPDIR=${TMPDIR:-$E/tmp} PIP_CACHE_DIR=$E/pipcache
mkdir -p "$TMPDIR" "$E/bin" "$E/logs"
MM=$E/bin/micromamba
PDK_REV=c6d73a35f524070e85faff4a6a9eef49553ebc2b
TRI_V=14-4-0; XY_V=7.10.0             # Xyce 7.10 needs Trilinos >= 13.5 (INSTALL.md recommends 14.4)

get() {    # get <URL> <file>: resumes broken downloads (large source tarballs)
  curl -fsSL --http1.1 --retry 8 --retry-delay 5 --retry-all-errors -C - -o "$2" "$1"; [ -s "$2" ]
}

untar() {  # untar <tar.gz> <dir>: renamed only after a complete unpack (a broken unpack is not reused)
  mkdir -p ".x_$2" && tar -xzf "$1" -C ".x_$2" && mv ".x_$2/$2" "$2"
}

part() {   # part <name> <function>
  local n=$1 f=$2 s rc
  s=$(date +%s%N)
  if $f > "$E/logs/$n.log" 2>&1; then rc=ok; else rc=fail; tail -25 "$E/logs/$n.log"; fi
  local ms=$(( ($(date +%s%N) - s) / 1000000 ))
  printf 'PART %s %d.%01d %s\n' "$n" $((ms / 1000)) $((ms % 1000 / 100)) "$rc"
  [ $rc = ok ]
}

do_mamba() {
  [ -x "$MM" ] && return 0
  curl -fsSL https://micro.mamba.pm/api/micromamba/linux-64/2.3.0 | tar -xj -C "$E" bin/micromamba
  "$MM" --version
}

do_eda() {
  [ -x "$E/eda/bin/magic" ] || "$MM" create -y -p "$E/eda" -c conda-forge python=3.10 magic=8.3.678 'qt-main=5.15' tclreadline readline tk
  [ -x "$E/netgen/bin/netgen" ] || "$MM" create -y -p "$E/netgen" -c litex-hub -c conda-forge 'litex-hub::netgen>=1.5'
  "$E/eda/bin/magic" -dnull -noconsole --version
  echo exit | "$E/netgen/bin/netgen" -batch 2>&1 | head -3
}

do_dig() {   # Yosys + Icarus Verilog (digital blocks, section 8) from conda-forge, launchers in ENV/bin
  [ -x "$E/dig/bin/yosys" ] && [ -x "$E/dig/bin/iverilog" ] || "$MM" create -y -p "$E/dig" -c conda-forge yosys iverilog || return 1
  for t in yosys iverilog vvp; do printf '#!/bin/bash\nexec %s "$@"\n' "$E/dig/bin/$t" > "$E/bin/$t"; chmod +x "$E/bin/$t"; done
  "$E/bin/yosys" -V && { "$E/bin/iverilog" -V 2>&1 || true; } | head -1   # iverilog -V exits 1 (no input file)
}

do_openroad() {
  local OR_V=2.0-17598-ga008522d8 RT=${OR_RT:-$E/eda}
  if [ ! -x "$E/openroad_deb/usr/bin/openroad" ]; then
    curl -fsSL -o "$TMPDIR/openroad.deb" https://github.com/Precision-Innovations/OpenROAD/releases/download/2024-12-14/openroad_${OR_V}_amd64-ubuntu-22.04.deb
    mkdir -p "$E/openroad_deb" && dpkg-deb -x "$TMPDIR/openroad.deb" "$E/openroad_deb"     # without dpkg-deb: ar x + tar --zstd -xf data.tar.zst
  fi
  [ -x "$E/bin/openroad" ] && { "$E/bin/openroad" -version; return; }
  cat > "$E/bin/openroad" <<EOS
#!/bin/bash
export LD_LIBRARY_PATH=$E/openroad_deb/opt/or-tools/lib:$RT/lib\${LD_LIBRARY_PATH:+:\$LD_LIBRARY_PATH} LD_PRELOAD=$RT/lib/libreadline.so.8 QT_QPA_PLATFORM=offscreen TCLLIBPATH=$RT/lib
exec $E/openroad_deb/usr/bin/openroad "\$@"
EOS
  chmod +x "$E/bin/openroad"; "$E/bin/openroad" -version
}

do_py() {
  python3 -c "import torch, klayout, numpy, matplotlib, volare" 2>/dev/null && { python3 -c "import torch, klayout, numpy; print('torch', torch.__version__, 'klayout', klayout.__version__, 'numpy', numpy.__version__)"; return 0; }
  PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install --user -q -r "$HERE/requirements.txt"
  python3 -c "import torch, klayout, numpy; print('torch', torch.__version__, 'klayout', klayout.__version__, 'numpy', numpy.__version__)"
}

do_pdk() {
  [ -f "$PR/sky130A/libs.tech/magic/sky130A.tech" ] && { head -2 "$PR/sky130A/SOURCES"; return 0; }
  VL=$(command -v volare || python3 -c 'import site,os;print(os.path.join(site.getuserbase(),"bin","volare"))')
  "$VL" enable --pdk sky130 --pdk-root "$PR" $PDK_REV
  ls "$PR/sky130A/libs.ref"
}

do_openvaf() {
  [ -x "$E/bin/openvaf" ] && return 0
  curl -fsSL https://openva.fra1.cdn.digitaloceanspaces.com/openvaf_23_5_0_linux_amd64.tar.gz | tar -xz -C "$E/bin"
  "$E/bin/openvaf" --version
}

buildenv() {   # compilers, cmake, BLAS etc. (shared by the ngspice and Xyce builds)
  local P=$E/xybuild/env
  mkdir -p "$E/xybuild"
  [ -x "$P/bin/cmake" ] || "$MM" create -y -p "$P" -c conda-forge gcc_linux-64=11 gxx_linux-64=11 gfortran_linux-64=11 \
      cmake=3.27 make bison flex 'openblas=0.3.27' 'libblas=*=*openblas' 'liblapack=*=*openblas' suitesparse=5.10 fftw
  eval "$("$MM" shell hook -s bash)"; micromamba activate "$P"
}

do_ngspice() {
  [ -x "$E/ngspice/bin/ngspice" ] && return 0
  buildenv; mkdir -p "$BT"; cd "$BT"
  [ -d ngspice-47 ] || { get https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/ngspice-47.tar.gz/download ngspice-47.tar.gz && untar ngspice-47.tar.gz ngspice-47; }
  mkdir -p ngspice-47/release && cd ngspice-47/release
  ../configure --prefix="$E/ngspice" --with-x=no --with-readline=no --enable-openmp --disable-debug --enable-osdi CFLAGS="-O2" LDFLAGS="-Wl,-rpath,$CONDA_PREFIX/lib" > "$E/logs/ngspice_cfg.log" 2>&1 || { tail -30 "$E/logs/ngspice_cfg.log"; return 1; }
  make -j"$NJ" > "$E/logs/ngspice_make.log" 2>&1 && make install >> "$E/logs/ngspice_make.log" 2>&1 || { tail -30 "$E/logs/ngspice_make.log"; return 1; }
  "$E/ngspice/bin/ngspice" --version | head -3
}

do_xyce() {
  [ -x "$E/xyce/bin/Xyce" ] && return 0
  local B=$BT P=$E/xybuild/env
  buildenv; mkdir -p "$B"
  cd "$B"
  [ -d Trilinos-trilinos-release-$TRI_V ] || { get https://github.com/trilinos/Trilinos/archive/refs/tags/trilinos-release-$TRI_V.tar.gz tri.tar.gz && untar tri.tar.gz Trilinos-trilinos-release-$TRI_V; }
  [ -d Xyce-Release-$XY_V ] || { get https://github.com/Xyce/Xyce/archive/refs/tags/Release-$XY_V.tar.gz xyce.tar.gz && untar xyce.tar.gz Xyce-Release-$XY_V; }
  mkdir -p tri_build_$TRI_V && cd tri_build_$TRI_V
  cmake -G "Unix Makefiles" -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" -DCMAKE_Fortran_COMPILER="$FC" \
    -DCMAKE_INSTALL_PREFIX="$E/trilinos-$TRI_V" -DCMAKE_PREFIX_PATH="$P" \
    -DAMD_LIBRARY_DIRS="$P/lib" -DTPL_AMD_INCLUDE_DIRS="$P/include" \
    -DBLAS_LIBRARY_DIRS="$P/lib" -DLAPACK_LIBRARY_DIRS="$P/lib" -DTPL_BLAS_LIBRARIES="$P/lib/libblas.so" -DTPL_LAPACK_LIBRARIES="$P/lib/liblapack.so" \
    -C "$B/Xyce-Release-$XY_V/cmake/trilinos/trilinos-base.cmake" "$B/Trilinos-trilinos-release-$TRI_V"
  make -j"$NJ" install > "$E/logs/trilinos_make.log" 2>&1 || { tail -40 "$E/logs/trilinos_make.log"; return 1; }
  mkdir -p "$B/xy_build" && cd "$B/xy_build"
  cmake -DCMAKE_C_COMPILER="$CC" -DCMAKE_CXX_COMPILER="$CXX" -DCMAKE_INSTALL_PREFIX="$E/xyce" -DTrilinos_ROOT="$E/trilinos-$TRI_V" \
    -DCMAKE_PREFIX_PATH="$P" -DCMAKE_INSTALL_RPATH="$P/lib;$E/trilinos-$TRI_V/lib;$E/xyce/lib" -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON \
    "$B/Xyce-Release-$XY_V"
  make -j"$NJ" install > "$E/logs/xyce_make.log" 2>&1 || { tail -40 "$E/logs/xyce_make.log"; return 1; }
  "$E/xyce/bin/Xyce" -v
}

ok=1
for p in $PARTS; do part "$p" "do_$p" || ok=0; done
[ $ok = 1 ]
