"""Attribute measured gate activity to threshold flops, clock cells and other logic."""
from pathlib import Path
import argparse,json,re
from scripts.measure_physical_pwm import structural
from scripts.measure_activity_power import run_command
from scripts.standalone_runtime import container

def run(root,power,work):
    root=Path(root).resolve();power=Path(power).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    measured=json.loads((power/'verification.json').read_text());rows=[]
    for variant in ('binary_reference','binary'):
        record=next(v for v in measured['results'] if v['variant']==variant)
        oldscript=power/variant/'power_readout.tcl';source=oldscript.read_text()
        netlist=Path(re.search(r'read_verilog \{(.*?)\}',source)[1]);cells,drivers=structural(netlist)
        storage={name for name,c in cells.items() if any(n.startswith('thresholds[') for p,n in c['pins'].items() if p in ('Q','Q_N'))}
        assert len(storage)==3648,len(storage)
        clocks=set()
        def visit(net):
            if net not in drivers:return
            name,pin=drivers[net]
            if name in clocks:return
            clocks.add(name)
            for p,n in cells[name]['pins'].items():
                if p not in ('X','Y','Q','Q_N','GCLK','HI','LO'):visit(n)
        for c in cells.values():
            if 'CLK' in c['pins']:visit(c['pins']['CLK'])
        clocks-=storage;groups={'threshold_data_flops':storage,'clock_distribution':clocks,
            'other_controller_logic':set(cells)-storage-clocks}
        script=work/f'{variant}.tcl'
        body=source.split('report_units',1)[0]
        for name,instances in groups.items():
            body+=f'puts "GROUP {name}"\nreport_power -instances [get_cells {{{" ".join(sorted(instances))}}}] -digits 9\n'
        body+='exit\n';script.write_text(body)
        command=[root/'tools/opensta_current/build/sta','-exit',script] if 'read_vcd ' in body else container(root,'sta',['-exit',script],'automx-attribute-'+variant,work)
        log=run_command(command,work,variant+'.log')
        assert not re.search(r'(?im)^Error:',log)
        for name,instances in groups.items():
            block=log.split('GROUP '+name+'\n',1)[1].split('GROUP ',1)[0]
            values=[]
            # With -instances OpenSTA emits one row per cell, no aggregate total.
            for line in block.splitlines():
                f=line.split()
                if len(f)>=5:
                    try:v=list(map(float,f[:4]))
                    except ValueError:continue
                    values.append(v)
            assert len(values)==len(instances),(name,len(values),len(instances),block[-600:])
            totals=[sum(v[i] for v in values) for i in range(4)]
            rows.append({'variant':variant,'group':name,'instances':len(instances),'internal_w':totals[0],
                'switching_w':totals[1],'leakage_w':totals[2],'total_w':totals[3]})
        print('POWER_ATTRIBUTION',variant,[(r['group'],round(r['total_w']*1000,5)) for r in rows if r['variant']==variant],flush=True)
    report={'status':'PASS','rows':rows,'scope':'Disjoint instance groups in the routed readout. VCD/Liberty power estimate; full supply/clock-tree variation and analog rails excluded.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--power',type=Path,required=True);p.add_argument('--work',type=Path,required=True);a=p.parse_args();run(a.root,a.power,a.work)
