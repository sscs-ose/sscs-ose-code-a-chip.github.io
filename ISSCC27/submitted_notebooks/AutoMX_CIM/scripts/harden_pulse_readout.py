"""Harden a readout with protected local pulse lanes and sized data buffers."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,time
from scripts import harden_digital_blocks as hard

def build(root,source,work):
    root=Path(root).resolve();source=Path(source).resolve();folder=Path(work).resolve()/'readout';design=folder/'design';design.mkdir(parents=True,exist_ok=False)
    top='automx_cim_readout_seq';config=json.loads((root/'inputs/openlane_config_template.json').read_text())
    config.update(DESIGN_NAME=top,VERILOG_FILES=[str(source)],DIE_AREA='0 0 1250 750',DESIGN_IS_CORE=0,FP_CORE_UTIL=30,
        PL_TARGET_DENSITY=.4,FP_PDN_CHECK_NODES=1,FP_PDN_VOFFSET=14,FP_PDN_VPITCH=80,FP_PDN_VWIDTH=1.6,
        PRIMARY_SIGNOFF_TOOL='magic',RT_MAX_LAYER='met4',GRT_MAX_LAYER='met4',DRT_MAX_LAYER='met4',RUN_SPEF_EXTRACTION=0,STA_WRITE_LIB=0,
        RUN_HEURISTIC_DIODE_INSERTION=0,GLB_RESIZER_DESIGN_OPTIMIZATIONS=0,GLB_RESIZER_TIMING_OPTIMIZATIONS=1,
        GLB_RESIZER_SETUP_SLACK_MARGIN=1.,GLB_RESIZER_HOLD_SLACK_MARGIN=.1,RSZ_MULTICORNER_LIB=0,
        RSZ_DONT_TOUCH_RX='(pulse_generator|delay_taps|storage_gating|clkbuf_)')
    for k in ('FP_PDN_MACRO_HOOKS','EXTRA_LEFS','EXTRA_GDS_FILES','EXTRA_LIBS','MACRO_PLACEMENT_CFG','FP_PDN_CFG','VERILOG_FILES_BLACKBOX'):config.pop(k,None)
    (design/'config.json').write_text(json.dumps(config,indent=2)+'\n');shutil.copy2(source,folder/'source.sv')
    eco=folder/'size_data_buffers.tcl';eco.write_text('''source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read
set master [[ord::get_db] findMaster sky130_fd_sc_hd__buf_16]
set block [ord::get_db_block]
set count 0
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {[[$inst getMaster] getName] eq "sky130_fd_sc_hd__buf_1" && ![regexp {(pulse_generator|delay_taps|clkbuf_)} $name]} {
  set net [[$inst findITerm X] getNet]
  if {[llength [$net getITerms]]>=16} {
   $inst swapMaster $master
   incr count
  }
 }
}
puts "DATA_BUFFER_SIZING count=$count drive=16 minimum_net_pin_count=16 pulse_lanes_preserved=true"
set outputs 0
foreach port [$block getBTerms] {
 set name [$port getName]
 if {![regexp {^wl[pn]_o} $name]} {continue}
 foreach pin [[$port getNet] getITerms] {
  if {[[$pin getMTerm] getIoType] ne "OUTPUT"} {continue}
  set inst [$pin getInst]
  set model [[$inst getMaster] getName]
  foreach strength {16 12 8 6 4 2 1} {
   set candidate [regsub {_[0-9]+$} $model _$strength]
   set strong [[ord::get_db] findMaster $candidate]
   if {$strong!="NULL"} {
    $inst swapMaster $strong
    puts "WORDLINE_OUTPUT_DRIVER $name $model $candidate"
    incr outputs
    break
   }
  }
 }
}
if {$outputs!=8} {error "Expected eight explicitly sized wordline output drivers"}
detailed_placement
check_placement -verbose
write
''')
    regular=folder/'place_delay_line.tcl';regular.write_text(r'''source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read
set block [ord::get_db_block]
set row [lindex [$block getRows] 40]
lassign [$row getOrigin] x y
set site [[$row getSite] getWidth]
set height [[$row getSite] getHeight]
set padding [expr {2*$site}]
set origin $x
set x [expr {$x+20*$site}]
set obstacles {}
foreach inst [$block getInsts] {
 if {[$inst isFixed]} {
  set bbox [$inst getBBox]
  if {[$bbox yMin]<$y+$height && [$bbox yMax]>$y} {lappend obstacles [list [$bbox xMin] [$bbox xMax]]}
 }
}
set stages {}
foreach inst [$block getInsts] {
 if {[regexp {^delay_taps\[([0-9]+)\]\.delay_i$} [string map {\\ ""} [$inst getName]] all number]} {lappend stages [list $number $inst]}
}
if {[llength $stages]!=72} {error "Expected 72 physical delay stages, found [llength $stages]"}
foreach pair [lsort -integer -index 0 $stages] {
 set inst [lindex $pair 1]
 set width [[$inst getMaster] getWidth]
 foreach obstacle [lsort -integer -index 0 $obstacles] {
  lassign $obstacle left right
  if {$x+$width+$padding>$left && $x-$padding<$right} {
   set x [expr {$origin+int(ceil(double($right+$padding-$origin)/$site))*$site}]
  }
 }
 $inst setOrient [$row getOrient]
 $inst setLocation $x $y
 $inst setPlacementStatus FIRM
 set x [expr {$x+$width+2*$padding}]
}
# Keep each isolated tap input near its source; strong local drivers
# carry the mux wiring. Loading every sixth tap equally preserves spacing.
set tap_driver_count 0
set tap_lookup {}
foreach mapped [$block getInsts] {dict set tap_lookup [string map [list [format %c 92] ""] [$mapped getName]] $mapped}
for {set lane 0} {$lane<4} {incr lane} {
 for {set code 0} {$code<=12} {incr code} {
  set names [list [format {pulse_generator[%d].pulse_tap_drive[%d].isolate_i} $lane $code] [format {pulse_generator[%d].pulse_tap_drive[%d].drive_i} $lane $code]]
  if {![dict exists $tap_lookup [lindex $names 0]]} {continue}
  set row [lindex [$block getRows] [expr {43+3*$lane}]]
  lassign [$row getOrigin] origin y
  set site [[$row getSite] getWidth];set height [[$row getSite] getHeight]
  set padding [expr {2*$site}]
  set stage [expr {$code==0 ? 1 : 6*$code}]
  set driver [dict get $tap_lookup [format {delay_taps[%d].delay_i} $stage]]
  lassign [$driver getLocation] x ignore_y
  set obstacles {}
  foreach fixed [$block getInsts] {
   if {[$fixed isFixed]} {
    set bb [$fixed getBBox]
    if {[$bb yMin]<$y+$height && [$bb yMax]>$y} {lappend obstacles [list [$bb xMin] [$bb xMax]]}
   }
  }
  foreach name $names {
   set inst [dict get $tap_lookup $name];set width [[$inst getMaster] getWidth]
   foreach obstacle [lsort -integer -index 0 $obstacles] {
    lassign $obstacle left right
    if {$x+$width+$padding>$left && $x-$padding<$right} {set x [expr {$origin+int(ceil(double($right+$padding-$origin)/$site))*$site}]}
   }
   $inst setOrient [$row getOrient]
   $inst setLocation $x $y
   $inst setPlacementStatus FIRM
   set x [expr {$x+$width+2*$padding}]
   incr tap_driver_count
  }
 }
}
# Pulse formation must remain adjacent to its strong output driver.
# Only full-swing reference/delay edges travel on the longer mux wires.
set edge_cluster_cells 0
for {set lane 0} {$lane<4} {incr lane} {
 set row [lindex [$block getRows] [expr {70+8*$lane}]]
 lassign [$row getOrigin] origin y
 set site [[$row getSite] getWidth];set height [[$row getSite] getHeight]
 set padding [expr {2*$site}];set x [expr {$origin+500*$site}]
 set obstacles {}
 foreach fixed [$block getInsts] {
  if {[$fixed isFixed]} {
   set bb [$fixed getBBox]
   if {[$bb yMin]<$y+$height && [$bb yMax]>$y} {lappend obstacles [list [$bb xMin] [$bb xMax]]}
  }
 }
 foreach suffix {reference_low_i delayed_low_i reference_high_i delayed_high_i reference_select_i delayed_select_i invert_i positive_i positive_drive_i negative_i negative_drive_i} {
  set name [format {pulse_generator[%d].%s} $lane $suffix]
  if {![dict exists $tap_lookup $name]} {continue}
  set inst [dict get $tap_lookup $name];set width [[$inst getMaster] getWidth]
  foreach obstacle [lsort -integer -index 0 $obstacles] {
   lassign $obstacle left right
   if {$x+$width+$padding>$left && $x-$padding<$right} {set x [expr {$origin+int(ceil(double($right+$padding-$origin)/$site))*$site}]}
  }
  $inst setOrient [$row getOrient]
  $inst setLocation $x $y
  $inst setPlacementStatus FIRM
  set x [expr {$x+$width+2*$padding}]
  incr edge_cluster_cells
 }
}
if {$edge_cluster_cells!=44} {error "Expected 44 explicitly clustered pulse-formation cells"}
puts "PULSE_FORMATION_CLUSTER cells=$edge_cluster_cells adjacent_gate_driver=true"
puts "ROW_LOCAL_TAP_PLACEMENT cells=$tap_driver_count"
puts "REGULAR_DELAY_LINE stages=72 row=40 fixed=true legal_padding_sites=2 tap_obstacles_skipped=true"
write
''')
    run=folder/'build.tcl';run.write_text('''lappend ::auto_path /openlane/scripts
package require openlane
prep -design {'''+str(design)+'''} -config_file {'''+str(design/'config.json')+'''} -tag hard
run_synthesis
run_floorplan
run_openroad_script {'''+str(regular)+'''} -indexed_log $::env(floorplan_logs)/delay_line_placement.log -save "dir=$::env(floorplan_tmpfiles),def,sdc,odb,netlist,powered_netlist"
run_placement
run_cts
run_resizer_timing
run_openroad_script {'''+str(eco)+'''} -indexed_log $::env(cts_logs)/data_buffer_sizing.log -save "dir=$::env(cts_tmpfiles),def,sdc,odb,netlist,powered_netlist"
set ::env(RSZ_LIB) $::env(LIB_TYPICAL)
run_routing
run_magic
save_final_views
save_state
puts LOCAL_PULSE_READOUT_ROUTED
''')
    command=hard.native(root,'/openlane/flow.tcl',['-interactive','-file',run],'automx-local-pulse-'+str(os.getpid()),'/openlane');start=time.monotonic()
    with (folder/'native.log').open('w') as log:q=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=2700)
    assert q.returncode==0,(folder/'native.log').read_text()[-2500:]
    result=hard.finish_block(root,folder,'readout',time.monotonic()-start)
    assert result['setup_slack_ns']>=0 and result['hold_slack_ns']>=0,result
    print('LOCAL_PULSE_READOUT_PASS',result['setup_slack_ns'],result['hold_slack_ns'],flush=True);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--source',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();build(a.root,a.source,a.work)
