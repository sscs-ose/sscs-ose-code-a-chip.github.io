if {[catch {
read_db /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/results/6_final.odb
set nebula_geometry_report /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/reports/pnr
source /home/asic03/project/user37/CodeAChip_Experiments/NextStage_20261013/standard-flow/.chip_nebula/taskgraph-v2/workspaces/attempt-5774e9973ce243acb92d41324cc4dd84/build/pnr/geometry_measure.tcl
} message options]} {puts stderr $message; puts stderr [dict get $options -errorinfo]; exit 1}
exit
