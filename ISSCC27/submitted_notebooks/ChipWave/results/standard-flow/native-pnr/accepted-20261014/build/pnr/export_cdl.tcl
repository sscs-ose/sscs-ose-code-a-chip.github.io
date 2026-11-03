if {[catch {
read_liberty /home/asic03/project/user37/CodeAChip_Baselines/CPU_NPU_before_standard_flow_20261013/submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_db build/pnr/results/6_final.odb
write_cdl -masters /home/asic03/project/user37/CodeAChip_Baselines/CPU_NPU_before_standard_flow_20261013/submission/ISSCC27/submitted_notebooks/ChipNebula_CPU/toolchain/orfs/flow/platforms/sky130hd/cdl/sky130hd.cdl build/pnr/results/6_final.cdl
} e]} {puts stderr $e; exit 1}
exit
