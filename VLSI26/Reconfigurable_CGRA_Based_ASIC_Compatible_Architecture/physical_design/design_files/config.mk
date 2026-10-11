# ==============================================================
# DESIGN CONFIGURATION
# ==============================================================
export DESIGN_NAME     = verification_fabric_top
export DESIGN_NICKNAME = cgra
export PLATFORM        = sky130hd

# ==============================================================
# INPUT FILES
# ==============================================================
export VERILOG_FILES = designs/sky130hd/cgra/verification_fabric_top.v
export SDC_FILE      = designs/sky130hd/cgra/constraint.sdc

# ==============================================================
# CLOCK
# ==============================================================
export CLOCK_PORT   = clk
export CLOCK_PERIOD = 10

# ==============================================================
# SYNTHESIS STRATEGY & OPTIONS
# ==============================================================
export SYNTH_STRATEGY = "AREA 2"
export SYNTH_NO_FLAT  = 1
export SYNTH_ARGS     = -noshare -noalumacc -nordff
export ABC_AREA       = 1

# ==============================================================
# FLOORPLAN
# Increased die from 800x2700 to 800x4000
# More routing space = less congestion = fewer DRC violations
# Router was crashing at 2.4GB due to 4795 violations
# ==============================================================
export DIE_AREA           = 0 0 800 4000
export CORE_AREA          = 10 10 790 3990
export IO_PLACER_DISTANCE = 1

# ==============================================================
# PLACEMENT
# Reduced density from 0.60 to 0.40
# Less dense = more routing channels between cells
# ==============================================================
export PL_TARGET_DENSITY      = 0.40
export PLACE_DENSITY          = 0.40
export PL_TIMING_DRIVEN       = 0
export GPL_ROUTABILITY_DRIVEN = 0
export GPL_PADDING            = 0

# ==============================================================
# CTS
# ==============================================================
export SKIP_CTS_REPAIR_TIMING = 1
export TNS_END_PERCENT        = 0

# ==============================================================
# ROUTING
# Threads reduced to 4 to save memory
# Layer adjustment 0.5 spreads routes across more layers
# Limited iterations to prevent infinite loops
# ==============================================================
export THREADS                  = 4
export ROUTING_LAYER_ADJUSTMENT = 0.5
export DETAILED_ROUTE_ARGS      = -droute_end_iter 10
export GLOBAL_ROUTE_ARGS        = -congestion_iterations 20

# ==============================================================
# TIMING / OPTIMIZATION
# ==============================================================
export MAX_FANOUT_CONSTRAINT = 6

# ==============================================================
# POWER NETS
# ==============================================================
export VDD_NETS = VPWR
export GND_NETS = VGND
