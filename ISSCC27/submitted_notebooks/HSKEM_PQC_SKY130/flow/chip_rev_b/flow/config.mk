export DESIGN_NICKNAME = trustedge_asic_core
export DESIGN_NAME = trustedge_asic_core
export PLATFORM = sky130hd

TRUSTEDGE_ROOT ?= /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/build_pub/root
ORIG_ROOT := /mnt/d/TKVM_ATTT_2026_test
A2_SOURCE_LIST := /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/sources.f
A2_REL_SOURCES := $(shell sed -n '/^[^+]/p' $(A2_SOURCE_LIST))

export VERILOG_FILES = $(addprefix $(TRUSTEDGE_ROOT)/,$(A2_REL_SOURCES))
export VERILOG_INCLUDE_DIRS = $(TRUSTEDGE_ROOT)/rtl/kyber
export VERILOG_DEFINES = -D TRUSTEDGE_ASIC_SRAM -D TRUSTEDGE_ASIC_MACRO_BIND -D TRUSTEDGE_ASIC_SERVICE_PORTS -D TRUSTEDGE_ASIC_SKY130_RESET_CELLS -D NTT_PAIR_SRAM_MACRO -D TRUSTEDGE_PMAC_RETIME -D TRUSTEDGE_SO_PIPE -D TRUSTEDGE_PACKED_NTT -D TRUSTEDGE_HASH_OVERLAP -D TRUSTEDGE_STREAM_IO -D TRUSTEDGE_FAST_BASEMUL -D TRUSTEDGE_FAST_FEED -D TRUSTEDGE_STREAM_OUT -D TRUSTEDGE_FOLD_READBACK -D TRUSTEDGE_PREFETCH -D TRUSTEDGE_TIGHT_LOOPS -D TRUSTEDGE_FAST_CHECK -D TRUSTEDGE_FAST_Y -D TRUSTEDGE_PACKED2 -D TRUSTEDGE_FAST_PRF -D TRUSTEDGE_FUSED_CMP -D TRUSTEDGE_FAST_READ -D TRUSTEDGE_PIPE_CHECK -D TRUSTEDGE_PAIR_PORT -D TRUSTEDGE_DEFER_J -D TRUSTEDGE_PIPE_MAC -D TRUSTEDGE_FAST_HASH -D TRUSTEDGE_DEC_STREAM -D TRUSTEDGE_SEG_CHECK -D TRUSTEDGE_BG_PRF -D TRUSTEDGE_STREAM_INV -D TRUSTEDGE_STREAM_FWD -D TRUSTEDGE_PRF_TO_NTT -D TRUSTEDGE_STREAM_DEC_INV -D TRUSTEDGE_PRF_FINE_HOLD -D TRUSTEDGE_POLY_GUARD
export VERILOG_DEFINES += $(T3_DEFINES_EXTRA)
export SYNTH_HDL_FRONTEND = slang
export SDC_FILE = /mnt/d/TKVM_ATTT_2026_test/codeachip_t3/flow_chip/constraint.sdc

# The qualified OpenRAM LEFs use vccd1/vssd1 rather than the default
# sky130hd VPWR/VGND-style macro pin names.  Register those names before the
# platform PDN script runs global_connect.
export PRE_PDN_TCL = $(ORIG_ROOT)/asic/orfs/pre_pdn.tcl

# M5 consumes the eight immutable derived views qualified by M4-PHY.  Keep a
# short-lived M3 alias so an old invocation fails only on a missing/empty view,
# never by silently dropping the new four masters.
ifneq ($(strip $(M5_MACRO_LEFS)),)
  A2_MACRO_LEFS := $(M5_MACRO_LEFS)
else ifneq ($(strip $(M3_MACRO_LEFS)),)
  A2_MACRO_LEFS := $(M3_MACRO_LEFS)
else
$(error M5_MACRO_LEFS must name the eight M4 derived LEF views)
endif
ifneq ($(strip $(M5_MACRO_LIBS)),)
  A2_MACRO_LIBS := $(M5_MACRO_LIBS)
else ifneq ($(strip $(M3_MACRO_LIBS)),)
  A2_MACRO_LIBS := $(M3_MACRO_LIBS)
else
$(error M5_MACRO_LIBS must name the eight M4 derived Liberty views)
endif
export ADDITIONAL_LEFS = $(A2_MACRO_LEFS)
export ADDITIONAL_LIBS = $(A2_MACRO_LIBS)

# Final stream-out must merge the real OpenRAM geometries, not only the LEF
# abstracts used by place/route.  The companion GDS gate pins hashes, validates
# the expected top cells and rejects empty geometry before A3.
A2_MACRO_GDS_ROOT ?= /opt/eda/openram-smoke
A2_MACRO_GDS := \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_16x256_wpr8_vdd_via_column_mux_candidate/sky130_sram_1rw_16x256_wpr8.gds \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_24x256_vdd_via_column_mux_candidate/sky130_sram_1rw_24x256.gds \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_8x768_vdd_via_column_mux_candidate/sky130_sram_1rw_8x768.gds \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_24x128_vdd_via_column_mux_candidate/sky130_sram_1rw_24x128.gds \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_12x256_wpr8_candidate/sky130_sram_1rw_12x256_wpr8.gds \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_12x512_wpr8_candidate/sky130_sram_1rw_12x512_wpr8.gds \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_12x640_wpr8_candidate/sky130_sram_1rw_12x640_wpr8.gds \
  $(A2_MACRO_GDS_ROOT)/sky130_sram_1rw_12x768_wpr8_candidate/sky130_sram_1rw_12x768_wpr8.gds
export ADDITIONAL_GDS = $(A2_MACRO_GDS)

# The screening configuration deliberately maps every remaining inferred memory to real
# standard cells.  The largest current generic memory is 9,216 bits.  This is
# diagnostic evidence, not the final A2 architecture.  Do not enable
# SYNTH_MOCK_LARGE_MEMORIES: that would make area/timing structurally unreal.
export SYNTH_MEMORY_MAX_BITS = 10000
export SYNTH_MOCK_LARGE_MEMORIES = 0

# The full-memory screening netlist makes the platform-specific full-adder
# extraction disproportionately expensive.  Leave adders to the ordinary ABC
# standard-cell mapping, as supported by ORFS designs that disable this map.
export ADDER_MAP_FILE :=

export CORE_UTILIZATION = 35
export TNS_END_PERCENT = 100
export LEC_CHECK = 0
