# ==============================
# Open-Source Flow Makefile
# Replaces VCS/DC/Innovus with: iverilog + yosys + gtkwave
# Project layout expected:
#   - ./designs/dut/*.circuit         GA output netlists (input to circuit_to_sv.py)
#   - ./designs/dut/*.sv              generated structural RTL (gf180 cells)
#   - ./designs/testbench/*.sv        testbench (must dump VCD)
#   - vsim/                           (simulation outputs)
# ==============================
SHELL := /bin/bash

##### GF180 library Verilog models (behavioral) #####
GF_STD_ROOT  := /home/ruichenq0623/NetlistGen/gate_type_extension/GA_notebook/src

# Collect common behavioral views (functional + UDPs/primitives)
GF_STD_MODELS := $(GF_STD_ROOT)/gf180mcu_fd_sc_mcu9t5v0.v \
				 $(GF_STD_ROOT)/primitives.v \

STD_CELLS := $(GF_STD_MODELS)

# Liberty for synthesis (pick a typical corner). Adjust if needed.
GF_LIB ?= $(GF_STD_ROOT)/gf180mcu_fd_sc_mcu9t5v0__tt_025C_3v30.lib

##### Sources #####
# NOTE:
# SIM_FILES is the generated structural RTL from circuit_to_sv.py.
# TOP should match *module name after sanitize*, not necessarily filename.
SIM_FILES            = ./code/synthesis/verilog/modules/mult_8bits.sv
TOP_LEVEL_TESTBENCH  = ./code/synthesis/verilog/testbench/mult_8bits_tb.sv
APPROX_NETLIST_TESTBENCH  = ./code/synthesis/verilog/testbench/approxMult_signed8x8_tb.sv

# SYNTHESIS
SYN_FILES			 = ./code/synthesis/verilog/modules/mult_8bits.sv
SYN_NETLIST		 	 = ./code/synthesis/syn/mult_8bits.syn.v
APPROX_NETLIST		 = ./code/genetic_algorithm/output/netlist_output.sv


TOP                  ?= mult_8bits

# Output / scratch dirs
VSIM_DIR        := code/synthesis/vsim

# RTL sim artifacts (pre-synthesis functional sim)
RTL_VVP         := $(VSIM_DIR)/rtl.vvp
RTL_VCD         ?= $(VSIM_DIR)/rtl.vcd
RTL_TXT_OUT     := $(VSIM_DIR)/rtl_sim_output.txt

GL_VVP          := $(VSIM_DIR)/gl.vvp
GL_VCD          ?= $(VSIM_DIR)/gl.vcd

# Tools
IVERILOG := iverilog
VVP      := vvp
YOSYS    := yosys
GTKWAVE  := gtkwave

# Icarus Verilog flags (SV 2012 support; add include dirs as needed)
IVFLAGS  := -g2012 -I../verilog/modules

.PHONY: all check_env map_netlist sim run_synth clean

# --------------------
# Environment checks
# --------------------

create_env:
	bash setup.sh

check_env:
	@if command -v $(IVERILOG) >/dev/null 2>&1; then \
		echo "[OK] iverilog found: $$(command -v $(IVERILOG))"; \
	else \
		echo "[ERR] iverilog not found in PATH"; \
		exit 1; \
	fi
	@if command -v $(YOSYS) >/dev/null 2>&1; then \
		echo "[OK] yosys found: $$(command -v $(YOSYS))"; \
	else \
		echo "[WARN] yosys not found in PATH"; \
	fi
	@if command -v sta >/dev/null 2>&1; then \
		echo "[OK] OpenSTA found: $$(command -v sta)"; \
	else \
		echo "[WARN] OpenSTA (sta) not found in PATH"; \
	fi

# --------------------
# Synthesis
# --------------------

# Use Yosys-abc to synthesis

run_synth:
	@echo "[SYN][OR] Generating $(SYN_FILES) via Yosys"
	cd code/synthesis && \
	LIB_SYN=$(GF_LIB) $(YOSYS) -ql syn/run_synth.log -c syn/run_synth.tcl
	@test -f $(SYN_FILES) || { echo "[ERR] Synthesis did not produce $(SYN_FILES)"; exit 1; }
	@echo "[SYN][OR] Done. Log: syn/run_synth.log"

# --------------------
# Simulation
# --------------------
goldenbrick_gen:
	python code/synthesis/goldenbrick/goldenbrick.py --width 8 --signed > code/synthesis/goldenbrick/goldenbrick.txt

sim_behavior:
	@if [ ! -d code/synthesis/vsim ]; then mkdir -p code/synthesis/vsim; fi
	$(IVERILOG) $(IVFLAGS) -o $(RTL_VVP) \
	  $(STD_CELLS) $(SIM_FILES) $(TOP_LEVEL_TESTBENCH) \
	  -D FUNCTIONAL \
	  -D VSIM_OUT=\"$(RTL_TXT_OUT)\" \
	  -D VCD_FILE=\"$(RTL_VCD)\"
	$(VVP) $(RTL_VVP)

check_behavior:
	@echo "[CHK] Comparing testbench output to golden brick..."
	if diff code/synthesis/goldenbrick/goldenbrick.txt $(VSIM_DIR)/rtl_sim_output.txt; then \
		echo "Outputs match! Behavioral model passed!"; \
	else \
		echo "Outputs differ!"; \
	fi

sim_synth:
	@echo "[GL] Compile gate-level with Icarus Verilog"
	@if [ ! -d code/synthesis/vsim ]; then mkdir -p code/synthesis/vsim; fi
	$(IVERILOG) $(IVFLAGS) -o $(GL_VVP) \
	  $(STD_CELLS) $(SYN_NETLIST) $(TOP_LEVEL_TESTBENCH) \
	  $(IVDEFS_GL) -D VSIM_OUT=\"$(VSIM_DIR)/gl_sim_output.txt\" -D VCD_FILE=\"$(GL_VCD)\"
	$(VVP) $(GL_VVP)

check_synth:
	@echo "[CHK] Comparing gate-level output to golden brick..."
	if diff code/synthesis/goldenbrick/goldenbrick.txt $(VSIM_DIR)/gl_sim_output.txt; then \
		echo "Outputs match! Gate-level netlist passed!"; \
	else \
		echo "Outputs differ!"; \
	fi

# --------------------
# Static Timing Analysis (OpenSTA)
# --------------------
STA ?= sta
sta:
	@echo "[STA] Running OpenSTA on synthesized netlist"
	@if [ ! -d code/synthesis/sta ]; then mkdir -p code/synthesis/sta; fi
	LIB_SYN=$(GF_LIB) $(STA) code/synthesis/sta/sta.tcl | tee code/synthesis/sta/sta.log
	@echo "[STA] Done. Reports in code/synthesis/sta/report_*.txt"

# --------------------
# Genetic Algorithm
# --------------------
compile_ga:
	cd code/genetic_algorithm && \
	g++ -std=c++17 -O3 -Wall -Wextra -I. \
	  file_io.cpp gate.cpp problem.cpp utils.cpp main.cpp \
	  -o main_exec

run_ga:
	cd code/genetic_algorithm && \
	./main_exec

map_netlist:
	python scripts/netlist_to_verilog.py \
	  --in ./code/genetic_algorithm/output/netlist_output.txt \
	  --out ./code/genetic_algorithm/output/netlist_output.sv \
	  --module-name approxMult_signed8x8

# --------------------
# Vefication
# --------------------
sim_approx_netlist:
	@if [ ! -d code/synthesis/vsim ]; then mkdir -p code/synthesis/vsim; fi
	$(IVERILOG) $(IVFLAGS) -o $(GL_VVP) \
	  $(STD_CELLS) $(APPROX_NETLIST) $(APPROX_NETLIST_TESTBENCH) \
	  $(IVDEFS_GL) -D VSIM_OUT=\"$(VSIM_DIR)/gl_sim_output.txt\" -D VCD_FILE=\"$(GL_VCD)\"
	$(VVP) $(GL_VVP)
	python scripts/extract_truth_table.py

check_lut:
	python scripts/error_eval.py code/genetic_algorithm/extracted_truth_table.txt --maxabs 16384

# --------------------
# All
# --------------------
all: run_synth check_behavior check_synth sta compile_ga run_ga map_netlist sim_approx_netlist

# --------------------
# Clean
# --------------------
clean:
	@rm -rf $(VSIM_DIR)/*.vvp $(VSIM_DIR)/*.vcd $(VSIM_DIR)/*.txt
	@echo "[CLEAN] Done."

