#!/usr/bin/env bash
# Install bf16 lane designs (base / exp) into ORFS.
set -eu
F=$HOME/orfs-src/flow
RTL=$HOME/flashattn_expmul/rtl
for V in b e; do
  if [ "$V" = "b" ]; then PP=".VARIANT(0)"; else PP=".VARIANT(1)"; fi
  SRC="$F/designs/src/fa_bf16_$V"
  DES="$F/designs/nangate45/fa_bf16_$V"
  rm -rf "$SRC" "$DES"
  mkdir -p "$SRC" "$DES"
  cp "$RTL/bf16_funcs.vh" "$RTL/bf16_ops.v" "$RTL/fa_lane_bf16.v" "$SRC"/
  cat > "$SRC/fa_bf16_${V}_top.v" <<EOF
module fa_bf16_${V}_top (
    input  wire clk,
    input  wire rst_n,
    input  wire en,
    input  wire [15:0] x1,
    input  wire [15:0] x2,
    input  wire [15:0] v,
    output wire [15:0] o_q,
    output wire [15:0] l_q
);
  fa_lane_bf16 #($PP, .MODE(1)) u_lane (
      .clk(clk), .rst_n(rst_n), .en(en),
      .x1(x1), .x2(x2), .v(v), .o_q(o_q), .l_q(l_q));
endmodule
EOF
  cat > "$DES/config.mk" <<EOF
export DESIGN_NAME = fa_bf16_${V}_top
export PLATFORM    = nangate45
export VERILOG_FILES = \$(sort \$(wildcard \$(DESIGN_HOME)/src/fa_bf16_$V/*.v))
export SDC_FILE      = \$(DESIGN_HOME)/nangate45/fa_bf16_$V/constraint.sdc
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
  rm -rf "$F/results/nangate45/fa_bf16_${V}_top" "$F/reports/nangate45/fa_bf16_${V}_top" \
         "$F/logs/nangate45/fa_bf16_${V}_top" "$F/objects/nangate45/fa_bf16_${V}_top"
  echo "installed $DES"
done
