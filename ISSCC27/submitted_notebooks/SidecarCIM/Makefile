# SidecarCIM top-level commands
SHELL := /bin/bash
PY    := .venv/bin/python
FLOW  := $(shell [ -f .flowcmd ] && cut -d= -f2 .flowcmd || echo openlane)
export PATH := $(CURDIR)/.venv/bin:$(PATH)

.PHONY: check check-full golden sim sim-full lint clean

check: golden lint sim        # quicker (~10 min + flow)
	@echo "== all checks passed =="

check-full: golden lint sim-full   # full sign-off (~20 min + flow)
	@echo "== all full checks passed =="

golden:            # python reference self-test
	$(PY) python/golden.py

lint:              # verilog lint
	verilator --lint-only -Wall rtl/dcim_core.v rtl/icg.v
	verilator --lint-only -Wall -GUSE_LATCH=0 rtl/dcim_core.v rtl/icg.v
	verilator --lint-only -Wall -GUSE_LATCH=0 -GCLK_GATE=0 rtl/dcim_core.v rtl/icg.v
	verilator --lint-only -Wall rtl/mac_baseline.v rtl/icg.v
	verilator --lint-only -Wall rtl/dcim_8bit.v rtl/dcim_core.v rtl/icg.v
	verilator --lint-only -Wall -GUSE_LATCH=0 rtl/dcim_8bit.v rtl/dcim_core.v rtl/icg.v
	verilator --lint-only -Wall --top-module sidecarcim_top rtl/sidecarcim_top.v rtl/dcim_core.v rtl/sidecar.v rtl/icg.v
	verilator --lint-only -Wall --top-module sidecarcim_top -GUSE_LATCH=0 rtl/sidecarcim_top.v rtl/dcim_core.v rtl/sidecar.v rtl/icg.v
	verilator --lint-only -Wall --top-module sidecarcim_top -GUSE_LATCH=0 -GPARALLEL=1 rtl/sidecarcim_top.v rtl/dcim_core.v rtl/sidecar.v rtl/icg.v
	verilator --lint-only -Wall --top-module sidecarcim_top -GUSE_LATCH=0 -GPIPE_MERGE=1 -GSBITS=3 rtl/sidecarcim_top.v rtl/dcim_core.v rtl/sidecar.v rtl/icg.v

sim:               # quick cocotb run: 500 random cases per variant
	$(MAKE) -C tests DCIM_RANDOM_LIMIT=500

sim-full:          # full sign-off: all vectors, both variants
	$(MAKE) -C tests

clean:
	$(MAKE) -C tests clean || true
	rm -rf flow/*/runs
