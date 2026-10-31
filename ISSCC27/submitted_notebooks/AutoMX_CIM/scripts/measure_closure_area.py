"""Use one synthesis/library configuration for controller and upstream SAR costs."""
from pathlib import Path
import argparse,csv,json,os,re,subprocess,time

def run(root,work,readout=None,core_views=None):
    root=Path(root).resolve();work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    library=root/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
    image=json.loads((root/'standalone.json').read_text())['openlane_image'];sar=root/'third_party/SKY130_SAR_ADC1/mixed_signal_partition/verilog/rtl'
    targets=[('binary_reference','automx_cim_readout_seq',[root/'inputs/digital_benchmarks/binary_reference/source.sv']),
       ('calibration_gated','automx_cim_readout_seq',[root/'inputs/digital_benchmarks/calibration_gated/source.sv']),
       ('current_readout','automx_cim_readout_seq',[Path(readout).resolve() if readout else root/'rtl/automx_cim_readout_seq.sv']),
       ('sar_digital','adc_core_digital',[sar/n for n in ('adc_control_nonbinary.v','adc_row_col_decoder.v','adc_osr.v','adc_core_digital.v')])]
    rows=[]
    for name,top,sources in targets:
        folder=work/name;folder.mkdir(exist_ok=True);script=folder/'synthesis.ys';stat=folder/'stat.json';mapped=folder/(top+'.v')
        script.write_text(f'read_liberty -lib "{library}"\n'+''.join(f'read_verilog -sv "{p}"\n' for p in sources)+
            f'hierarchy -check -top {top}\nsynth -top {top} -flatten\ndfflibmap -liberty "{library}"\nabc -liberty "{library}"\nclean\ncheck -assert\nwrite_verilog -noattr -noexpr "{mapped}"\ntee -o {stat} stat -json -liberty "{library}"\n')
        args=['docker','run','--rm','--network','none','--cpus','2','--user',f'{os.getuid()}:{os.getgid()}',
            '-v',str(root)+':'+str(root),'-w',str(folder),'--entrypoint','yosys',image,'-s',str(script)]
        start=time.monotonic()
        with (folder/'yosys.log').open('w') as log:q=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=300)
        assert q.returncode==0,(folder,(folder/'yosys.log').read_text()[-1500:])
        statistics=json.loads(stat.read_text());data=statistics.get('design',statistics['modules']['\\'+top])
        rows.append({'design':name,'mapped_cells':data['num_cells'],'mapped_area_um2':data['area'],'elapsed_s':time.monotonic()-start})
        print('CONTROLLER_ADC_AREA',name,data['num_cells'],f"{data['area']:.6f}um2",flush=True)
    with (work/'costs.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    physical=[]
    views=[('core_reference',root/'inputs/core.lef'),('conditioner',root/'inputs/conditioner.lef'),('adc_full_macro',root/'inputs/adc.lef'),('readout',root/'inputs/digital_blocks/readout/automx_cim_readout_seq.lef'),('mha',root/'inputs/digital_blocks/mha/automx_mha_ip.lef')]
    if core_views:views.append(('core_delivered_pwm',Path(core_views)/'core.lef'))
    for name,path in views:
        match=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',path.read_text());assert match,(name,path)
        width,height=map(float,match.groups());physical.append({'macro':name,'width_um':width,'height_um':height,'footprint_um2':width*height})
    odbs=[('binary_reference',root/'inputs/digital_benchmarks/binary_reference/automx_cim_readout_seq.odb'),('calibration_gated',root/'inputs/digital_benchmarks/calibration_gated/automx_cim_readout_seq.odb'),('current_readout',root/'inputs/digital_blocks/readout/automx_cim_readout_seq.odb')]
    script=work/'routed_area.py';result_path=work/'routed_area.json'
    script.write_text('import odb,json\nrows=[]\nfor label,path in '+repr([(n,str(p)) for n,p in odbs])+':\n db=odb.dbDatabase.create();odb.read_db(db,path);b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()\n cells=list(b.getInsts());area=sum(i.getMaster().getWidth()*i.getMaster().getHeight()/u**2 for i in cells)\n rows.append(dict(design=label,routed_instances=len(cells),routed_stdcell_area_um2=area))\njson.dump(rows,open('+repr(str(result_path))+',"w"),indent=2)\nprint("OpenROAD ROUTED_STANDARD_CELL_AREAS",rows)\n')
    args=['docker','run','--rm','--network','none','--user',f'{os.getuid()}:{os.getgid()}','-v',str(root)+':'+str(root),'-w',str(work),'--entrypoint','openroad',image,'-exit','-python',str(script)]
    with (work/'routed_area.log').open('w') as log:q=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=120)
    assert q.returncode==0,(work/'routed_area.log').read_text()[-1000:]
    routed=json.loads(result_path.read_text());print('ROUTED_AREA',routed,flush=True)
    report={'status':'PASS','designs':rows,'physical_macros':physical,'routed_standard_cells':routed,'scope':'Mapped standard-cell areas with the same Yosys/ABC image and SKY130 TT Liberty; macro footprint and analog layout area are separate quantities.'}
    (work/'verification.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--work',type=Path,required=True);p.add_argument('--readout',type=Path);p.add_argument('--core-views',type=Path);a=p.parse_args();run(a.root,a.work,a.readout,a.core_views)
