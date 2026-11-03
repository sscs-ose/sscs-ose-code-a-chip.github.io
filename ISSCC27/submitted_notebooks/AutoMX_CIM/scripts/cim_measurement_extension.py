"""Notebook authoring: measured cost tables, matched PWM control and fixed renders.
All runtime implementations are inserted literally into notebook cells.
"""
from pathlib import Path
import copy
import nbformat as nbf

PEX_BATCH = r'''import ctypes as C,sys,re
lib=C.CDLL(sys.argv[1]);errors=[]
CB=C.CFUNCTYPE(C.c_int,C.c_char_p,C.c_int,C.c_void_p)
def output(message,*_):
    text=message.decode(errors='replace')
    if text.startswith(('stdout ','stderr ')):text=text[7:]
    print(text,flush=True)
    if re.search(r'(?i)\b(?:error:|fatal:)',text):errors.append(text)
    return 0
callback=CB(output);lib.ngSpice_Init(callback,None,None,None,None,None,None)
lib.ngSpice_Command.argtypes=[C.c_char_p];lib.ngSpice_Command.restype=C.c_int
for command in ['set ngbehavior=hsa','set skywaterpdk','set num_threads=1','version','source '+sys.argv[2],'run']:
    code=lib.ngSpice_Command(command.encode())
    if code or errors:raise RuntimeError('ngspice failed: '+command+' '+str(errors))
'''

ARCHITECTURE = r'''## Kiến trúc lưu trọng số, tính analog và khôi phục attention

**Thực hiện:** Nối hợp đồng số tới các chân transistor rồi theo từng phép đo đến đầu ra ứng dụng.

| Khối | Dữ liệu nhận và lưu | Hoạt động thực hiện | Dữ liệu chuyển tiếp |
|---|---|---|---|
| Thanh ghi controller | 16 trọng số ternary, mỗi trọng số dùng hai bit `WPOS/WNEG` | Giữ mask dấu trong suốt evaluation; phát điều khiển precharge, track và chọn cột | Gate của transistor weight trong từng cell 8T |
| Bộ phát input | Bốn mã signed `ACT_X2` | Dấu chọn `WLP/WLN`; độ rộng xung PWM tỷ lệ trị tuyệt đối | Gate của transistor activation, dùng chung theo hàng |
| Cell 8T và core 4×4 | Bốn nhánh, mỗi nhánh có hai NMOS nối tiếp | AND điện của input/weight chọn bitline dương hoặc âm; các hàng cộng điện tích trên cột | `BLP/BLN` chứa kết quả analog |
| Acquisition và conditioner | Bốn cặp bitline | Lấy mẫu/giữ, đệm và ghép kênh | `AINP/AINN` đưa đến ADC |
| SAR và ADC | Điện áp vi sai, quyết định comparator | SAR (Successive Approximation Register) RTL điều khiển vòng tìm mã; SPICE giải transistor comparator/sampler | Mã ADC, EOC (End Of Conversion), trace từng quyết định |
| Calibration và projection | Mã ADC cùng ba điểm hiệu chuẩn độc lập | Khóa slope/offset, khôi phục tổng nguyên rồi áp scale | Q/K/V và phép chiếu O đo từ mạch |
| MHA trên CPU | Q/K/V đo được, hai attention head | Tính score, softmax và context; lượng tử context trước phép chiếu O | Đầu ra tiny-MHA và sai số với reference cùng lượng tử |

Cell 8T là **phần tử tính nhận trọng số từ thanh ghi controller**, không chứa latch SRAM lưu weight. CIM
(Compute-in-Memory) ở đây mô tả mặt phẳng cộng analog gắn với giao diện trọng số; bảng chi phí luôn tính riêng controller lưu mask.
Giá trị của tích hợp CIM–SAR–MHA là kiểm được cùng một chuỗi: thay đổi điện áp vật lý → mã ADC thật từ vòng SAR → tổng nguyên → tensor ứng dụng.
Các quyết định không dừng ở oracle Python; mỗi dot product cần record conversion khớp payload và calibration đã khóa.

**Đầu vào → đầu ra:** block số/weight → pin `WLP/WLN/WPOS/WNEG` → điện áp giữ → code → tổng nguyên → projection.
Mạch vật lý có bốn cột; bài chứng minh dùng một cột theo thời gian. Một conversion là dot product 4 phần tử;
một stage Q/K/V/O của ví dụ 2×4 gồm 8 conversion; cả ví dụ dùng 32 giao dịch projection.

| Đường triển khai | Cách khôi phục tổng | Lịch conversion |
|---|---|---|
| Chứng minh transistor/SAR/MHA và bảng năng lượng | Fit affine ba điểm độc lập, khóa trước holdout | Một dot 4 hàng/conversion, một cột được tái sử dụng |
| Sequencer của top vật lý | LUT 304 ngưỡng 12 bit, kèm 304 bit valid | Hai phase 2+2 hàng, hai conversion cho mỗi cột |

LUT của top chứa 3.648 bit ngưỡng bên cạnh mask weight 32 bit; diện tích controller đo ở cuối bao gồm cả phần này.
Bảng năng lượng gắn với đường chứng minh partition; bảng diện tích gắn với macro và sequencer được triển khai vật lý.
Bảng PEX đầu flow đo cửa sổ 0–3 ns ở tải quét; bảng conversion tích phân từ operating point đã precharge tới đoạn giữ sau EOC.
Mỗi bảng đối chiếu baseline trong cùng mạch, cửa sổ và chính sách kích thích của thí nghiệm đó.
'''

EARLY = r'''%%cim_lesson measured-checkpoints
edu_table(['w','sign(A)','I_P − I_N đo / µA','Dấu oracle','Sai lệch dấu'],
 [[r['weight'],r['activation_sign'],f"{r['differential_current_a']*1e6:.6f}",r['truth_sign'],
   int((abs(r['differential_current_a'])>1e-10 if r['truth_sign']==0 else r['differential_current_a']*r['truth_sign']<=0))]
  for r in EDU_LEAF_MEASURED])
edu_table(['Mốc kiểm','Giá trị từ cấu trúc đã dựng/đo','Kết quả làm đầu vào bước sau'],[
 ['Bảng logic',len(EDU_ALPHABET)*3,'45 tổ hợp activation/weight khớp tích nguyên'],
 ['DC transistor',len(EDU_LEAF_MEASURED),'9 trạng thái dấu/zero từ ngspice TT'],
 ['Core: chân',len(EDU_CORE.splitlines()[0].split()[2:]),'Hợp đồng nối netlist core'],
 ['Core: leaf',sum(l.startswith('XCOL') for l in EDU_CORE.splitlines())*4,'16 leaf × 8 NMOS'],
 ['Block32: sai số lớn nhất',float(np.max(abs(edu_y-edu_reference))),'Kiểm phép chia lát và áp scale'],
 ['Block32: partial sums',list(edu_partial.shape),'8 lát × 4 cột'],
])
(EDU_OUT/'first_checkpoints.json').write_text(json.dumps({'dc9':EDU_LEAF_MEASURED,
 'logic_cases':len(EDU_ALPHABET)*3,'core_pins':len(EDU_CORE.splitlines()[0].split()[2:]),
 'block32_max_error':float(np.max(abs(edu_y-edu_reference)))},indent=2))
'''

ENERGY_BASELINE = r'''from concurrent.futures import ThreadPoolExecutor
import subprocess,json,sys,numpy as np
from pathlib import Path
from automx_nb_inline_v1.support import save,item
meter_mha=json.loads((flow.work/'mha_end_to_end.json').read_text())
meter_baseline=flow.work/'matched_pwm100';meter_baseline.mkdir(exist_ok=False)
meter_sources={Path(j['case']['path']).parent.name:Path(j['case']['path']) for j in meter_mha['jobs']}
for meter_ref in experiment.calibration['source_cases'].values():
    meter_path=Path(meter_ref['path']);meter_sources[meter_path.parent.name]=meter_path
meter_tasks=[]
for meter_name,meter_summary in sorted(meter_sources.items()):
    meter_folder=meter_baseline/meter_name;meter_folder.mkdir()
    meter_case=json.loads((meter_summary.parent/'case.json').read_text());meter_case['pwm_unit_ps']=100
    save(meter_folder/'case.json',meter_case)
    meter_cmd=[sys.executable,'-u',str(Path(INLINE_ROOT)/'cosim.py'),'--root',str(ROOT),
      '--work',str(meter_folder),'--library',str(experiment.lib),'--case',str(meter_folder/'case.json')]
    meter_tasks.append((meter_folder,meter_cmd))
print('MATCHED BASELINE: PWM 100 ps/unit; candidate 50 ps/unit. Same payloads, TT/1.8 V/25 C, physical caps, sample timing, ADC, observation window.')
with ThreadPoolExecutor(max_workers=flow.settings.jobs) as meter_pool:
    meter_futures=[meter_pool.submit(subprocess.run,meter_cmd,text=True,stdout=subprocess.PIPE,
      stderr=subprocess.STDOUT,timeout=180,cwd=ROOT) for _,meter_cmd in meter_tasks]
    for (meter_folder,meter_cmd),meter_future in zip(meter_tasks,meter_futures):
        meter_result=meter_future.result();(meter_folder/'worker.log').write_text(meter_result.stdout)
        if meter_folder==meter_tasks[0][0]:
            print('\n'.join(line for line in meter_result.stdout.splitlines() if 'ngspice-' in line)[:200])
        if meter_result.returncode:print('\n'.join(meter_result.stdout.splitlines()[-12:]))
        if meter_result.returncode:raise RuntimeError('Baseline conversion failed: '+str(meter_folder/'worker.log'))
meter_cal=[]
for meter_ref in experiment.calibration['source_cases'].values():
    meter_original=json.loads(Path(meter_ref['path']).read_text())
    meter_control=json.loads((meter_baseline/Path(meter_ref['path']).parent.name/'summary.json').read_text())
    meter_cal.append((meter_original['expected_integer_sum'],meter_control['result_code_12bit']))
meter_slope,meter_offset=np.polyfit(*np.array(meter_cal).T,1)
if abs(meter_slope)<1:raise ValueError('Baseline calibration has no usable span')
meter_baseline_meta={'pwm_unit_ps':100,'candidate_pwm_unit_ps':50,'calibration':meter_cal,
 'slope':float(meter_slope),'offset':float(meter_offset),'unique_patterns':len(meter_tasks),
 'fixed_conditions':{'corner':'tt','vdd_v':1.8,'temperature_c':25,'analog_source':'same core/conditioner/ADC',
 'load':'same physical MIM capacitance','payload':'identical activation and weights','sampling':'same PRE/TRACK/START timing'},
 'independent_calibration':True}
save(meter_baseline/'comparison_conditions.json',meter_baseline_meta)
print('Baseline conversions:',len(meter_tasks))
print('Calibration (sum, ADC code):',meter_cal)
print('Slope / offset:',float(meter_slope),float(meter_offset))
'''

ENERGY_TABLE = r'''import json,numpy as np
from pathlib import Path
from IPython.display import Markdown,display
meter_columns=['core_acquisition_vdd_j','conditioner_vdd_j','adc_vdd_j','adc_bridge_net_j','monitored_total_j']
meter_job_rows=[]
for meter_job in meter_mha['jobs']:
    meter_candidate=json.loads(Path(meter_job['case']['path']).read_text())
    meter_control=json.loads((meter_baseline/Path(meter_job['case']['path']).parent.name/'summary.json').read_text())
    for meter_label,meter_result,meter_fit in [('PWM50',meter_candidate,(experiment.slope,experiment.offset)),
                                             ('PWM100 baseline',meter_control,(meter_slope,meter_offset))]:
        meter_energy=meter_result['energy'];meter_decoded=int(np.rint((meter_result['result_code_12bit']-meter_fit[1])/meter_fit[0]))
        meter_job_rows.append({'mode':meter_label,'stage':meter_job['stage'],'row':meter_job['row'],
         'column':meter_job['column'],'expected':meter_job['reference_integer_sum'],'decoded':meter_decoded,
         'code':meter_result['result_code_12bit'],'window_ns':meter_energy['duration_s']*1e9,
         'start_to_eoc_ns':meter_result['start_to_eoc_s']*1e9,
         **{k:meter_energy[k] for k in meter_columns}})
display(Markdown('| Mode | Stage | Dot | ADC code | Sum ref / decoded | VDD core / pJ | Conditioner / pJ | ADC VDD / pJ | ADC bridge net / pJ | Total monitored / pJ |\n|---|---|---|---|---|---|---|---|---|---|\n'+'\n'.join(
 f"| {r['mode']} | {r['stage']} | {r['row']},{r['column']} | {r['code']} | {r['expected']} / {r['decoded']} | "+' | '.join(f"{r[k]*1e12:.5f}" for k in meter_columns)+' |' for r in meter_job_rows)))
meter_aggregate=[]
for meter_mode in ['PWM50','PWM100 baseline']:
    for meter_stage in ['Q','K','V','O','ALL']:
        meter_group=[r for r in meter_job_rows if r['mode']==meter_mode and (meter_stage=='ALL' or r['stage']==meter_stage)]
        meter_aggregate.append({'mode':meter_mode,'stage':meter_stage,'conversions':len(meter_group),
         'decode_errors':sum(r['decoded']!=r['expected'] for r in meter_group),
         'energy_pj':sum(r['monitored_total_j'] for r in meter_group)*1e12,
         'mean_conversion_pj':np.mean([r['monitored_total_j'] for r in meter_group])*1e12,
         'mean_start_to_eoc_ns':np.mean([r['start_to_eoc_ns'] for r in meter_group]),
         'adc_share_percent':100*sum(r['adc_vdd_j']+r['adc_bridge_net_j'] for r in meter_group)/sum(r['monitored_total_j'] for r in meter_group)})
display(Markdown('| Mode | Projection | Conversions | Decode errors | Energy/projection / pJ | Mean/conversion / pJ | START→EOC / ns | ADC share / % |\n|---|---|---|---|---|---|---|---|\n'+'\n'.join(
 f"| {r['mode']} | {r['stage']} | {r['conversions']} | {r['decode_errors']} | {r['energy_pj']:.5f} | {r['mean_conversion_pj']:.5f} | {r['mean_start_to_eoc_ns']:.3f} | {r['adc_share_percent']:.2f} |" for r in meter_aggregate)))
meter_energy_report={'conditions':meter_baseline_meta,'per_conversion':meter_job_rows,'per_projection':meter_aggregate,
 'scope':'Transient energy on measured analog VDD rails plus net work of ideal ADC bottom/sample/clock voltage bridges; excludes RTL internal switching, input/weight driver generation, CPU softmax and DC operating-point initialization. Same 0-to-stable-EOC observation window policy for both modes.',
 'reuse':'Each logical dot is charged once; identical payload simulations may be deduplicated within the current run. No energy assigned to CPU softmax.',
 'integration':'Trapezoidal integral of instantaneous voltage times current; signed net bridge work retains returned charge.'}
save(flow.work/'energy_comparison.json',meter_energy_report);flow.outputs['energy_comparison']=item(flow.work/'energy_comparison.json')
print(meter_energy_report['scope'])
'''

AREA = r"""import json,re
from pathlib import Path
from IPython.display import Markdown,display
meter_area_dir=flow.work/'area_inventory';meter_area_dir.mkdir()
meter_odb=portable.inputs(flow)[1]['odb']
meter_tcl=meter_area_dir/'inventory.tcl';meter_area_json=meter_area_dir/'placed_area.json'
meter_tcl.write_text('read_db {'+str(meter_odb)+r'''}
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set die [$block getDieArea]
set die_area [expr {double([$die dx])*[$die dy]/$dbu/$dbu}]
set macro 0.0;set logic 0.0;set physical 0.0;set count 0
foreach inst [$block getInsts] {
 set master [$inst getMaster]
 set a [expr {double([$master getWidth])*[$master getHeight]/$dbu/$dbu}]
 if {[$master isBlock]} {set macro [expr {$macro+$a}]} elseif {[regexp {SPACER|WELLTAP|ENDCAP|TAPCELL} [$master getType]]} {set physical [expr {$physical+$a}]} else {set logic [expr {$logic+$a}];incr count}
}
set f [open {'''+str(meter_area_json)+r'''} w]
puts $f [format {"die_um2":%.9f,"macro_um2":%.9f,"placed_logic_um2":%.9f,"physical_cells_um2":%.9f,"logic_instances":%d} $die_area $macro $logic $physical $count]
close $f
puts "MEASURED_PLACED_AREA die=$die_area macro=$macro logic=$logic physical=$physical instances=$count"
exit
''')
flow.run('measured_area',portable.container(ROOT,'openroad',['-exit',meter_tcl],'automx-area-'+str(__import__('os').getpid()),meter_area_dir),
 inputs=[meter_odb,meter_tcl],outputs=[meter_area_json],cwd=meter_area_dir,timeout_s=90)
meter_placed=json.loads('{'+meter_area_json.read_text().strip()+'}')
meter_areas=[]
for meter_file,meter_name in [('core','Core + acquisition'),('conditioner','Conditioner + mux'),('adc','ADC macro (analog + internal digital)')]:
    meter_lef=(ROOT/'inputs'/f'{meter_file}.lef').read_text();meter_w,meter_h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',meter_lef).groups())
    meter_areas.append({'block':meter_name,'area_um2':meter_w*meter_h,'source':str(ROOT/'inputs'/f'{meter_file}.lef'),'kind':'macro footprint'})
meter_areas += [{'block':'Placed wrapper/controller + CTS/buffers','area_um2':meter_placed['placed_logic_um2'],'source':str(meter_odb),'kind':'placed standard-cell master area'},
 {'block':'Die bounding area','area_um2':meter_placed['die_um2'],'source':str(meter_odb),'kind':'die footprint'}]
# Independent synthesis measures controller and SAR in the same library/flow.
meter_lib=ROOT/'pdks/digital/sky130A/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__tt_025C_1v80.lib'
for meter_top,meter_sources_area in [('automx_cim_readout_seq',[ROOT/'rtl/automx_cim_readout_seq.sv']),
 ('adc_core_digital',[ROOT/'third_party/SKY130_SAR_ADC1/mixed_signal_partition/verilog/rtl'/x for x in ['adc_control_nonbinary.v','adc_row_col_decoder.v','adc_osr.v','adc_core_digital.v']])]:
    meter_ys=meter_area_dir/(meter_top+'.ys');meter_stat=meter_area_dir/(meter_top+'.stat.json')
    meter_ys.write_text(f'read_liberty -lib "{meter_lib}"\n'+''.join(f'read_verilog -sv "{p}"\n' for p in meter_sources_area)+
     f'hierarchy -check -top {meter_top}\nsynth -top {meter_top} -flatten\ndfflibmap -liberty "{meter_lib}"\nabc -liberty "{meter_lib}"\nclean\n'+
     f'tee -o {meter_stat} stat -json -liberty "{meter_lib}"\n')
    flow.run('area_'+meter_top,portable.container(ROOT,'yosys',['-s',meter_ys],'automx-area-'+meter_top,meter_area_dir),
     inputs=[meter_ys,meter_lib,*meter_sources_area],outputs=[meter_stat],cwd=meter_area_dir,timeout_s=180)
    meter_stats=json.loads(meter_stat.read_text());meter_module=next(iter(meter_stats['modules'].values()))
    meter_areas.append({'block':meter_top,'area_um2':meter_module['area'],'cells':meter_module['num_cells'],
      'source':str(meter_stat),'kind':'TT mapped cell area; same synthesis recipe'})
display(Markdown('| Block | Area / µm² | Meaning | Source |\n|---|---|---|---|\n'+'\n'.join(
 f"| {r['block']} | {r['area_um2']:.3f} | {r['kind']} | `{Path(r['source']).name}` |" for r in meter_areas)))
assert abs(sum(r['area_um2'] for r in meter_areas[:3])-meter_placed['macro_um2'])<1.0
save(flow.work/'area_comparison.json',{'blocks':meter_areas,'placed':meter_placed,
 'baseline':'PWM100 and PWM50 use identical physical hardware: area delta = 0. Only input pulse width is changed.',
 'accounting':'ADC macro already contains its native digital; separately synthesized SAR is a reference breakdown, never added twice to top area.'})
flow.outputs['area_comparison']=item(flow.work/'area_comparison.json')
print('PWM100 vs PWM50 physical area change: 0 µm² (same hardware). Controller storage/decoder cost is included; SAR reference is not double-counted in ADC macro.')
"""


def patch_sources(book):
    cells={c.id:c for c in book.cells}
    render=(Path(__file__).parent/'render_flow2_wrapper_gds.py').read_text()
    cells['native-inline-klayout-render-source'].source='%%native_lab inline-klayout-render-source\n%%eda_source render_flow2_wrapper_gds.py\n'+render
    cells['klayout-script'].source='%%design_review klayout-script\nKLAYOUT_SCRIPT = '+repr(render)+'\n'
    render_cell=cells['native-runall-render-top']
    if 'top_routing_detail' not in render_cell.source:
        render_cell.source=render_cell.source.replace('def render(self,gds,top,name):',"def render(self,gds,top,name,mode='overview'):")
        render_cell.source=render_cell.source.replace("'AUTOMX_TOP':top}","'AUTOMX_TOP':top,'AUTOMX_RENDER_MODE':mode}")
        render_cell.source+='\nprint("Detailed view: met1–met5, same GDS and placement.")\ntop_render.render(flow,top_gds,geometry_common.TOP,"top_routing_detail",mode="detail")\n'
    cosim=cells['native-inline-cosim'].source
    if '# ENERGY_METERS_V1' not in cosim:
        cosim=cosim.replace('column,total,model_override=None):','column,total,model_override=None,pwm_unit_ps=50):')
        cosim=cosim.replace('column=0,model_override=None):','column=0,model_override=None,pwm_unit_ps=50):')
        cosim=cosim.replace('column,total,model_override)','column,total,model_override,pwm_unit_ps)')
        cosim=cosim.replace('{magnitude*50}p','{magnitude*pwm_unit_ps}p')
        cosim=cosim.replace("'VVDD VPWR 0 1.8','VVCM VCM 0 .9',", "'VVDD VPWR 0 1.8','VVCM VCM 0 .9',\n        'VCORE_METER VPWR VDD_CORE 0','VCOND_METER VPWR VDD_COND 0','VADC_METER VPWR VDD_ADC 0',")
        cosim=cosim.replace("'0' if p=='VGND' else p for p in core.PINS", "'0' if p=='VGND' else ('VDD_CORE' if p=='VPWR' else p) for p in core.PINS")
        cosim=cosim.replace("'0' if p=='VGND' else p for p in design.COND_PINS", "'0' if p=='VGND' else ('VDD_COND' if p=='VPWR' else p) for p in design.COND_PINS")
        for prefix in ['XSP SAMPLE_N AINP SAMPLE CTOPP','XSN SAMPLE_N AINN SAMPLE CTOPN','XCOMP']:
            cosim=cosim.replace(prefix+' VPWR',prefix+' VDD_ADC')
        cosim=cosim.replace("    lines += ['.save '+' '.join(vectors[1:])", "    # ENERGY_METERS_V1: zero-volt series probes do not change the circuit.\n    vectors += ['v(VPWR)','v(VCM)','v(SAMPLE_N)',*('i('+name+')' for name in\n      ('VVDD','VCORE_METER','VCOND_METER','VADC_METER','VVCM','VBOTTOMP','VBOTTOMN','VSAMPLE','VSAMPLEN','VCLKCOMP'))]\n    lines += ['.save '+' '.join(vectors[1:])")
        cosim=cosim.replace("        report=dict(status=", """        meter_t=observed['time'];meter_v=observed['v(VPWR)']
        meter_int=np.trapezoid if hasattr(np,'trapezoid') else np.trapz
        meter_energy={'start_s':float(meter_t[0]),'end_s':float(meter_t[-1]),'duration_s':float(meter_t[-1]-meter_t[0])}
        for key,probe in [('core_acquisition_vdd_j','VCORE_METER'),('conditioner_vdd_j','VCOND_METER'),('adc_vdd_j','VADC_METER')]:
            meter_energy[key]=float(meter_int(meter_v*observed['i('+probe+')'],meter_t))
        meter_bridge=np.zeros_like(meter_t)
        for node,source in [('BOTTOMP','VBOTTOMP'),('BOTTOMN','VBOTTOMN'),('SAMPLE','VSAMPLE'),('SAMPLE_N','VSAMPLEN'),('ADC_CLK_COMP','VCLKCOMP'),('VCM','VVCM')]:
            meter_bridge-=observed['v('+node+')']*observed['i('+source+')']
        meter_energy['adc_bridge_net_j']=float(meter_int(meter_bridge,meter_t))
        meter_energy['monitored_total_j']=sum(meter_energy[k] for k in ('core_acquisition_vdd_j','conditioner_vdd_j','adc_vdd_j','adc_bridge_net_j'))
        meter_vdd=float(meter_int(-meter_v*observed['i(VVDD)'],meter_t))
        if not np.isclose(meter_vdd,sum(meter_energy[k] for k in ('core_acquisition_vdd_j','conditioner_vdd_j','adc_vdd_j')),rtol=1e-5,atol=1e-18):raise ValueError('VDD branch energy does not balance')
        (work/'energy.json').write_text(json.dumps(meter_energy,indent=2)+'\\n')
        print('MEASURED_ENERGY_J',json.dumps(meter_energy),flush=True)
        report=dict(energy=meter_energy,pwm_unit_ps=pwm_unit_ps,status=""")
        cosim=cosim.replace("data.get('column',0))", "data.get('column',0),pwm_unit_ps=data.get('pwm_unit_ps',50))")
        cells['native-inline-cosim'].source=cosim
    pilot=cells['native-inline-fresh-pilot'].source
    if 'shared_pex_batch.py' not in pilot:
        pilot=pilot.replace("    executable=shutil.which('ngspice')", "    worker=folder/'shared_pex_batch.py'\n    worker.write_text("+repr(PEX_BATCH)+")\n    executable=shutil.which('ngspice')")
        pilot=pilot.replace("command=[executable,'-b',str(deck)]", "command=[__import__('sys').executable,'-u',str(worker),str(root/'tools/ngspice/libngspice.so'),str(deck)]")
    if 'vdd_energy_j INTEG' not in pilot:
        pilot=pilot.replace('lines += [".tran 5p 3n",', 'lines += [".measure tran vdd_energy_j INTEG par(\'-v(VPWR)*i(VVDD)\') FROM=0 TO=3n", ".tran 5p 3n",')
        pilot=pilot.replace("        return {'case':name,", "        energy_match=re.search(r'vdd_energy_j\\s*=\\s*([-+\\deE.]+)',text,re.I)\n        if not energy_match:raise ValueError('PEX energy measurement missing')\n        return {'vdd_energy_j':float(energy_match[1]),'case':name,")
        pilot=pilot.replace("    print('Measured signed-level gap:'", "    display(Markdown('| Case | VDD energy, 0–3 ns / pJ |\\n|---|---|\\n'+'\\n'.join(f'| {r[\"case\"]} | {r[\"vdd_energy_j\"]*1e12:.6f} |' for r in jobs)))\n    print('Measured signed-level gap:'")
    cells['native-inline-fresh-pilot'].source=pilot
    return book


def insert_extensions(book):
    book=copy.deepcopy(book)
    prior={c.id:c for c in book.cells if c.id.startswith('meter-')}
    book.cells=[c for c in book.cells if not c.id.startswith('meter-')]
    def add(before,key,markdown,code=None):
        idx=next(i for i,c in enumerate(book.cells) if c.id==before)
        if idx and book.cells[idx-1].metadata.get('automx_explains')==before:
            idx-=1
        additions=[nbf.v4.new_markdown_cell(markdown,id='meter-'+key+'-theory')]
        if code:
            cell=nbf.v4.new_code_cell(code,id='meter-'+key)
            if cell.id in prior and prior[cell.id].source==code:
                cell.outputs=prior[cell.id].get('outputs',[]);cell.execution_count=prior[cell.id].get('execution_count')
                cell.metadata=copy.deepcopy(prior[cell.id].metadata)
            additions.append(cell)
        book.cells[idx:idx]=additions
    add('architecture','architecture',ARCHITECTURE)
    add('cim-edu-bridge','early-checkpoints',
        '### Bảng đo kiểm đầu tiên: từ logic đến dòng transistor và chia lát\n\n**Thực hiện:** Tổng hợp lại dữ liệu vừa tính và đo, giữ riêng logic 45 tổ hợp và ngspice DC 9 trạng thái. Nhận `EDU_LEAF_MEASURED`, netlist core và kết quả tiled projection; xuất bảng cùng `first_checkpoints.json`. Đây là checkpoint trước thí nghiệm PEX và ADC. µA là microampere; TT là corner typical; DC là trạng thái điện một chiều.',EARLY)
    add('standalone-sync-conversions','baseline',
        '### Baseline cùng phần cứng: thay riêng độ rộng PWM\n\n**Thực hiện:** Chạy lại chính các payload Q/K/V/O và ba điểm calibration với PWM 100 ps/unit, đối chiếu mode 50 ps/unit hiện tại. Giữ cùng TT, 1,8 V, 25 °C, nguồn netlist, tụ MIM, lịch PRE/TRACK/START và cửa sổ đo. Mỗi mode có fit calibration riêng, khóa trước chấm projection. PWM là Pulse-Width Modulation; ps là picosecond. Kết quả là conversion mới trong `matched_pwm100/`, không phải số liệu tham khảo cũ.',ENERGY_BASELINE)
    add('standalone-sync-conversions','energy',
        r'''### Năng lượng từng conversion và từng projection

**Thực hiện:** Tích phân waveform dòng/áp đã lưu từ lần mô phỏng này, cộng theo lịch Q/K/V/O. Các nguồn đo 0 V mắc nối tiếp chia VDD thành core/acquisition, conditioner và ADC mà không thay đổi điện áp cấp. ADC còn có phần công điện qua bridge CDAC, sample và clock, được ghi riêng theo dấu công nguồn.

$$E=\int_{t_0}^{t_1}v(t)i_{\mathrm{delivered}}(t)\,dt$$

**Đầu vào → đầu ra:** `coupled.raw` → tích phân trong `cosim.simulate` → `summary.json.energy` → bảng từng dot và tổng 8 conversion/stage → `energy_comparison.json`. Đơn vị pJ là picojoule. Mỗi dot trả một tổng 4 phần tử; tổng ALL gồm 32 giao dịch, chưa cộng công CPU softmax. Đây là năng lượng của các rail/bridge analog được đo; hoạt động nội bộ RTL controller không tự được gán bằng dòng của nguồn stimulus lý tưởng.''',ENERGY_TABLE)
    add('native-runall-streamout','area',
        '### Diện tích và chi phí controller/ADC\n\n**Thực hiện:** Đọc master footprint của ba macro từ LEF, kiểm tổng với ODB routed mới; tổng hợp riêng controller và SAR bằng cùng Yosys/Liberty TT. LEF là Layout Exchange Format; ODB là database OpenROAD; CTS là Clock Tree Synthesis. Diện tích master standard cell khác die footprint: bảng giữ rõ hai nghĩa. ADC macro đã gồm digital gốc; số SAR tổng hợp riêng dùng phân tích chi phí, không cộng lần nữa. Hai mode PWM dùng cùng phần cứng nên chênh diện tích bằng 0. Đầu vào là LEF/ODB/RTL của lượt này; đầu ra là report tool và `area_comparison.json`.',AREA)
    add('native-runall-render-top','render',
        '### Hình top GDS với cấu hình hiển thị cố định\n\n**Thực hiện:** KLayout đọc đúng GDS mới, dùng màu SKY130 cố định, tắt grid và nhãn chồng nhau. Hình tổng quan dùng met3–met5; hình chi tiết tiếp theo dùng met1–met5. Các lớp hiển thị được nêu trong log `shown_layers`; vùng mật độ standard cell là geometry thật của lần place-and-route hiện tại. Các hình macro dùng thêm lớp thiết bị. Cách vẽ không sửa polygon hay vị trí instance trong GDS. Bản render thứ hai ở cuối flow dùng cùng script và cấu hình để kiểm tính nhất quán.')
    return book
