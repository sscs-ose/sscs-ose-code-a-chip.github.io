if {[catch {
read_liberty {/home/asic03/project/user37/CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib}
read_lef {/home/asic03/project/user37/CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lef/sky130_fd_sc_hd.tlef}
read_lef {/home/asic03/project/user37/CodeAChip_Submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lef/sky130_fd_sc_hd_merged.lef}
read_verilog {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/evidence/measurement/6_final.sta.v}
link_design nebula_cpu_npu_top
read_sdc {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/evidence/orfs-work/results/sky130hd/nebula_cpu_npu_top/nebula/6_final.sdc}
set_propagated_clock [all_clocks]
read_spef {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/evidence/orfs-work/results/sky130hd/nebula_cpu_npu_top/nebula/6_final.spef}
report_units
report_parasitic_annotation -report_unannotated > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/workloads/power/CONV3/parasitic-annotation.rpt}
read_vcd -scope tb_cpu_elf/dut -begin_time 30000 -end_time 46326000 {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/workloads/CONV3/activity-full.vcd}
report_activity_annotation -report_unannotated > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/workloads/power/CONV3/activity-annotation.rpt}
report_power -digits 12 -format json > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/workloads/power/CONV3/power.json}
report_power -digits 12 > {/home/asic03/project/user37/CodeAChip_Experiments/Configurable_PPA_20261016/high-frequency/W1/physical/workloads/power/CONV3/power.rpt}
} message options]} {puts stderr $message; puts stderr [dict get $options -errorinfo]; exit 1}
exit
