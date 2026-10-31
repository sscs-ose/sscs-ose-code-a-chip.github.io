"""Export the actual final OpenDB connectivity, retaining antenna and signal cells."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from study_protocol import digest,write_json

CASE=Path(__file__).resolve().parents[1]


def export(run):
    run=Path(run).resolve();evidence=run/'evidence';target=evidence/'measurement-source.json'
    if target.exists():raise ValueError('Existing derived-view attestation retained')
    selected=json.loads((evidence/'selected-delivery.json').read_text())
    commit=selected['content']['commit'];project=run/'project'
    paths=subprocess.run(['git','ls-tree','-r','--name-only',commit,'build/rtl-to-gds'],cwd=project,text=True,capture_output=True,check=True).stdout.splitlines()
    databases=[path for path in paths if path.endswith('/6_final.odb')]
    if len(databases)!=1:raise ValueError('Exactly one final physical database is required')
    output=evidence/'measurement';output.mkdir(exist_ok=False)
    database=output/'6_final.odb'
    database.write_bytes(subprocess.run(['git','show',commit+':'+databases[0]],cwd=project,capture_output=True,check=True).stdout)
    files=selected['collected_files']
    def view(name):
        matches=[item for item in files if Path(item['path']).name==name]
        if len(matches)!=1:raise ValueError('Ambiguous original physical view: '+name)
        item=matches[0];path=evidence/item['path']
        if digest(path)!=item['sha256']:raise ValueError('Original physical view changed')
        return path
    spef,sdc=view('6_final.spef'),view('6_final.sdc')
    library=CASE/'toolchain/orfs/flow/platforms/sky130hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    def q(path):
        text=str(path)
        if any(c in text for c in ('{','}','\\','\n','\r')):raise ValueError('Unsupported Tcl path')
        return '{'+text+'}'
    netlist=output/'6_final.sta.v';report=output/'database-parasitics.rpt'
    script=output/'export.tcl'
    script.write_text('if {[catch {\n'+
        'read_liberty '+q(library)+'\nread_db '+q(database)+'\nread_sdc '+q(sdc)+'\nset_propagated_clock [all_clocks]\nread_spef '+q(spef)+'\n'+
        '''set remove {}
set inventory [open '''+q(output/'cell-inventory.tsv')+''' w]
puts $inventory "instance\tmaster\tsignal_pins\tliberty_model\tpreserved"
foreach inst [[ord::get_db_block] getInsts] {
  set master [$inst getMaster]
  set name [$master getName]
  set signals 0
  foreach mt [$master getMTerms] {if {[$mt getSigType] ni {POWER GROUND}} {incr signals}}
  set modeled [expr {[llength [get_lib_cells -quiet $name]] > 0}]
  if {$signals > 0 && !$modeled} {error "Missing actual signal-cell Liberty model: $name"}
  set keep [expr {$signals > 0 || $modeled}]
  if {!$keep} {lappend remove $name}
  puts $inventory "[$inst getName]\t$name\t$signals\t$modeled\t$keep"
}
close $inventory
write_verilog -sort -remove_cells [lsort -unique $remove] '''+q(netlist)+'\nreport_parasitic_annotation -report_unannotated > '+q(report)+
        '\n} message options]} {puts stderr $message; puts stderr [dict get $options -errorinfo];exit 1}\nexit\n')
    with (output/'export.log').open('w') as log:
        result=subprocess.run(['openroad','-no_init','-exit','-threads','2',str(script)],stdout=log,stderr=subprocess.STDOUT,timeout=120)
    if result.returncode:raise RuntimeError('Final database export failed; inspect preserved log')
    record={'source_delivery':selected['id'],'source_commit':commit,'source_database_path':databases[0],
        'database_sha256':digest(database),'snapshot_id':selected['id']+'/database-aligned-sta',
        'views':{name:{'path':str(path.relative_to(evidence)),'sha256':digest(path)} for name,path in
                 (('netlist',netlist),('spef',spef),('sdc',sdc),('database',database))},
        'liberty_sha256':digest(library),'export_script_sha256':digest(script),
        'scope':'Derived read-only views of the selected immutable final OpenDB. All signal-bearing and Liberty-modeled cells, including antenna diodes, are retained; no RTL, layout, extraction or clock changes.'}
    write_json(target,record)
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',type=Path,required=True)
    print(json.dumps(export(p.parse_args().run),indent=2))
