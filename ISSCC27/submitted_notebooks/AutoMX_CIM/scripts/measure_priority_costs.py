"""Map original/new readout and a ternary sign/add baseline with one tool/library."""
from pathlib import Path
import argparse,csv,json,os,subprocess,time

def measure(root,work):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    lib=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    image=json.loads((root/'standalone.json').read_text())['openlane_image']
    ip=root/'ip/automx_mha/rtl';baseline=root/'inputs/digital_benchmarks/linear_readout/source.sv'
    targets=[('linear_readout','automx_cim_readout_seq',[baseline]),('binary_readout','automx_cim_readout_seq',[root/'rtl/automx_cim_readout_seq.sv']),
             ('digital_projection','automx_ternary_projection_digital',[ip/'automx_mha_ip.sv',ip/'automx_ternary_projection_digital.sv']),
             ('digital_attention','automx_mha_digital_top',[ip/'automx_mha_ip.sv',ip/'automx_ternary_projection_digital.sv'])]
    rows=[]
    for label,top,sources in targets:
        folder=work/label;folder.mkdir(exist_ok=True);script=folder/'synthesis.ys';stat=folder/'stat.json'
        mapped=folder/f'{top}.v'
        script.write_text(f'read_liberty -lib "{lib}"\n'+''.join(f'read_verilog -sv "{s}"\n' for s in sources)+
            f'hierarchy -check -top {top}\nsynth -top {top} -flatten\ndfflibmap -liberty "{lib}"\nabc -liberty "{lib}"\nclean\ncheck -assert\nwrite_verilog -noattr -noexpr "{mapped}"\ntee -o {stat} stat -json -liberty "{lib}"\n')
        args=['docker','run','--rm','--network','none','--cpus','2','--user',f'{os.getuid()}:{os.getgid()}',
          '-v',f'{root}:{root}','-w',str(folder),'--entrypoint','yosys',image,'-s',str(script)]
        start=time.monotonic();r=subprocess.run(args,capture_output=True,text=True,timeout=300)
        (folder/'yosys.log').write_text(r.stdout+r.stderr)
        if r.returncode:raise RuntimeError((r.stdout+r.stderr)[-3000:])
        statistics=json.loads(stat.read_text());result=statistics.get('design',statistics['modules']['\\'+top])
        row={'design':label,'top':top,'mapped_cells':result['num_cells'],'mapped_area_um2':result['area'],
           'elapsed_s':time.monotonic()-start,'evidence':'mapped SKY130 TT synthesis; not routed power or area'}
        rows.append(row);print('MAPPED_COST',json.dumps(row),flush=True)
    (work/'costs.json').write_text(json.dumps({'status':'PASS','clock_target_ns':40,'library':str(lib),'designs':rows,'scope':'Same Yosys/ABC image and Liberty for all candidates. No vectorless power is presented as measured energy.'},indent=2)+'\n')
    with (work/'costs.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return rows

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();measure(a.root,a.work)
