# GlitchScope layout study: 16x16 NOR array multiplier, variant v0 (see bench/gen_arraymul.py)
export DESIGN_NAME     = mul16
export DESIGN_NICKNAME = mul16_v0
export PLATFORM        = sky130hd
export VERILOG_FILES   = $(GLITCHSCOPE_ROOT)/bench/layout/mul16_v0.v
export SDC_FILE        = $(GLITCHSCOPE_ROOT)/bench/layout/orfs/constraint.sdc
export CORE_UTILIZATION = 45
export PLACE_DENSITY    = 0.60
export TNS_END_PERCENT  = 100
