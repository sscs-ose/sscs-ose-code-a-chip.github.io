import hashlib
import json
from pathlib import Path
import subprocess
import sys
from checkpoint import save as checkpoint, restore

ROOT = Path(__file__).resolve().parents[2]
c = json.loads((ROOT / 'physical/chip-nebula/implementation.constraints.json').read_text())
views = c['view_binding']['views']
lib = views[c['view_binding']['liberty']]['installed_path']
result = ROOT / 'build/pnr/results'
report = ROOT / 'reports/pnr'
for name in [c['view_binding']['liberty'],'lef/sky130_fd_sc_hd.tlef','lef/sky130_fd_sc_hd_merged.lef','setRC.tcl','rcx_patterns.rules']:
    view=views[name]
    assert hashlib.sha256(Path(view['installed_path']).read_bytes()).hexdigest()==view['sha256'], 'Error-Class: invalid_physical_view: frozen view changed: '+name
tool_identity = json.loads((report / 'input_audit.json').read_text())['tool_identity']
assert hashlib.sha256(Path(tool_identity['path']).read_bytes()).hexdigest() == tool_identity['sha256']
if '--restore' in sys.argv:
    restore()


def run(name, body):
    script = ROOT / 'build/pnr' / (name + '.tcl')
    script.write_text('if {[catch {\n' + body + '\n} message options]} {\nputs stderr $message\nputs stderr [dict get $options -errorinfo]\nexit 1\n}\nexit\n')
    with (report / (name + '.log')).open('w') as f:
        subprocess.run([tool_identity['path'], '-exit', '-no_init', '-threads', '2', str(script)], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, check=True)


def reports(mode):
    return f'''
set f [open {report}/{mode}_signal_connectivity.tsv w]
puts $f "net\tterminal"
foreach net [[ord::get_db_block] getNets] {{
  if {{[$net getSigType] in {{POWER GROUND}}}} {{continue}}
  foreach it [$net getITerms] {{
    set mt [$it getMTerm]
    if {{[$mt getSigType] ni {{POWER GROUND}}}} {{puts $f "[$net getName]\tI:[[$it getInst] getName]/[$mt getName]"}}
  }}
  foreach bt [$net getBTerms] {{puts $f "[$net getName]\tP:[$bt getName]"}}
}}
close $f
set f [open {report}/{mode}_all_signal_pins.tsv w]
puts $f "terminal\tnet"
foreach inst [[ord::get_db_block] getInsts] {{
  foreach it [$inst getITerms] {{
    if {{[[$it getMTerm] getSigType] in {{POWER GROUND}}}} {{continue}}
    set net [$it getNet]
    set netname ""
    if {{$net ne "NULL"}} {{set netname [$net getName]}}
    puts $f "I:[$inst getName]/[[$it getMTerm] getName]\t$netname"
  }}
}}
foreach bt [[ord::get_db_block] getBTerms] {{
  if {{[$bt getSigType] ni {{POWER GROUND}}}} {{puts $f "P:[$bt getName]\t[[$bt getNet] getName]"}}
}}
close $f
report_units
report_parasitic_annotation -report_unannotated > {report}/{mode}_parasitic_annotation.rpt
report_checks -path_delay max -group_path_count 10000 -format full_clock_expanded -fields {{slew capacitance fanout input_pin net}} -digits 12 > {report}/{mode}_setup_paths.rpt
report_checks -path_delay min -group_path_count 10000 -format full_clock_expanded -fields {{slew capacitance fanout input_pin net}} -digits 12 > {report}/{mode}_hold_paths.rpt
check_setup -verbose > {report}/{mode}_check_setup.rpt
report_checks -unconstrained -path_delay min_max -group_path_count 10000 -digits 12 > {report}/{mode}_unconstrained_paths.rpt
foreach kind {{max_slew max_capacitance max_fanout recovery removal min_pulse_width}} {{
  puts "REPORT_CHECK_TYPES {mode} $kind -violators"
  report_check_types -$kind -violators -digits 12 > {report}/{mode}_$kind.rpt
}}
report_clock_skew -setup -digits 12 > {report}/{mode}_clock_skew_setup.rpt
report_clock_skew -hold -digits 12 > {report}/{mode}_clock_skew_hold.rpt
set f [open {report}/{mode}_timing.json w]
puts $f [format {{{{"setup_slack_ns": %.17g, "hold_slack_ns": %.17g, "instance_count": %d}}}} [sta::worst_slack -max] [sta::worst_slack -min] [llength [get_cells -hier *]]]
close $f
report_worst_slack -max -digits 12
report_worst_slack -min -digits 12
report_tns -max -digits 12
report_tns -min -digits 12
'''


run('export_sta_netlist', f'''
read_liberty {lib}
read_db {result}/6_final.odb
read_sdc {ROOT / c['sdc_path']}
set_propagated_clock [all_clocks]
read_spef {result}/6_final.spef
set block [ord::get_db_block]
set remove {{}}
set f [open {report}/database_instances.tsv w]
puts $f "instance\tmaster\tsignal_pin_count\tliberty_model\tsta_preserved\tantenna"
foreach inst [$block getInsts] {{
  set master [$inst getMaster]
  set name [$master getName]
  set signals 0
  foreach mt [$master getMTerms] {{
    if {{[$mt getSigType] ni {{POWER GROUND}}}} {{incr signals}}
  }}
  set modeled [expr {{[llength [get_lib_cells -quiet $name]] > 0}}]
  if {{$signals > 0 && !$modeled}} {{error "Error-Class: invalid_physical_view: missing Liberty model for actual signal master $name"}}
  set keep [expr {{$signals > 0 || $modeled}}]
  if {{!$keep}} {{lappend remove $name}}
  set antenna [expr {{[$master getType] eq "CORE_ANTENNACELL"}}]
  puts $f "[$inst getName]\t$name\t$signals\t$modeled\t$keep\t$antenna"
}}
close $f
write_verilog -sort -remove_cells [lsort -unique $remove] {result}/6_final.sta.v
write_sdc -no_timestamp -digits 12 {result}/6_final.sdc
write_sdf -no_timestamp -digits 12 {result}/6_final.sdf
write_cdl -masters {views['cdl/sky130hd.cdl']['installed_path']} {result}/6_final.cdl
set nebula_geometry_report {report}
source {ROOT}/build/pnr/geometry_measure.tcl
check_placement -verbose
set routed [design_is_routed -verbose]
set antenna [check_antennas -verbose -report_file {report}/final_antenna.rpt]
set f [open {report}/physical_checks.json w]
puts $f [format {{{{"routed": %s, "antenna_violations": %d}}}} [expr {{$routed ? "true" : "false"}}] $antenna]
close $f
check_power_grid -net VDD -error_file {report}/final_power_vdd.rpt
check_power_grid -net VSS -error_file {report}/final_power_vss.rpt
{reports('database')}
''')
(result / '6_final.v').write_bytes((result / '6_final.sta.v').read_bytes())

run('netlist_spef_with_diodes', f'''
read_liberty {lib}
read_lef {views['lef/sky130_fd_sc_hd.tlef']['installed_path']}
read_lef {views['lef/sky130_fd_sc_hd_merged.lef']['installed_path']}
read_verilog {result}/6_final.sta.v
link_design {c['physical_top']}
read_sdc {result}/6_final.sdc
set_propagated_clock [all_clocks]
read_spef {result}/6_final.spef
set f [open {report}/sta_instances.tsv w]
puts $f "instance\tmaster"
foreach inst [[ord::get_db_block] getInsts] {{puts $f "[$inst getName]\t[[$inst getMaster] getName]"}}
close $f
{reports('sta')}
''')
print('Final STA export and independent reload completed; consistency evaluation remains required.')
checkpoint('final_export', result / '6_final.odb', 'finish')
