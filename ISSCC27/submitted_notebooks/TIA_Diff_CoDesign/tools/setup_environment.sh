#!/usr/bin/env bash
# Build the documented Linux/Python toolchain inside this submission folder.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OPT="$ROOT/tools/opt"
SRC="$ROOT/tools/src"
DL="$SRC/downloads"
BUILD="$ROOT/tools/build"
STAMPS="$ROOT/tools/logs/stamps"
LOGS="$ROOT/tools/logs"
VENV="$ROOT/.venv"
PDK_ROOT="${TIA_PDK_ROOT:?Install the PDK separately and set TIA_PDK_ROOT}"
PDK=ihp-sg13g2
PYTHON="${PYTHON:-python3.12}"
CPU_BUDGET="$($PYTHON -c 'import os; print(min(16,max(1,(os.cpu_count() or 2)//2)))')"
NJOBS="${NJOBS:-$CPU_BUDGET}"
if (( NJOBS < 1 || NJOBS > CPU_BUDGET )); then
    echo "NJOBS must be between 1 and $CPU_BUDGET" >&2; exit 2
fi
BOOST_VER=1.86.0
MPFR_VER=4.2.1
HDF5_VER=1.14.6
VTK_VER=9.3.1
CGAL_VER=5.6.2
NGSPICE_VER=47
OPENVAF_URL="https://openva.fra1.cdn.digitaloceanspaces.com/openvaf_23_5_0_linux_amd64.tar.gz"
mkdir -p "$OPT" "$SRC" "$DL" "$BUILD" "$STAMPS" "$LOGS"
export PATH="$OPT/bin:$PATH" CMAKE_PREFIX_PATH="$OPT" PKG_CONFIG_PATH="$OPT/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
export LD_LIBRARY_PATH="$OPT/lib:${LD_LIBRARY_PATH:-}" CC=gcc CXX=g++
if ! printf '#include <gmp.h>\nint main(void){mpz_t x;mpz_init(x);mpz_clear(x);return 0;}\n' | gcc -x c - -lgmp -o "$BUILD/check_gmp"; then
    echo 'Install GMP development headers/libraries before building MPFR and CGAL.' >&2; exit 2
fi
step() {
    local name="$1" fn="$2"
    if [[ -f "$STAMPS/$name" ]]; then echo "[complete] $name"; return; fi
    if (set -euo pipefail; "$fn") > "$LOGS/$name.log" 2>&1; then
        touch "$STAMPS/$name"; echo "[complete] $name"
    else
        echo "[failed] $name; inspect tools/logs/$name.log" >&2; exit 1
    fi
}
fetch() {
    [[ -s "$DL/$2" ]] || curl -fL --retry 3 -o "$DL/$2" "$1"
}
do_venv() {
    "$PYTHON" -m venv "$VENV"
    "$VENV/bin/python" -m pip install -r "$ROOT/requirements.txt"
}
do_source() {
    if [[ ! -d "$SRC/openEMS-Project/.git" ]]; then
        git clone https://github.com/thliebig/openEMS-Project.git "$SRC/openEMS-Project"
    fi
    git -C "$SRC/openEMS-Project" checkout 974294ba7d812ef5a46a4760593057aee7ce6866
    git -C "$SRC/openEMS-Project" submodule update --init --recursive
}

do_boost() {
  local v="${BOOST_VER//./_}"
  fetch "https://archives.boost.io/release/$BOOST_VER/source/boost_$v.tar.gz" "boost_$v.tar.gz"
  rm -rf "$BUILD/boost_$v"; tar -xzf "$DL/boost_$v.tar.gz" -C "$BUILD"
  cd "$BUILD/boost_$v"
  ./bootstrap.sh --prefix="$OPT" --with-toolset=gcc \
    --with-libraries=system,thread,date_time,serialization,chrono,program_options,atomic,filesystem
  ./b2 -j"$NJOBS" variant=release link=shared threading=multi \
    hardcode-dll-paths=true dll-path="$OPT/lib" install
}

do_mpfr() {
  fetch "https://ftp.gnu.org/gnu/mpfr/mpfr-$MPFR_VER.tar.xz" "mpfr-$MPFR_VER.tar.xz"
  rm -rf "$BUILD/mpfr-$MPFR_VER"; tar -xJf "$DL/mpfr-$MPFR_VER.tar.xz" -C "$BUILD"
  cd "$BUILD/mpfr-$MPFR_VER"
  ./configure --prefix="$OPT" --enable-shared --disable-static
  make -j"$NJOBS" && make install
}

do_hdf5() {
  fetch "https://github.com/HDFGroup/hdf5/releases/download/hdf5_$HDF5_VER/hdf5-$HDF5_VER.tar.gz" "hdf5-$HDF5_VER.tar.gz"
  rm -rf "$BUILD/hdf5-$HDF5_VER"; tar -xzf "$DL/hdf5-$HDF5_VER.tar.gz" -C "$BUILD"
  cd "$BUILD/hdf5-$HDF5_VER"
  ./configure --prefix="$OPT" --enable-hl --enable-shared --disable-static \
    --disable-fortran --enable-cxx --disable-tests
  make -j"$NJOBS" && make install
}

do_vtk() {
  fetch "https://www.vtk.org/files/release/${VTK_VER%.*}/VTK-$VTK_VER.tar.gz" "VTK-$VTK_VER.tar.gz"
  rm -rf "$BUILD/VTK-$VTK_VER" "$BUILD/vtk-build"; tar -xzf "$DL/VTK-$VTK_VER.tar.gz" -C "$BUILD"
  # Only the IO modules needed by CSXCAD/openEMS; no rendering, no Python wrapping.
  cmake -S "$BUILD/VTK-$VTK_VER" -B "$BUILD/vtk-build" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$VENV/bin/ninja" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$OPT" \
    -DCMAKE_INSTALL_RPATH="$OPT/lib" -DCMAKE_INSTALL_LIBDIR=lib \
    -DBUILD_SHARED_LIBS=ON -DVTK_BUILD_TESTING=OFF -DVTK_BUILD_EXAMPLES=OFF \
    -DVTK_WRAP_PYTHON=OFF -DVTK_USE_MPI=OFF -DVTK_ENABLE_REMOTE_MODULES=OFF \
    -DVTK_GROUP_ENABLE_Imaging=DONT_WANT -DVTK_GROUP_ENABLE_MPI=DONT_WANT \
    -DVTK_GROUP_ENABLE_Qt=DONT_WANT -DVTK_GROUP_ENABLE_Rendering=DONT_WANT \
    -DVTK_GROUP_ENABLE_StandAlone=DONT_WANT -DVTK_GROUP_ENABLE_Views=DONT_WANT \
    -DVTK_GROUP_ENABLE_Web=DONT_WANT \
    -DVTK_MODULE_ENABLE_VTK_IOXML=YES -DVTK_MODULE_ENABLE_VTK_IOGeometry=YES \
    -DVTK_MODULE_ENABLE_VTK_IOLegacy=YES -DVTK_MODULE_ENABLE_VTK_IOPLY=YES
  cmake --build "$BUILD/vtk-build" -j "$NJOBS"
  cmake --install "$BUILD/vtk-build"
}

do_cgal() {
  fetch "https://github.com/CGAL/cgal/releases/download/v$CGAL_VER/CGAL-$CGAL_VER.tar.xz" "CGAL-$CGAL_VER.tar.xz"
  rm -rf "$BUILD/CGAL-$CGAL_VER" "$BUILD/cgal-build"; tar -xJf "$DL/CGAL-$CGAL_VER.tar.xz" -C "$BUILD"
  cmake -S "$BUILD/CGAL-$CGAL_VER" -B "$BUILD/cgal-build" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$OPT" -DCMAKE_INSTALL_LIBDIR=lib
  cmake --install "$BUILD/cgal-build"
}

do_tinyxml() {
  cd "$SRC/openEMS-Project"
  mkdir -p "$BUILD/tinyxml"
  ./scripts/build_tinyxml.sh --download-dir "$DL" --build-dir "$BUILD/tinyxml" --install-dir "$OPT"
}

do_ngspice() {
  fetch "https://sourceforge.net/projects/ngspice/files/ng-spice-rework/$NGSPICE_VER/ngspice-$NGSPICE_VER.tar.gz/download" "ngspice-$NGSPICE_VER.tar.gz"
  rm -rf "$BUILD/ngspice-$NGSPICE_VER"; tar -xzf "$DL/ngspice-$NGSPICE_VER.tar.gz" -C "$BUILD"
  mkdir -p "$BUILD/ngspice-$NGSPICE_VER/release" && cd "$BUILD/ngspice-$NGSPICE_VER/release"
  ../configure --prefix="$OPT" --with-x=no --with-readline=no --enable-xspice \
    --enable-cider --enable-osdi --enable-openmp --disable-debug \
    CFLAGS="-O2" LDFLAGS="-Wl,-rpath,$OPT/lib"
  make -j"$NJOBS" && make install
}

do_openvaf() {
  fetch "$OPENVAF_URL" openvaf-23.5.0.tar.gz
  rm -rf "$BUILD/openvaf" "$OPT/bin/openvaf-r" && mkdir -p "$BUILD/openvaf"
  tar -xzf "$DL/openvaf-23.5.0.tar.gz" -C "$BUILD/openvaf"
  install -D -m 755 "$BUILD/openvaf/openvaf" "$OPT/bin/openvaf"
  openvaf --version
}

do_osdi() {
  bash "$ROOT/tools/compile_models.sh"
}

# ---------------------------------------------------------------- openEMS
cmake_oems() {  # cmake_oems <subdir> [extra args]
  local name="$1"; shift
  rm -rf "$BUILD/oems-$name"
  cmake -S "$SRC/openEMS-Project/$name" -B "$BUILD/oems-$name" \
    -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$OPT" \
    -DCMAKE_PREFIX_PATH="$OPT" -DCMAKE_INSTALL_RPATH="$OPT/lib" \
    -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON -DBOOST_ROOT="$OPT" -DHDF5_ROOT="$OPT" "$@"
  cmake --build "$BUILD/oems-$name" -j "$NJOBS"
  cmake --install "$BUILD/oems-$name"
}

do_openems() {
  cmake_oems fparser
  cmake_oems CSXCAD -DFPARSER_ROOT_DIR="$OPT"
  cmake_oems openEMS -DFPARSER_ROOT_DIR="$OPT" -DCSXCAD_ROOT_DIR="$OPT"
}

do_openems_python() {
  export CSXCAD_INSTALL_PATH="$OPT" OPENEMS_INSTALL_PATH="$OPT" CSXCAD_NOSCM=1 OPENEMS_NOSCM=1
  "$VENV/bin/pip" install --no-build-isolation -v "$SRC/openEMS-Project/CSXCAD/python"
  "$VENV/bin/pip" install --no-build-isolation -v "$SRC/openEMS-Project/openEMS/python"
}


step python do_venv
step source do_source
step boost do_boost
step mpfr do_mpfr
step hdf5 do_hdf5
step vtk do_vtk
step cgal do_cgal
step tinyxml do_tinyxml
step ngspice do_ngspice
step openvaf do_openvaf
step osdi do_osdi
step openems do_openems
step openems-python do_openems_python
cat > "$ROOT/tools/activate.sh" <<'ACTIVATE'
TIA_SUBMISSION_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TIA_SUBMISSION_ROOT/.venv/bin/activate"
export PATH="$TIA_SUBMISSION_ROOT/tools/opt/bin:$PATH"
export LD_LIBRARY_PATH="$TIA_SUBMISSION_ROOT/tools/opt/lib:${LD_LIBRARY_PATH:-}"
export TIA_PDK_ROOT="${TIA_PDK_ROOT:?Set TIA_PDK_ROOT to the external PDK checkout}"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
ACTIVATE
echo 'Toolchain ready. Run: source tools/activate.sh'
