# implementation.constraints@1 -- draft; only the platform may freeze after human confirmation.
# spec_revision_id: specir:9e2e4dc1c876bda98921b4d26ccea97cad53efc9e5064966c16cbc6a8f2ecec5
# Decision Artifact IDs: artifact-5fdbf302d11041e2a6375c73a5d03467, authorized-physical-reference, artifact-df6fa9be51d7464a87f298380738ee10, authorized-valid-token-correction
# Current 27 reaffirmed answers and historical 27 answers are cited in implementation.constraints.json.
# Verified TT Liberty units: ns and pF. Values are approved engineering assumptions.
current_design nebula_cpu_npu_top
create_clock -name nebula_clock -period 100 -waveform {0 50} [get_ports {clk}]
set_clock_latency -source -early 0 [get_clocks nebula_clock]
set_clock_latency -source -late 0 [get_clocks nebula_clock]
set_clock_uncertainty -setup 0.1 [get_clocks nebula_clock]
set_clock_uncertainty -hold 0.1 [get_clocks nebula_clock]
set_clock_transition -rise 0.05 [get_clocks nebula_clock]
set_clock_transition -fall 0.05 [get_clocks nebula_clock]

# Physical rising-edge reference; approved external launch/capture skew is zero.
set_input_delay -clock nebula_clock -min 0.5 [get_ports {imem_rdata[*] dmem_req_ready dmem_rsp_valid dmem_rsp_rdata[*] dmem_rsp_err}]
set_input_delay -clock nebula_clock -max 0.5 [get_ports {imem_rdata[*] dmem_req_ready dmem_rsp_valid dmem_rsp_rdata[*] dmem_rsp_err}]
set_output_delay -clock nebula_clock -min 0.5 [get_ports {imem_valid imem_addr[*] dmem_req_valid dmem_req_write dmem_req_addr[*] dmem_req_wdata[*] dmem_req_wstrb[*] dmem_rsp_ready commit_valid commit_pc[*] commit_insn[*] commit_rd[*] commit_wdata[*] commit_mem_addr[*] commit_mem_wstrb[*] commit_mem_wdata[*] trap_valid trap_pc[*] trap_cause[*] trap_tval[*]}]
set_output_delay -clock nebula_clock -max 0.5 [get_ports {imem_valid imem_addr[*] dmem_req_valid dmem_req_write dmem_req_addr[*] dmem_req_wdata[*] dmem_req_wstrb[*] dmem_rsp_ready commit_valid commit_pc[*] commit_insn[*] commit_rd[*] commit_wdata[*] commit_mem_addr[*] commit_mem_wstrb[*] commit_mem_wdata[*] trap_valid trap_pc[*] trap_cause[*] trap_tval[*]}]

# Active-low reset release rises 49..51 ns after clk rise, including +/-1 ns skew.
# Assertion phase is unrestricted; no invented falling-edge arrival or false path.
set_input_delay -clock nebula_clock -rise -min 49 [get_ports {rst_n}]
set_input_delay -clock nebula_clock -rise -max 51 [get_ports {rst_n}]
# Require external reset low pulse >=200 ns and joint external-memory reset.
# OpenSTA set_min_pulse_width rejects a top-level Port: validate this environment
# waveform obligation externally; retain library pulse-width/recovery/removal checks.

set_input_transition -rise 0.05 [get_ports {rst_n imem_rdata[*] dmem_req_ready dmem_rsp_valid dmem_rsp_rdata[*] dmem_rsp_err}]
set_input_transition -fall 0.05 [get_ports {rst_n imem_rdata[*] dmem_req_ready dmem_rsp_valid dmem_rsp_rdata[*] dmem_rsp_err}]
set_load -pin_load 0.005 [get_ports {imem_valid imem_addr[*] dmem_req_valid dmem_req_write dmem_req_addr[*] dmem_req_wdata[*] dmem_req_wstrb[*] dmem_rsp_ready commit_valid commit_pc[*] commit_insn[*] commit_rd[*] commit_wdata[*] commit_mem_addr[*] commit_mem_wstrb[*] commit_mem_wdata[*] trap_valid trap_pc[*] trap_cause[*] trap_tval[*]}]
set_timing_derate -early 1.0
set_timing_derate -late 1.0

# Enforce library slew/capacitance limits and available fanout limits; report structural
# fanout where the library supplies no ceiling, without inventing a hard limit.
# No functional/observer/reset false paths, multicycle, case analysis or dont_touch.
# After CTS, run set_propagated_clock [get_clocks nebula_clock] AFTER this SDC.
# Keep the 0.1 ns setup/hold margins; do not double-count internal CTS delay.
# Extract using manifest-bound RC rules with early/late R and C scales=1.0.
