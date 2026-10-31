# SidecarCIM cocotb tests (Icarus). Each target runs one cocotb sub-make
# (tests/cocotb.mk) with its own build dir; results in sim_build/<name>/results.xml.
# Testbenches: core_tb.py (dcim_core, dcim_8bit, mac_baseline), top_tb.py (sidecarcim_top).
# Targets run one after another (do not use -j: memory is shared with the flow).
#
#   make              = all targets below except clean
#   make dcim_latch   rtl/dcim_core.v, USE_LATCH=1 (default storage), all tests
#   make dcim_ff      rtl/dcim_core.v, USE_LATCH=0 (flip-flop storage), all tests
#   make vcd          100 real-layer cases, dcim_core USE_LATCH=1 -> results/vcd/dcim_core.vcd
#   make mac          rtl/mac_baseline.v, all tests (random set: MAC_RANDOM_LIMIT)
#   make vcd_mac      100 real-layer cases, mac_baseline -> results/vcd/mac_baseline.vcd
#   make dcim8_latch  rtl/dcim_8bit.v (W8A8), USE_LATCH=1, dense8_* vectors + protocol
#   make dcim8_ff     rtl/dcim_8bit.v (W8A8), USE_LATCH=0, dense8_* vectors + protocol
#   make vcd8         100 dense8 real-layer cases, dcim_8bit USE_LATCH=1 -> results/vcd/dcim_8bit.vcd
#   make top_p0       rtl/sidecarcim_top.v K=2 PARALLEL=0 USE_LATCH=1, sidecar_* vectors + protocol
#   make top_p1       rtl/sidecarcim_top.v K=2 PARALLEL=1 USE_LATCH=1, sidecar_* vectors + protocol
#   make top_ff       rtl/sidecarcim_top.v K=2 PARALLEL=0 USE_LATCH=0 (primary), full vectors + protocol
#   make top_p1_ff    rtl/sidecarcim_top.v K=2 PARALLEL=1 USE_LATCH=0, full vectors + protocol
#   make vcd_top      100 sidecar real-layer cases, PARALLEL=0 USE_LATCH=1 -> results/vcd/sidecarcim_top.vcd
#   make vcd_top_ff_p0 / vcd_top_ff_p1   same 100 cases, USE_LATCH=0, PARALLEL=0 / 1
#                     -> results/vcd/sidecarcim_top_ff_p0.vcd / sidecarcim_top_ff_p1.vcd
#   make top_ff_pipe  rtl/sidecarcim_top.v K=2 PARALLEL=0 USE_LATCH=0 PIPE_MERGE=1 (output register
#                     after the merge, start->valid = ABITS+1), full vectors + protocol;
#                     top_tb takes the latency from TOP_PIPE_MERGE (set here with the -P)
#   make vcd_top_ff_pipe   same 100 cases as vcd_top_ff_p0 on that build
#                     -> results/vcd/sidecarcim_top_ff_pipe.vcd
#   make top_ff_pipe_s3   top_ff_pipe + SBITS=3 (3-bit S 0..7, YTW 22, y 176 bits; the final
#                     build), sidecar_s3_* vectors + protocol; top_tb takes the S width
#                     from TOP_SBITS and the vectors from TOP_VEC_PREFIX (set here with the -P)
#   make vcd_top_ff_pipe_s3   first 100 sidecar_s3 real-layer cases on that build
#                     -> results/vcd/sidecarcim_top_ff_pipe_s3.vcd
#   make dcim_w8a4_ff / dcim_w6a4_ff   rtl/dcim_core.v WBITS=8 / 6, ABITS=4, USE_LATCH=0,
#                     w8a4_* / w6a4_* vectors + protocol + clock-gating directed
#   make vcd_w8a4_ff / vcd_w6a4_ff     first 100 real-layer cases of those builds
#                     -> results/vcd/dcim_w8a4_ff.vcd / dcim_w6a4_ff.vcd
#   make dcim_w7a4_ff / dcim_w4a8_ff   same, WBITS=7 ABITS=4 / WBITS=4 ABITS=8 (8 cycles,
#                     x_in 256 b), w7a4_* / w4a8_* vectors + protocol + clock-gating directed
#   make vcd_w7a4_ff / vcd_w4a8_ff     -> results/vcd/dcim_w7a4_ff.vcd / dcim_w4a8_ff.vcd
#   make clean
# DCIM_RANDOM_LIMIT=N runs only the first N random cases (all targets).
# MAC_RANDOM_LIMIT=N overrides it for `mac` (default: full 10,000).
# CLK_GATE=0|1: storage clock gating of the flip-flop targets (dcim_ff, mac, vcd_mac,
#   dcim8_ff, top_ff, top_p1_ff, vcd_top_ff_p0/p1, top_ff_pipe, vcd_top_ff_pipe, top_ff_pipe_s3,
#   vcd_top_ff_pipe_s3, dcim_w?a?_ff, vcd_w?a?_ff); default 1 = RTL default.

SUB  = $(MAKE) --no-print-directory -f $(CURDIR)/cocotb.mk
RTL  = $(CURDIR)/../rtl
VCDD = $(abspath $(CURDIR)/../results/vcd)
MAC_RANDOM_LIMIT ?=
MAC_LIM = $(or $(MAC_RANDOM_LIMIT),$(DCIM_RANDOM_LIMIT))
# rtl/icg.v (clock gate) is in every source list except counter; latch builds do not use it.
CLK_GATE ?= 1
ICG  = $(RTL)/icg.v
TOPSRC = "$(RTL)/dcim_core.v $(RTL)/sidecar.v $(RTL)/sidecarcim_top.v $(ICG)"
D8SRC  = "$(RTL)/dcim_core.v $(RTL)/dcim_8bit.v $(ICG)"
TOPARG = TOP=sidecarcim_top MOD=test_sidecarcim_top SIDECAR_K=2

.PHONY: all dcim_latch dcim_ff vcd mac vcd_mac dcim8_latch dcim8_ff vcd8 \
        top_p0 top_p1 top_ff top_p1_ff vcd_top vcd_top_ff_p0 vcd_top_ff_p1 \
        top_ff_pipe vcd_top_ff_pipe top_ff_pipe_s3 vcd_top_ff_pipe_s3 \
        dcim_w8a4_ff dcim_w6a4_ff vcd_w8a4_ff vcd_w6a4_ff \
        dcim_w7a4_ff dcim_w4a8_ff vcd_w7a4_ff vcd_w4a8_ff clean

all: dcim_latch dcim_ff vcd mac vcd_mac dcim8_latch dcim8_ff vcd8 \
     top_p0 top_p1 top_ff top_p1_ff vcd_top vcd_top_ff_p0 vcd_top_ff_p1 \
     top_ff_pipe vcd_top_ff_pipe top_ff_pipe_s3 vcd_top_ff_pipe_s3 \
     dcim_w8a4_ff dcim_w6a4_ff vcd_w8a4_ff vcd_w6a4_ff \
     dcim_w7a4_ff dcim_w4a8_ff vcd_w7a4_ff vcd_w4a8_ff

# Dense comparison points: dcim_core at (WBITS, ABITS), primary build (FF, clock-gated rows).
# The same width goes to -P and to core_tb (DCIM_WBITS/DCIM_ABITS); setup() checks both.
# $(call wpar,W,A) = parameter overrides, $(call wenv,W,A) = testbench env.
wpar = "-Pdcim_core.USE_LATCH=0 -Pdcim_core.CLK_GATE=$(CLK_GATE) -Pdcim_core.WBITS=$(1) -Pdcim_core.ABITS=$(2)"
wenv = DCIM_WBITS=$(1) DCIM_ABITS=$(2) DCIM_VEC_PREFIX=w$(1)a$(2)_ VARIANT=W$(1)A$(2)_USE_LATCH=0
WSRC  = "$(RTL)/dcim_core.v $(ICG)"
WVSRC = "$(RTL)/dcim_core.v $(ICG) $(CURDIR)/vcd_dump.v"

dcim_w8a4_ff:
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WSRC) \
	  BUILD=sim_build/dcim_w8a4_ff PARAMS=$(call wpar,8,4) $(call wenv,8,4)

dcim_w6a4_ff:
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WSRC) \
	  BUILD=sim_build/dcim_w6a4_ff PARAMS=$(call wpar,6,4) $(call wenv,6,4)

vcd_w8a4_ff:
	mkdir -p $(VCDD)
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WVSRC) \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=dcim_core" \
	  BUILD=sim_build/dcim_w8a4_vcd PARAMS=$(call wpar,8,4) $(call wenv,8,4) \
	  VCD_FILE=$(VCDD)/dcim_w8a4_ff.vcd

vcd_w6a4_ff:
	mkdir -p $(VCDD)
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WVSRC) \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=dcim_core" \
	  BUILD=sim_build/dcim_w6a4_vcd PARAMS=$(call wpar,6,4) $(call wenv,6,4) \
	  VCD_FILE=$(VCDD)/dcim_w6a4_ff.vcd

# W7A4 (start->valid 4 edges) and W4A8 (8 edges, x_in 256 bits); same recipe as above.
dcim_w7a4_ff:
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WSRC) \
	  BUILD=sim_build/dcim_w7a4_ff PARAMS=$(call wpar,7,4) $(call wenv,7,4)

dcim_w4a8_ff:
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WSRC) \
	  BUILD=sim_build/dcim_w4a8_ff PARAMS=$(call wpar,4,8) $(call wenv,4,8)

vcd_w7a4_ff:
	mkdir -p $(VCDD)
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WVSRC) \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=dcim_core" \
	  BUILD=sim_build/dcim_w7a4_vcd PARAMS=$(call wpar,7,4) $(call wenv,7,4) \
	  VCD_FILE=$(VCDD)/dcim_w7a4_ff.vcd

vcd_w4a8_ff:
	mkdir -p $(VCDD)
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS=$(WVSRC) \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=dcim_core" \
	  BUILD=sim_build/dcim_w4a8_vcd PARAMS=$(call wpar,4,8) $(call wenv,4,8) \
	  VCD_FILE=$(VCDD)/dcim_w4a8_ff.vcd

dcim_latch:
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS="$(RTL)/dcim_core.v $(ICG)" \
	  BUILD=sim_build/dcim_latch PARAMS=-Pdcim_core.USE_LATCH=1 VARIANT=USE_LATCH=1

dcim_ff:
	$(SUB) TOP=dcim_core MOD=test_dcim_core SRCS="$(RTL)/dcim_core.v $(ICG)" \
	  BUILD=sim_build/dcim_ff PARAMS="-Pdcim_core.USE_LATCH=0 -Pdcim_core.CLK_GATE=$(CLK_GATE)" VARIANT=USE_LATCH=0

vcd:
	mkdir -p $(VCDD)
	$(SUB) TOP=dcim_core MOD=test_dcim_core \
	  SRCS="$(RTL)/dcim_core.v $(ICG) $(CURDIR)/vcd_dump.v" \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=dcim_core" \
	  BUILD=sim_build/dcim_vcd PARAMS=-Pdcim_core.USE_LATCH=1 VARIANT=USE_LATCH=1 \
	  VCD_FILE=$(VCDD)/dcim_core.vcd

mac:
	$(SUB) TOP=mac_baseline MOD=test_mac_baseline SRCS="$(RTL)/mac_baseline.v $(ICG)" \
	  BUILD=sim_build/mac VARIANT=mac PARAMS=-Pmac_baseline.CLK_GATE=$(CLK_GATE) DCIM_RANDOM_LIMIT=$(MAC_LIM)

vcd_mac:
	mkdir -p $(VCDD)
	$(SUB) TOP=mac_baseline MOD=test_mac_baseline \
	  SRCS="$(RTL)/mac_baseline.v $(ICG) $(CURDIR)/vcd_dump.v" \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=mac_baseline" \
	  BUILD=sim_build/mac_vcd VARIANT=mac PARAMS=-Pmac_baseline.CLK_GATE=$(CLK_GATE) VCD_FILE=$(VCDD)/mac_baseline.vcd

dcim8_latch:
	$(SUB) TOP=dcim_8bit MOD=test_dcim_8bit SRCS=$(D8SRC) \
	  BUILD=sim_build/dcim8_latch PARAMS=-Pdcim_8bit.USE_LATCH=1 VARIANT=W8A8_USE_LATCH=1

dcim8_ff:
	$(SUB) TOP=dcim_8bit MOD=test_dcim_8bit SRCS=$(D8SRC) \
	  BUILD=sim_build/dcim8_ff PARAMS="-Pdcim_8bit.USE_LATCH=0 -Pdcim_8bit.CLK_GATE=$(CLK_GATE)" VARIANT=W8A8_USE_LATCH=0

vcd8:
	mkdir -p $(VCDD)
	$(SUB) TOP=dcim_8bit MOD=test_dcim_8bit \
	  SRCS="$(RTL)/dcim_core.v $(RTL)/dcim_8bit.v $(ICG) $(CURDIR)/vcd_dump.v" \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=dcim_8bit" \
	  BUILD=sim_build/dcim8_vcd PARAMS=-Pdcim_8bit.USE_LATCH=1 VARIANT=W8A8_USE_LATCH=1 \
	  VCD_FILE=$(VCDD)/dcim_8bit.vcd

top_p0:
	$(SUB) $(TOPARG) SRCS=$(TOPSRC) BUILD=sim_build/top_p0 \
	  PARAMS="-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=0 -Psidecarcim_top.USE_LATCH=1" \
	  VARIANT=K2_P0_LATCH1

top_p1:
	$(SUB) $(TOPARG) SRCS=$(TOPSRC) BUILD=sim_build/top_p1 \
	  PARAMS="-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=1 -Psidecarcim_top.USE_LATCH=1" \
	  VARIANT=K2_P1_LATCH1

top_ff:
	$(SUB) $(TOPARG) SRCS=$(TOPSRC) BUILD=sim_build/top_ff \
	  PARAMS="-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=0 -Psidecarcim_top.USE_LATCH=0 -Psidecarcim_top.CLK_GATE=$(CLK_GATE)" \
	  VARIANT=K2_P0_LATCH0

top_p1_ff:
	$(SUB) $(TOPARG) SRCS=$(TOPSRC) BUILD=sim_build/top_p1_ff \
	  PARAMS="-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=1 -Psidecarcim_top.USE_LATCH=0 -Psidecarcim_top.CLK_GATE=$(CLK_GATE)" \
	  VARIANT=K2_P1_LATCH0

TOPVSRC = "$(RTL)/dcim_core.v $(RTL)/sidecar.v $(RTL)/sidecarcim_top.v $(ICG) $(CURDIR)/vcd_dump.v"
TOPVARG = $(TOPARG) SRCS=$(TOPVSRC) EXTRA_TOP="-s vcd_dump -DVCD_TOP=sidecarcim_top"

vcd_top_ff_p0:
	mkdir -p $(VCDD)
	$(SUB) $(TOPVARG) BUILD=sim_build/top_vcd_ff_p0 \
	  PARAMS="-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=0 -Psidecarcim_top.USE_LATCH=0 -Psidecarcim_top.CLK_GATE=$(CLK_GATE)" \
	  VARIANT=K2_P0_LATCH0 VCD_FILE=$(VCDD)/sidecarcim_top_ff_p0.vcd

vcd_top_ff_p1:
	mkdir -p $(VCDD)
	$(SUB) $(TOPVARG) BUILD=sim_build/top_vcd_ff_p1 \
	  PARAMS="-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=1 -Psidecarcim_top.USE_LATCH=0 -Psidecarcim_top.CLK_GATE=$(CLK_GATE)" \
	  VARIANT=K2_P1_LATCH0 VCD_FILE=$(VCDD)/sidecarcim_top_ff_p1.vcd

# PIPE_MERGE=1 build (register after the merge): the same number goes to -P and to top_tb
# (TOP_PIPE_MERGE, latency ABITS+1); setup() checks the DUT parameter against it.
PIPEPAR = "-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=0 -Psidecarcim_top.USE_LATCH=0 -Psidecarcim_top.CLK_GATE=$(CLK_GATE) -Psidecarcim_top.PIPE_MERGE=1"

top_ff_pipe:
	$(SUB) $(TOPARG) SRCS=$(TOPSRC) BUILD=sim_build/top_ff_pipe PARAMS=$(PIPEPAR) \
	  VARIANT=K2_P0_LATCH0_PIPE1 TOP_PIPE_MERGE=1

vcd_top_ff_pipe:
	mkdir -p $(VCDD)
	$(SUB) $(TOPVARG) BUILD=sim_build/top_vcd_ff_pipe PARAMS=$(PIPEPAR) \
	  VARIANT=K2_P0_LATCH0_PIPE1 TOP_PIPE_MERGE=1 VCD_FILE=$(VCDD)/sidecarcim_top_ff_pipe.vcd

# SBITS=3 final build (= flow/sidecarcim_top_ff_pipe_s3): the same SBITS goes to -P and to
# top_tb (TOP_SBITS: S width, golden sbits, YTW); setup() checks the DUT parameter against it.
S3PAR = "-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=0 -Psidecarcim_top.USE_LATCH=0 -Psidecarcim_top.CLK_GATE=$(CLK_GATE) -Psidecarcim_top.PIPE_MERGE=1 -Psidecarcim_top.SBITS=3"
S3ENV = VARIANT=K2_P0_LATCH0_PIPE1_S3 TOP_PIPE_MERGE=1 TOP_SBITS=3 TOP_VEC_PREFIX=sidecar_s3_

top_ff_pipe_s3:
	$(SUB) $(TOPARG) SRCS=$(TOPSRC) BUILD=sim_build/top_ff_pipe_s3 PARAMS=$(S3PAR) $(S3ENV)

vcd_top_ff_pipe_s3:
	mkdir -p $(VCDD)
	$(SUB) $(TOPVARG) BUILD=sim_build/top_vcd_ff_pipe_s3 PARAMS=$(S3PAR) $(S3ENV) \
	  VCD_FILE=$(VCDD)/sidecarcim_top_ff_pipe_s3.vcd

vcd_top:
	mkdir -p $(VCDD)
	$(SUB) $(TOPARG) \
	  SRCS="$(RTL)/dcim_core.v $(RTL)/sidecar.v $(RTL)/sidecarcim_top.v $(ICG) $(CURDIR)/vcd_dump.v" \
	  EXTRA_TOP="-s vcd_dump -DVCD_TOP=sidecarcim_top" BUILD=sim_build/top_vcd \
	  PARAMS="-Psidecarcim_top.K=2 -Psidecarcim_top.PARALLEL=0 -Psidecarcim_top.USE_LATCH=1" \
	  VARIANT=K2_P0_LATCH1 VCD_FILE=$(VCDD)/sidecarcim_top.vcd

clean:
	rm -rf sim_build results_*.xml results.xml __pycache__
