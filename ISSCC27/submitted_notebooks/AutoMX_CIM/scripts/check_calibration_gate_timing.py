"""Independently report the actual routed calibration ICG enable timing checks."""
from pathlib import Path
import argparse,json,re,subprocess

def run(root,work,sdc=None):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=False)
    block=root/'inputs/digital_blocks/readout'
    netlist=block/'automx_cim_readout_seq.nl.v';spef=block/'automx_cim_readout_seq.spef'
    gates=re.findall(r'sky130_fd_sc_hd__dlclkp_1\s+(\S+)\s*\(',netlist.read_text())
    assert len(gates)==1,('Expected exactly one calibration data-bank ICG',gates)
    enable_pin=gates[0].lstrip('\\')+'/GATE'
    constraint=Path(sdc).resolve() if sdc else block/'child.sdc';assert constraint.is_file()
    script=work/'gate_timing.tcl'
    script.write_text(f'''read_liberty {{{root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'}}}
read_verilog {{{netlist}}}
link_design automx_cim_readout_seq
read_sdc {{{constraint}}}
read_spef {{{spef}}}
set_propagated_clock [all_clocks]
set enable_pin [get_pins {{{enable_pin}}}]
if {{[llength $enable_pin] != 1}} {{error "Missing mapped ICG enable pin"}}
puts GATING_SETUP_BEGIN
report_checks -to $enable_pin -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts GATING_SETUP_END
puts GATING_HOLD_BEGIN
report_checks -to $enable_pin -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts GATING_HOLD_END
exit
''')
    q=subprocess.run([root/'tools/opensta_current/build/sta','-exit',script],cwd=work,capture_output=True,text=True,timeout=180)
    text=q.stdout+q.stderr;(work/'opensta.log').write_text(text)
    assert q.returncode==0 and not re.search(r'(?im)^Error:',text),text[-2500:]
    checks={}
    for kind in ('SETUP','HOLD'):
        section=text.split('GATING_'+kind+'_BEGIN',1)[1].split('GATING_'+kind+'_END',1)[0]
        slacks=[float(s) for s in re.findall(r'([\deE+.-]+)\s+slack\s+\(',section)]
        assert slacks,('No actual ICG '+kind+' check reported',section)
        checks[kind.lower()+'_slack_ns']=min(slacks)
    report={'status':'PASS' if min(checks.values())>=0 else 'ICG_TIMING_VIOLATION','clock_gate_instances':gates,**checks,
        'constraint_source':str(constraint),'netlist':str(netlist),'spef':str(spef),
        'scope':'Actual mapped latch-based ICG GATE setup/hold checks at TT with child CTS SDC and extracted routed RC; independent of threshold-clock VCD and power measurements.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('CALIBRATION_ICG_TIMING',report['status'],checks,flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);p.add_argument('--sdc',type=Path)
    a=p.parse_args();run(a.root,a.work,a.sdc)
