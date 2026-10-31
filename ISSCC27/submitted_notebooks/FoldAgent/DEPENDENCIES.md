# External dependencies at fixed revisions

The standalone RTL comparison uses Python 3.12 and Icarus Verilog. Joint timing uses OpenSTA plus one SKY130 Liberty file. Notebook execution additionally uses requirements.txt. The verification run records exact installed binary hashes under portability/environment.json.

## SKY130 typical-corner Liberty

Repository: [OpenROAD-flow-scripts](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/tree/1ec57da7bf0f1491190cbea2673c2c01fb3bc3ae)  
Commit: 1ec57da7bf0f1491190cbea2673c2c01fb3bc3ae  
File: flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib

The fixed public download was checked byte-for-byte by SHA-256 against the experimental library.

```sh
mkdir -p dependencies
curl --fail --location 'https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD-flow-scripts/1ec57da7bf0f1491190cbea2673c2c01fb3bc3ae/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib' -o dependencies/sky130_fd_sc_hd__tt_025C_1v80.lib
echo 'ec0e1067a35c8bf20b11e58d1e8ac53326067e4dac84a125cc1b917a3518d0d9  dependencies/sky130_fd_sc_hd__tt_025C_1v80.lib' | sha256sum -c -
export SKY130_TT_LIB="$PWD/dependencies/sky130_fd_sc_hd__tt_025C_1v80.lib"
```

Keep this export in the same shell used for the timing commands. The [SKY130 HD upstream license](https://github.com/google/skywater-pdk-libs-sky130_fd_sc_hd/blob/ac7fb61f06e6470b94e8afdf7c25268f62fbd7b1/LICENSE) is Apache-2.0. The library is obtained separately; its selected byte identity is in physical/library-requirement.json.

## Build the two tools

The following is a source-build recipe for Linux (Ubuntu 24.04 package names). Install build dependencies through the machine's normal package administrator:

```sh
sudo apt-get install build-essential git autoconf automake gperf bison flex cmake tcl-dev swig libeigen3-dev libfmt-dev zlib1g-dev libreadline-dev curl
```

Choose a new tools directory and keep CAC_TOOL_ROOT in the same shell:

```sh
export CAC_TOOL_ROOT="$PWD/cac-tools"
mkdir -p "$CAC_TOOL_ROOT/src" "$CAC_TOOL_ROOT/install"
git clone https://github.com/steveicarus/iverilog.git "$CAC_TOOL_ROOT/src/iverilog"
git -C "$CAC_TOOL_ROOT/src/iverilog" checkout dfeee909ed9f20b4870dd93423156c0170c0e1ff
cd "$CAC_TOOL_ROOT/src/iverilog"
sh autoconf.sh
./configure --prefix="$CAC_TOOL_ROOT/install"
make -j4
make install
```

This commit is the target of release tag **v13_0**. See the [fixed Icarus README](https://github.com/steveicarus/iverilog/blob/dfeee909ed9f20b4870dd93423156c0170c0e1ff/README.md) for supported build options. The tool uses GPL-2.0-or-later.

OpenSTA's recorded revision is **f89887b59600cd3a2a10c3de31bda4235d904cdf**, reporting version **3.1.0**. Build its required CUDD 3.0.0 dependency (commit f54f533303640afd5dbe47a05ebeabb3066f2a25), then OpenSTA:

```sh
git clone https://github.com/cuddorg/cudd.git "$CAC_TOOL_ROOT/src/cudd"
git -C "$CAC_TOOL_ROOT/src/cudd" checkout f54f533303640afd5dbe47a05ebeabb3066f2a25
cd "$CAC_TOOL_ROOT/src/cudd"
./configure --prefix="$CAC_TOOL_ROOT/install/cudd"
make -j4
make install
git clone https://github.com/The-OpenROAD-Project/OpenSTA.git "$CAC_TOOL_ROOT/src/OpenSTA"
git -C "$CAC_TOOL_ROOT/src/OpenSTA" checkout f89887b59600cd3a2a10c3de31bda4235d904cdf
cmake -S "$CAC_TOOL_ROOT/src/OpenSTA" -B "$CAC_TOOL_ROOT/src/OpenSTA/build" -DCMAKE_BUILD_TYPE=Release -DCUDD_DIR="$CAC_TOOL_ROOT/install/cudd" -DCMAKE_INSTALL_PREFIX="$CAC_TOOL_ROOT/install"
cmake --build "$CAC_TOOL_ROOT/src/OpenSTA/build" -j4
export IVERILOG_EXE="$CAC_TOOL_ROOT/install/bin/iverilog"
export VVP_EXE="$CAC_TOOL_ROOT/install/bin/vvp"
export PATH="$CAC_TOOL_ROOT/install/bin:$CAC_TOOL_ROOT/src/OpenSTA/build:$PATH"
```

Return to the review package directory before running reproduction commands. OpenSTA uses GPL-3.0-or-later; its [fixed README](https://github.com/The-OpenROAD-Project/OpenSTA/blob/f89887b59600cd3a2a10c3de31bda4235d904cdf/README.md) documents compiler, Tcl, SWIG, Eigen, CUDD and fmt requirements.

This revision verifies the submitted package using the recorded installed tools in an isolated extraction and fresh Python environment on the same host. The commands above document how to obtain/build those public tool revisions; rebuilding the tools on another operating system remains a separate portability check.

## Routing-tool patch provenance

The optional patches under physical/tool-patches/ apply to OpenROAD base commit **4a7cf9b22a5f24f32ce4f4eb1448fef4d2a367ca**. Their source is [OpenROAD at that commit](https://github.com/The-OpenROAD-Project/OpenROAD/tree/4a7cf9b22a5f24f32ce4f4eb1448fef4d2a367ca); retain the [upstream BSD-3-Clause notice](https://github.com/The-OpenROAD-Project/OpenROAD/blob/4a7cf9b22a5f24f32ce4f4eb1448fef4d2a367ca/LICENSE). The patches document the route/extraction repair used in the original experiment. The supplied final SPEFs let joint STA run directly with OpenSTA.

Full place-and-route regeneration needs the remaining original physical flow inputs and build environment described in physical/README.md.
