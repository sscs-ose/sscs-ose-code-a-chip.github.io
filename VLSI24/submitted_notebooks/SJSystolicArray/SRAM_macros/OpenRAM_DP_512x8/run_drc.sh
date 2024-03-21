#!/bin/sh
export OPENRAM_TECH="/tmp/OpenRAM/technology:/tmp/OpenRAM/compiler/../technology"
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_dp_cell.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_dp_cell_dummy.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_dp_cell_replica.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_cell_opt1a.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_sp_cell_opt1a_dummy.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_cell_opt1_ce.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_cell_opt1.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_sp_cell_opt1_replica.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_sp_cell_opt1a_replica.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_colend.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_colend_cent.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_colend_p_cent.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_colenda.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_colenda_cent.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_colenda_p_cent.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_rowend.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_rowenda.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_sp_rowend_replica.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__openram_sp_rowenda_replica.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_corner.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_cornera.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_cornerb.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_wlstrapa.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_wlstrap_ce.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_wlstrap.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_wlstrap_p_ce.mag .
cp /tmp/OpenRAM/technology/sky130/maglef_lib/sky130_fd_bd_sram__sram_sp_wlstrap_p.mag .
echo "$(date): Starting DRC using Magic /tmp/OpenRAM/miniconda/bin/magic"

/tmp/OpenRAM/miniconda/bin/magic -dnull -noconsole << EOF
load myconfig -dereference
puts "Finished loading cell myconfig"
cellname delete \(UNNAMED\)
select top cell
expand
puts "Finished expanding"
drc euclidean on
drc check
puts "Finished drc check"
drc catchup
puts "Finished drc catchup"
drc count total
quit -noprompt
EOF
magic_retcode=$?
echo "$(date): Finished ($magic_retcode) DRC using Magic /tmp/OpenRAM/miniconda/bin/magic"
exit $magic_retcode
