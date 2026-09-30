# ORFS design config shared by every design-space point.
# Selected by: make DESIGN_CONFIG=<this> CAC_VARIANT=<v> CAC_CLK_NS=<ns>
# SPDX-License-Identifier: Apache-2.0
CAC_ROOT ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
CAC_VARIANT ?= ntt_dp
CAC_CLK_NS ?= 20

export PLATFORM = sky130hd
export DESIGN_NICKNAME = cac_$(CAC_VARIANT)_$(subst .,p,$(CAC_CLK_NS))ns
export SYNTH_HDL_FRONTEND = slang
export SDC_FILE = $(CAC_ROOT)/flow/constraint.sdc
export CAC_CLK_NS

ifeq ($(CAC_VARIANT),ntt_dp)
  export DESIGN_NAME = kyber_ntt_engine
  export VERILOG_FILES = $(CAC_ROOT)/rtl/kyber_pkg.sv $(CAC_ROOT)/rtl/barrett_reduce.v \
                         $(CAC_ROOT)/rtl/kyber_ntt_engine.sv
else ifeq ($(CAC_VARIANT),ntt_sp)
  export DESIGN_NAME = kyber_ntt_engine
  export VERILOG_DEFINES = -D TRUSTEDGE_ASIC_SRAM
  export VERILOG_FILES = $(CAC_ROOT)/rtl/kyber_pkg.sv $(CAC_ROOT)/rtl/barrett_reduce.v \
                         $(CAC_ROOT)/rtl/te_sram_models.sv $(CAC_ROOT)/rtl/kyber_ntt_engine.sv
else ifeq ($(CAC_VARIANT),ntt_macro)
  # single-port NTT with the chip's OpenRAM macro as coefficient store (views in flow/macros/)
  export DESIGN_NAME = kyber_ntt_engine
  export VERILOG_DEFINES = -D TRUSTEDGE_ASIC_SRAM
  export VERILOG_FILES = $(CAC_ROOT)/rtl/kyber_pkg.sv $(CAC_ROOT)/rtl/barrett_reduce.v \
                         $(CAC_ROOT)/rtl/sram_macro_16x256.sv $(CAC_ROOT)/rtl/kyber_ntt_engine.sv
else ifeq ($(CAC_VARIANT),ntt_opt_pipe_macro)
  # the pipelined NTT redesign of Section 7 with the same OpenRAM macro as coefficient store
  export DESIGN_NAME = kyber_ntt_engine_opt
  export VERILOG_TOP_PARAMS = BARRETT_1C 1 PIPE_MUL 1 COEFF_W 12
  export VERILOG_FILES = $(CAC_ROOT)/rtl/kyber_pkg.sv $(CAC_ROOT)/rtl/barrett_reduce.v \
                         $(CAC_ROOT)/rtl/barrett_reduce_1c.v $(CAC_ROOT)/rtl/sram_macro_16x256.sv \
                         $(CAC_ROOT)/rtl/sram_macro_16x256_opt.sv $(CAC_ROOT)/rtl/kyber_ntt_engine_opt.sv
else ifeq ($(CAC_VARIANT),keccak_r1)
  export DESIGN_NAME = keccak_lane_wrapper
  export VERILOG_TOP_PARAMS = SERIAL_ROUND 0
  export VERILOG_FILES = $(CAC_ROOT)/rtl/keccak_f1600_iter.sv $(CAC_ROOT)/rtl/keccak_lane_wrapper.sv
else ifeq ($(CAC_VARIANT),keccak_s7)
  export DESIGN_NAME = keccak_lane_wrapper
  export VERILOG_TOP_PARAMS = SERIAL_ROUND 1
  export VERILOG_FILES = $(CAC_ROOT)/rtl/keccak_f1600_iter.sv $(CAC_ROOT)/rtl/keccak_lane_wrapper.sv
else ifneq ($(filter ntt_opt_b1_w12 ntt_opt_pipe_w12,$(CAC_VARIANT)),)
  # NTT redesign of Section 7 (single-port store, see rtl/kyber_ntt_engine_opt.sv)
  export DESIGN_NAME = kyber_ntt_engine_opt
  ifeq ($(CAC_VARIANT),ntt_opt_b1_w12)
    export VERILOG_TOP_PARAMS = BARRETT_1C 1 PIPE_MUL 0 COEFF_W 12
  else
    export VERILOG_TOP_PARAMS = BARRETT_1C 1 PIPE_MUL 1 COEFF_W 12
  endif
  export VERILOG_FILES = $(CAC_ROOT)/rtl/kyber_pkg.sv $(CAC_ROOT)/rtl/barrett_reduce.v \
                         $(CAC_ROOT)/rtl/barrett_reduce_1c.v $(CAC_ROOT)/rtl/te_sram_models.sv \
                         $(CAC_ROOT)/rtl/kyber_ntt_engine_opt.sv
else
  $(error unknown CAC_VARIANT $(CAC_VARIANT))
endif

# views and physical settings shared by the two OpenRAM-macro points
ifneq ($(filter ntt_macro ntt_opt_pipe_macro,$(CAC_VARIANT)),)
  export ADDITIONAL_LEFS = $(CAC_ROOT)/flow/macros/sky130_sram_1rw_16x256_wpr8.lef
  export ADDITIONAL_LIBS = $(CAC_ROOT)/flow/macros/sky130_sram_1rw_16x256_wpr8_TT_1p8V_25C.lib
  CAC_SRAM_GDS ?= /opt/eda/openram-smoke/sky130_sram_1rw_16x256_wpr8_vdd_via_column_mux_candidate/sky130_sram_1rw_16x256_wpr8.gds
  export ADDITIONAL_GDS = $(CAC_SRAM_GDS)
  export PRE_PDN_TCL = $(CAC_ROOT)/flow/pre_pdn_sram.tcl
  # the 473 um wide macro plus the default 40 um halo would not fit the 45 %-utilization core
  export MACRO_PLACE_HALO ?= 10 10
  # upsize the minimum-size wire buffers that the post-route repair puts on the macro's address pins
  export POST_GLOBAL_ROUTE_TCL = $(CAC_ROOT)/flow/post_grt_macro_pins.tcl
endif

# Ten antenna-repair passes (ORFS default: 5); needed for the dense Keccak blocks.
export MAX_REPAIR_ANTENNAS_ITER_DRT ?= 10
export MAX_REPAIR_ANTENNAS_ITER_GRT ?= 10

export CORE_UTILIZATION ?= 45
export PLACE_DENSITY_LB_ADDON ?= 0.20
export TNS_END_PERCENT = 100
