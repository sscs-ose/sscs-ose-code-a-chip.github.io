# One cocotb run; called from tests/Makefile with TOP, MOD, SRCS, BUILD,
# and optional PARAMS, EXTRA_TOP, VARIANT, VCD_FILE.
SIM ?= icarus
TOPLEVEL_LANG = verilog
VERILOG_SOURCES = $(SRCS)
COCOTB_TOPLEVEL = $(TOP)
COCOTB_TEST_MODULES = $(MOD)
SIM_BUILD = $(BUILD)
COCOTB_RESULTS_FILE = $(BUILD)/results.xml
COMPILE_ARGS += $(PARAMS) $(EXTRA_TOP)
export DCIM_VARIANT = $(VARIANT)

ifneq ($(VCD_FILE),)
COCOTB_PLUSARGS += +vcd=$(VCD_FILE)
export DCIM_VCD = 1
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
