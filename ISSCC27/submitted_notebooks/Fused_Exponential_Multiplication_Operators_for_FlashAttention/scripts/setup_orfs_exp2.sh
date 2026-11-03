#!/usr/bin/env bash
# Fresh ExpMul lane design under a distinct DESIGN_NAME (avoids ORFS caching).
set -eu
F=$HOME/orfs-src/flow
RTL=$HOME/flashattn_expmul/rtl
SRC="$F/designs/src/fa_lane_e"
DES="$F/designs/nangate45/fa_lane_e"
rm -rf "$SRC" "$DES"
mkdir -p "$SRC" "$DES"
cp "$RTL/fp32_funcs.vh" "$RTL/fp32_mul.v" "$RTL/fp32_add.v" \
   "$RTL/exp_pwl.v" "$RTL/expmul.v" "$RTL/fa_lane.v" "$SRC"/
cat > "$SRC/fa_lane_e_top.v" <<'EOF'
module fa_lane_e_top (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    input  wire [31:0] x1,
    input  wire [31:0] x2,
    input  wire [31:0] v,
    output wire [31:0] o_q,
    output wire [31:0] l_q
);
  fa_lane #(.VARIANT(1), .MODE(1)) u_lane (
      .clk(clk), .rst_n(rst_n), .en(en),
      .x1(x1), .x2(x2), .v(v), .o_q(o_q), .l_q(l_q));
endmodule
EOF
cat > "$DES/config.mk" <<EOF
export DESIGN_NAME = fa_lane_e_top
export PLATFORM    = nangate45
export VERILOG_FILES = \$(sort \$(wildcard \$(DESIGN_HOME)/src/fa_lane_e/*.v))
export SDC_FILE      = \$(DESIGN_HOME)/nangate45/fa_lane_e/constraint.sdc
export CORE_UTILIZATION = 40
export PLACE_DENSITY    = 0.55
EOF
cat > "$DES/constraint.sdc" <<'EOF'
create_clock -name clk -period 20.0 [get_ports clk]
set_clock_uncertainty 0.05 [get_clocks clk]
set_input_delay  0.20 -clock clk [all_inputs]
set_output_delay 0.20 -clock clk [all_outputs]
set_input_transition 0.05 [all_inputs]
set_load 0.005 [all_outputs]
EOF
rm -rf "$F/results/nangate45/fa_lane_e_top" "$F/reports/nangate45/fa_lane_e_top" \
       "$F/logs/nangate45/fa_lane_e_top" "$F/objects/nangate45/fa_lane_e_top"
echo installed
