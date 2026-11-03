#!/usr/bin/env bash
# ============================================================================
#  setup_orfs.sh -- install the fa_kernel designs into OpenROAD-flow-scripts
#  Creates d=16 baseline / expmul variants (nangate45, 500 MHz target).
# ============================================================================
set -eu
RTL=$HOME/flashattn_expmul/rtl
F=$HOME/orfs-src/flow

for VAR in base exp; do
  if [ "$VAR" = "base" ]; then PP=".VARIANT(0)"; else PP=".VARIANT(1)"; fi
  SRC="$F/designs/src/fa_d16_$VAR"
  DES="$F/designs/nangate45/fa_d16_$VAR"
  mkdir -p "$SRC" "$DES"
  cp "$RTL/fp32_funcs.vh" "$RTL/fp32_mul.v" "$RTL/fp32_add.v" \
     "$RTL/exp_pwl.v" "$RTL/expmul.v" "$RTL/fa_kernel.v" "$SRC/"

  cat > "$SRC/fa_top.v" <<EOF
module fa_top (
    input  wire clk,
    input  wire rst_n,
    input  wire init,
    input  wire valid_in,
    input  wire [511:0] q_flat,
    input  wire [511:0] k_flat,
    input  wire [511:0] v_flat,
    output wire [511:0] o_flat,
    output wire [31:0] l_out,
    output wire [31:0] m_out,
    output wire [511:0] attn_flat
);
  fa_kernel #(.D(16), $PP, .MODE(1)) u_kernel (
      .clk(clk), .rst_n(rst_n), .init(init), .valid_in(valid_in),
      .q_flat(q_flat), .k_flat(k_flat), .v_flat(v_flat),
      .o_flat(o_flat), .l_out(l_out), .m_out(m_out), .attn_flat(attn_flat));
endmodule
EOF

  cat > "$DES/config.mk" <<EOF
export DESIGN_NAME = fa_top
export PLATFORM    = nangate45

export VERILOG_FILES = \$(sort \$(wildcard \$(DESIGN_HOME)/src/fa_d16_$VAR/*.v))
export SDC_FILE      = \$(DESIGN_HOME)/nangate45/fa_d16_$VAR/constraint.sdc

export CORE_UTILIZATION = 40
export PLACE_DENSITY    = 0.55
EOF

  cat > "$DES/constraint.sdc" <<'EOF'
current_design fa_top
set clk_name  clk
set clk_port_name clk
set clk_period 2.0
create_clock -name $clk_name -period $clk_period [get_ports $clk_port_name]
set_clock_uncertainty 0.05 [get_clocks $clk_name]
set_input_delay  0.20 -clock $clk_name [remove_from_collection [all_inputs] [get_ports $clk_port_name]]
set_output_delay 0.20 -clock $clk_name [all_outputs]
set_input_transition 0.05 [all_inputs]
set_load 0.005 [all_outputs]
EOF
  echo "installed $DES"
done
