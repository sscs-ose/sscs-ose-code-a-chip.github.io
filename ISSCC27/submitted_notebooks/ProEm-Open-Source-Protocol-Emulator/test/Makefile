# =============================================================================
# Project: ProEm - Open Source Protocol Emulator
# File: test/Makefile
# Type: Build script: cocotb test (RTL, or gate level with GATES=yes)
# Author: Paul Vincent Bezzina
# Language: Make
# Description:
# =============================================================================

# defaults
SIM ?= icarus
FST ?= -fst # Use more efficient FST format
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(PWD)/../src
PROJECT_SOURCES = primitives/frame_buffer.sv \
	primitives/host_fifo.sv \
	primitives/uart_rx.sv \
	primitives/uart_tx.sv \
	core/frame_chain/first_counter.sv \
	core/frame_chain/header_counter.sv \
	core/frame_chain/start_router.sv \
	core/frame_chain/main_counter.sv \
	core/frame_chain/end_counter.sv \
	core/frame_chain/watchdog.sv \
	core/frame_chain/branch_unit.sv \
	core/frame_chain/crc_unit.sv \
	core/frame_chain/frame_chain.sv \
	core/line_codec.sv \
	core/entry_dispatch.sv \
	core/control_unit.sv \
	core/return_path.sv \
	core/emulator_channel.sv \
	top/protocol_emulator.sv \
	top/tt_um_vertrex_star_proem.sv

ifneq ($(GATES),yes)

# RTL simulation:
SIM_BUILD				= sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

# Gate level simulation:
SIM_BUILD				= sim_build/gl
COMPILE_ARGS    += -DGL_TEST
COMPILE_ARGS    += -DFUNCTIONAL
COMPILE_ARGS    += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_io/verilog/sg13cmos5l_io.v
VERILOG_SOURCES += $(wildcard $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_udp.v)
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog/sg13cmos5l_stdcell.v

# this gets copied in by the GDS action workflow
VERILOG_SOURCES += $(PWD)/gate_level_netlist.v

endif

# Allow sharing configuration between design and testbench via `include`:
COMPILE_ARGS 		+= -I$(SRC_DIR)

# Include the testbench sources:
VERILOG_SOURCES += $(PWD)/tb.v
TOPLEVEL = tb

# List test modules to run, separated by commas and without the .py suffix:
COCOTB_TEST_MODULES = test

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim
