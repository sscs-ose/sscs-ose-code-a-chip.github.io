"""Gate-level, VCD-annotated child-block power on matched native application frames."""
from pathlib import Path
import argparse,json,re,subprocess,time,shutil
import numpy as np
from scripts.standalone_runtime import container

def run_command(args,work,name,timeout=240):
    result=subprocess.run(list(map(str,args)),cwd=work,capture_output=True,text=True,timeout=timeout)
    (work/name).write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError((result.stdout+result.stderr)[-2500:])
    return result.stdout+result.stderr

def measure(root,base,work,clock_aware=False):
    root=Path(root).resolve();base=Path(base).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    native=base/'native_replay';record=json.loads((native/'verification.json').read_text());assert record['status']=='PASS'
    n=record['frames'];assert n>=2
    primitive=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/verilog/primitives.v'
    models=primitive.with_name('sky130_fd_sc_hd.v')
    library=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    hard=json.loads((root/'inputs/digital_blocks/source_library.json').read_text())
    mha=next(v for v in hard['blocks'] if v['name']=='mha')
    new=next(v for v in hard['blocks'] if v['name']=='readout')
    def resolve(row,key):return root/'inputs/digital_blocks'/row[key]
    benchmarks=root/'inputs/digital_benchmarks';old_folder=benchmarks/'linear_readout'
    baseline=json.loads((benchmarks/'digital_attention.json').read_text())
    for key in ('source','gds','lef','odb','lib','mapped_netlist','spef'):baseline[key]=str(benchmarks/baseline[key])
    expected_source=(root/'ip/automx_mha/rtl/automx_mha_ip.sv').read_text()+'\n'+(root/'ip/automx_mha/rtl/automx_ternary_projection_digital.sv').read_text()
    assert Path(baseline['source']).read_text()==expected_source,'Digital comparison physical views do not match current RTL'
    results=[]
    for variant in ('linear','binary','digital'):
        folder=work/variant;folder.mkdir(exist_ok=True)
        for path in native.glob('*.memh'):shutil.copy2(path,folder/path.name)
        # Capture interface outputs, not RTL-only internal array names, so the
        # same comparison also verifies the synthesized/routed gate netlist.
        if variant=='digital':
            from scripts.verify_har_application_rtl import DIGITAL_TB
            source=DIGITAL_TB
            source=source.replace('reg [47:0] held;','reg [47:0] held;reg [95:0] observed_frame;')
            source=source.replace('held=rsp_result_x2_o;','observed_frame[48*row+:48]=rsp_result_x2_o;held=rsp_result_x2_o;')
            source=source.replace('{dut.mha_i.output_rows[1],dut.mha_i.output_rows[0]}','observed_frame')
            source=source.replace('for(f=0;f<n;f=f+1)begin','$dumpfile("activity.vcd");$dumpvars(0,dut);\n for(f=0;f<n;f=f+1)begin')
            top='tb_digital_application';netlists=[Path(baseline['mapped_netlist'])]
            power_blocks=[('digital_attention','automx_mha_digital_top',netlists[0],Path(baseline['spef']),'tb_digital_application/dut')]
        else:
            source=(native/'tb_native_replay.sv').read_text()
            if 'control_timing.csv' in source:
                from scripts.capture_readout_timing import TRACE
                source=source.replace(TRACE,'')
            source=re.sub(r'module sky130_fd_sc_hd__buf_1\(.*?endmodule','',source,flags=re.S)
            source=re.sub(r'^\s*defparam dut\.seq_i\..*?;','',source,flags=re.M)
            # This benchmark starts after boot and calibration. Advance only
            # the boot counter before measurement, then release it and program
            # every threshold through the real interface. No active-window
            # state or output is forced. Cold-start energy remains separate.
            source=source.replace('rst_ni=1;repeat(4)@(negedge clk_i);',
                r"rst_ni=1; force dut.seq_i.\timer[13] = 1'b1; repeat(2)@(negedge clk_i); release dut.seq_i.\timer[13] ; repeat(2)@(negedge clk_i);")
            # Internal transaction tags were checked at RTL. Gate netlists
            # no longer contain the compiler's row/phase register hierarchy.
            start=source.index('col=dut.seq_i.column;phase=dut.seq_i.phase_b;requested_acts=0;')
            end=source.index('adc_word<=native_words[conversions];',start)
            source=source[:start]+source[end:]
            source=source.replace('reg [47:0] held;','reg [47:0] held;reg [95:0] observed_frame;')
            source=source.replace('held=mha_rsp_result_x2_o;','observed_frame[48*row+:48]=mha_rsp_result_x2_o;held=mha_rsp_result_x2_o;')
            source=source.replace('{dut.mha_i.output_rows[1],dut.mha_i.output_rows[0]}','observed_frame')
            source=source.replace('for(f=0;f<cases;f=f+1)begin','$dumpfile("activity.vcd");$dumpvars(0,dut);\n        for(f=0;f<cases;f=f+1)begin')
            source=re.sub(r'// The original direct readout interface.*?\$finish;', '$finish;',source,flags=re.S)
            top='tb_mha_mixed_top'
            seq=resolve(new,'mapped_netlist') if variant=='binary' else old_folder/'automx_cim_readout_seq.nl.v'
            spef=resolve(new,'spef') if variant=='binary' else old_folder/'automx_cim_readout_seq.spef'
            netlists=[resolve(mha,'mapped_netlist'),seq,root/'inputs/automx_cim_mixed_signal_proto.sv',root/'inputs/wrapper_blackboxes.sv']
            power_blocks=[('readout','automx_cim_readout_seq',seq,spef,'tb_mha_mixed_top/dut/seq_i'),
                          ('mha','automx_mha_ip',resolve(mha,'mapped_netlist'),resolve(mha,'spef'),'tb_mha_mixed_top/dut/mha_i')]
        test=folder/'tb_gls.sv';test.write_text(source)
        run_command(['iverilog','-g2012','-DFUNCTIONAL','-DUNIT_DELAY=','-s',top,'-o',folder/'gls.vvp',primitive,models,*netlists,test],folder,'compile.log')
        start=time.monotonic()
        out=run_command(['vvp',folder/'gls.vvp','+DATA='+str(folder),f'+CASES={n}'],folder,'simulation.log',timeout=600)
        expected=(folder/'outputs.memh').read_text().splitlines()
        observed=(folder/('observed_digital.memh' if variant=='digital' else 'observed_native.memh')).read_text().splitlines()
        assert [int(x,16) for x in observed]==[int(x,16) for x in expected]
        vcd=folder/'activity.vcd';text=vcd.read_text();times=[int(v) for v in re.findall(r'^#(\d+)\s*$',text,re.M)]
        unit=re.search(r'\$timescale\s+(\d+)\s*(s|ms|us|ns|ps|fs)\s+\$end',text)
        assert times and unit
        scale=int(unit[1])*{'s':1,'ms':1e-3,'us':1e-6,'ns':1e-9,'ps':1e-12,'fs':1e-15}[unit[2]]
        duration=(max(times)-min(times))*scale;assert duration>0
        powers=[]
        for label,design,netlist,spef,scope in power_blocks:
            script=folder/f'power_{label}.tcl'
            activity=f'read_vcd -scope {scope} {{{vcd}}}' if clock_aware else f'read_power_activities -scope {scope} -vcd {{{vcd}}}'
            script.write_text(f'''read_liberty {{{library}}}
set_cmd_units -power W
read_verilog {{{netlist}}}
link_design {design}
create_clock -name clk -period 40 [get_ports clk_i]
read_spef {{{spef}}}
set_input_transition 0.1 [all_inputs]
set_load 0.004 [all_outputs]
{activity}
puts "POWER_SIGNAL_PIN_COUNT=[llength [get_pins -hierarchical *]]"
puts "POWER_PORT_COUNT=[llength [get_ports *]]"
report_units
report_power -digits 9
exit
''')
            command=[root/'tools/opensta_current/build/sta','-exit',script] if clock_aware else container(root,'sta',['-exit',script],f'automx-power-{variant}-{label}',folder)
            log=run_command(command,folder,f'power_{label}.log')
            assert not re.search(r'(?im)^Error:',log),log[-2000:]
            numbers=re.search(r'(?m)^Total\s+([\deE+.-]+)\s+([\deE+.-]+)\s+([\deE+.-]+)\s+([\deE+.-]+)',log)
            assert numbers,log[-3000:]
            values=list(map(float,numbers.groups()))
            annotation=re.search(r'Annotated (\d+) pin activities',log)
            pin_count=re.search(r'POWER_SIGNAL_PIN_COUNT=(\d+)',log)
            port_count=re.search(r'POWER_PORT_COUNT=(\d+)',log)
            assert annotation and pin_count and port_count,'Missing activity annotation evidence'
            powers.append({'block':label,'internal_power_w':values[0],'switching_power_w':values[1],'leakage_power_w':values[2],
                          'total_power_w':values[3],'annotated_pin_activities':int(annotation[1]),'signal_pin_count':int(pin_count[1]),
                          'design_port_count':int(port_count[1]),'annotation_fraction_including_ports':int(annotation[1])/(int(pin_count[1])+int(port_count[1])),
                          'activity_scope':scope,'spef':str(spef),'log':str(folder/f'power_{label}.log')})
        report={'variant':variant,'frames':n,'gate_output_mismatches':0,'activity_window_s':duration,'gate_simulation_elapsed_s':time.monotonic()-start,
           'power_blocks':powers,'child_digital_power_w':sum(p['total_power_w'] for p in powers),
           'child_digital_energy_per_frame_j':sum(p['total_power_w'] for p in powers)*duration/n,
           'scope':'VCD-annotated child gate netlists with extracted RC, zero-delay warm functional GLS. Boot counter advanced before calibration/measurement. Excludes parent CTS/IO, analog rails, external drivers and initialization; not total measured system energy.'}
        results.append(report);(folder/'power.json').write_text(json.dumps(report,indent=2)+'\n')
        print('ACTIVITY_POWER_PASS',variant,'frames',n,'mismatches',0,'latency_us/frame',round(duration/n*1e6,6),
            'child_mW',round(report['child_digital_power_w']*1000,6),'nJ/frame',round(report['child_digital_energy_per_frame_j']*1e9,6),flush=True)
    final={'status':'PASS','results':results,'corner':'SKY130 TT 1.8V 25C','clock_mhz':25,'same_native_application_frames':True,'power_tool':'OpenSTA 3.1.0 clock-aware VCD' if clock_aware else 'OpenSTA 2.4.0 VCD'}
    (work/'verification.json').write_text(json.dumps(final,indent=2)+'\n');return final

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--base',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();measure(a.root,a.base,a.work)
