if {[catch {
read_liberty {/home/asic03/project/user37/CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib}
read_lef {/home/asic03/project/user37/CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef}
read_lef {/home/asic03/project/user37/CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef}
read_verilog {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/evidence/measurement/6_final.sta.v}
link_design nebula_cpu_npu_top
read_sdc {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/evidence/orfs-work/results/sky130hd/nebula_cpu_npu_top/nebula/6_final.sdc}
set_propagated_clock [all_clocks]
read_spef {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/evidence/orfs-work/results/sky130hd/nebula_cpu_npu_top/nebula/6_final.spef}
report_units
report_parasitic_annotation -report_unannotated > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/workloads/power/GEMM8/parasitic-annotation.rpt}
read_vcd -scope tb_cpu_elf/dut -begin_time 300000 -end_time 709451000 {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/workloads/GEMM8/activity-full.vcd}
report_activity_annotation -report_unannotated > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/workloads/power/GEMM8/activity-annotation.rpt}
report_power -digits 12 -format json > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/workloads/power/GEMM8/power.json}
report_power -digits 12 > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/representatives/fresh-single/physical/workloads/power/GEMM8/power.rpt}
} message options]} {puts stderr $message; puts stderr [dict get $options -errorinfo]; exit 1}
exit
