"""Measured development history, embedded visibly in notebook cells."""
from pathlib import Path
from collections import Counter
import hashlib,json,re
from IPython.display import Markdown,display

EVIDENCE={}
BASE='results/sky130/'
PHYSICAL=BASE+'flow2_wrapper_integration/'


def fingerprint(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read_report(root,relative):
    path=Path(root)/relative
    data=json.loads(path.read_text())
    EVIDENCE[relative]={'path':str(path),'sha256':fingerprint(path)}
    return data


def table(headers,rows):
    def safe(value):return str(value).replace('|',' / ').replace('\n',' ')
    display(Markdown('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+
        '\n'.join('| '+' | '.join(safe(v) for v in row)+' |' for row in rows)))


def linked(root,child,field,parent):
    """Verify a recorded input digest, rather than infer dependency from ordering."""
    data=read_report(root,child)
    for key in field.split('.'):data=data[key]
    actual=fingerprint(Path(root)/parent)
    if data!=actual:raise ValueError(f'Historical dependency changed: {child}:{field} -> {parent}')
    return {'parent':parent,'child':child,'input_field':field,'sha256':actual,'verified':True}


def transfer_error(root):
    """Display actual reversed sum pairs from the native PEX campaign."""
    relative=BASE+'core_transfer_diagnostics/measured.json'
    data=read_report(root,relative);rows=[]
    for column in data['analysis']['columns']:
        for pair in column['overlaps']:
            low=pair['lower_sum_case'];high=pair['higher_sum_case']
            rows.append([column['column'],low['case'],pair['lower_sum'],low['diff_v'],high['case'],pair['higher_sum'],high['diff_v'],round(pair['reversal_v']*1000,4)])
    print('ARCHIVED MEASUREMENT — ngspice PEX; completed/planned:',data['completed_sims'],data['planned_sims'])
    table(['Cột','Case thấp','Sum thấp','ΔV thấp / V','Case cao','Sum cao','ΔV cao / V','Đảo mức / mV'],rows)
    EVIDENCE['transfer_reversals']={'source':relative,'measured_pairs':len(rows),'rows':rows}
    return rows


def candidate_result(root):
    data=read_report(root,BASE+'core_candidate_full_tt/measured.json')
    cols=data['analysis']['samples']['1.9']['columns']
    print('Sau sweep tải và PWM: C =',data['load_ff'],'fF; PWM =',data['pwm_unit_ps'],'ps;',data['completed_sims'],'/',data['planned_sims'],'native PEX jobs')
    table(['Cột','Số mức đã đo','Gap nhỏ nhất / mV','Overlap'],[
        [c['column'],c['measured_sum_levels'],round(c['min_adjacent_gap_v']*1000,4),c['overlap_count']] for c in cols])
    return cols


def decoder_errors(root):
    relative=BASE+'post49_decoder_diagnostic.json';data=read_report(root,relative);a=data['analysis']
    all_rows=[dict(row,column=c['column']) for c in a['columns'] for row in c['details']]
    wrong=[r for r in all_rows if r['expected_sum']!=r['predicted_sum']]
    if len(all_rows)!=a['sample_count'] or len(wrong)!=a['decode_mismatches']:raise ValueError('Decoder detail/count mismatch')
    print(f'ARCHIVED ERROR — scalar decoder: {len(wrong)}/{len(all_rows)} sai ({len(wrong)/len(all_rows):.3%}); 16 holdout patterns × 4 cột × 2 thời điểm.')
    table(['Case','Cột','Thời điểm','Sum đúng','Sum giải mã','ΔV / V','Mức chưa có khi train'],[
        [r['case'],r['column'],r['time'],r['expected_sum'],r['predicted_sum'],r['diff_v'],r['expected_sum_unseen_in_training']] for r in wrong[:12]])
    expanded=read_report(root,BASE+'post49_calibration_tt/measured.json')
    gap=expanded['feature_screens']['differential_v']['minimum_gap_equivalent_v']
    print(f'Bổ sung {expanded["completed_sims"]} case calibration: minimum differential gap = {gap*1000:.4f} mV. Dữ liệu đảo mức này dẫn tới thử nghiệm chia 2+2 hàng.')
    EVIDENCE['decoder_errors']={'source':relative,'mismatches':len(wrong),'samples':len(all_rows),'wrong_examples':wrong[:12],'expanded_gap_v':gap}
    return wrong


def partition_result(root):
    import matplotlib.pyplot as plt
    targeted=read_report(root,BASE+'post49_row_partition/adjacent/measured.json')
    cal=read_report(root,BASE+'post49_partition_full_tt/calibration/measured.json')
    held=read_report(root,BASE+'post49_partition_full_tt/holdout/measured.json');a=held['analysis']['combined']
    before=read_report(root,BASE+'post49_decoder_diagnostic.json')['analysis']
    before_wrong=before['decode_mismatches'];before_samples=before['sample_count']
    wrong=sum(r['expected_sum']!=r['predicted_sum'] for r in a['details'])
    if len(a['details'])!=a['samples'] or wrong!=a['decode_mismatches']:raise ValueError('2+2 detail/count mismatch')
    print('Can thiệp: precharge và đọc riêng hàng [0,1], [2,3], giải mã từng phần rồi cộng số.')
    print('Targeted jobs:',targeted['completed_sims'],'/',targeted['planned_sims'],'; full signed calibration:',cal['completed_sims'],'/',cal['planned_sims'])
    gaps=[v['threshold_training']['minimum_gap_equivalent_v']*1000 for v in cal['analysis']['phases'].values()]
    table(['Phép đo','Tập dữ liệu','Kết quả'],[
        ['Scalar decoder trước sửa','16 patterns × 4 cột × 2 thời điểm',f'{before_wrong} / {before_samples} decode errors'],
        ['2+2 calibration phase A','39 partial-sum levels',f'{gaps[0]:.4f} mV minimum gap'],
        ['2+2 calibration phase B','39 partial-sum levels',f'{gaps[1]:.4f} mV minimum gap'],
        ['2+2 frozen decoder','32 fresh patterns × 4 cột × 2 thời điểm',f'{wrong} / {a["samples"]} decode errors']])
    display(Markdown('Hai tập holdout có kích thước và pattern khác nhau; đây là hai mốc phát triển với denominator riêng. Ngưỡng 2+2 lấy từ calibration đã khóa trước khi đọc fresh holdout.'))
    fig,axes=plt.subplots(1,2,figsize=(11,3.4),layout='constrained')
    axes[0].bar([f'Scalar\n{before_wrong}/{before_samples}\n16 patterns',f'2+2\n{wrong}/{a["samples"]}\n32 fresh patterns'],[100*before_wrong/before_samples,100*wrong/a['samples']],color=['#c44e52','#55a868']);axes[0].set_ylabel('Measured decode errors / %')
    axes[1].bar(['Phase A','Phase B'],gaps,color='#4c72b0');axes[1].axhline(cal['analysis']['minimum_required_gap_v']*1000,color='gray',ls='--',label='Recorded target');axes[1].set_ylabel('Measured calibration minimum gap / mV');axes[1].legend()
    plt.show();plt.close(fig)
    EVIDENCE['partition_decode']={'samples':a['samples'],'mismatches':wrong,'minimum_gaps_mv':gaps,'source':BASE+'post49_partition_full_tt/holdout/measured.json'}
    return a


def routing_progress(root):
    """Parse real independent OpenROAD reports, including indented violations."""
    import matplotlib.pyplot as plt
    rows=[];records=[]
    for suffix in ('05','06','07','08'):
        tag='antenna_safe_srv_20261022_'+suffix
        data=read_report(root,PHYSICAL+tag+'/summary.json')
        report=Path(root)/'build/flow2_wrapper_integration'/tag/'independent.drc'
        text=report.read_text();counts=Counter(re.findall(r'^\s*violation type:\s*(.+?)\s*$',text,re.M))
        # An empty file alone is insufficient: bind it to a finished tool/log receipt.
        check=data['checks']['subset'];log=Path(root)/check['log']['path'];native=log.read_text()
        if check['returncode']!=0 or fingerprint(log)!=check['log']['sha256'] or 'AUTOMX_SUBSET_DRC_DONE' not in native:raise ValueError('Independent DRC did not finish')
        if report.stat().st_size!=data['independent_drc_bytes']:raise ValueError('DRC report size changed')
        odb=Path(root)/data['candidate_odb']['path']
        if odb.is_file() and fingerprint(odb)!=data['candidate_odb']['sha256']:raise ValueError('Candidate ODB changed')
        if suffix=='08' and not odb.is_file():raise FileNotFoundError(odb)
        rows.append([suffix,len(data['rollback_nets']),sum(counts.values()),counts.get('Short',0),counts.get('Cut Short',0)])
        records.append({'iteration':suffix,'markers':sum(counts.values()),'counts':dict(counts),'report':{'path':str(report),'sha256':fingerprint(report)},'log':check['log'],'candidate_odb':data['candidate_odb']})
        if suffix=='05':
            print('ARCHIVED VIOLATION — OpenROAD native report:',report)
            print('\n'.join(text.splitlines()[:10]))
    table(['ECO lần','Net route được khôi phục','Independent DRC markers','Short','Cut Short'],rows)
    print('Thay đổi: khôi phục có chọn lọc các net route xung đột sau diode ECO; từng candidate được kiểm lại bằng independent OpenROAD DRC.')
    log=Path(root)/records[-1]['log']['path'];native=log.read_text().splitlines()
    print('SAVED NATIVE OPENROAD LOG:',log)
    print('\n'.join(native[:3]+[line for line in native if 'AUTOMX_SUBSET_DRC_DONE' in line]))
    fig,ax=plt.subplots(figsize=(8,3),layout='constrained');ax.plot([r[0] for r in rows],[r[2] for r in rows],'o-');ax.set_xlabel('ECO iteration');ax.set_ylabel('Independent OpenROAD DRC markers');ax.grid(alpha=.25)
    for row in rows:ax.annotate(str(row[2]),(row[0],row[2]),xytext=(0,7),textcoords='offset points')
    plt.show();plt.close(fig)
    EVIDENCE['routing']=records
    return records


def dependencies(root,flow):
    """Show concrete old-to-new input edges and separately identify design rationale."""
    book=json.loads((Path(root)/'AutoMX_CIM_Sky130_MHA.ipynb').read_text())
    mapping={r['original_id']:r['original_index']+1 for r in book['metadata']['automx']['historical_cell_mapping']}
    recipes={c.get('metadata',{}).get('historical_recipe'):c for c in book['cells'] if c.get('metadata',{}).get('historical_recipe')}
    stages=[
        ('original-012','MHA numerical reference','Oracle số để so kết quả projection và attention.'),
        ('original-014','Tile schedule','Thứ tự dependency Q/K/V → attention → O và transaction controller.'),
        ('c4dd9fe2','Stage 5 GDS/LEF/PEX','Netlist PEX đầu vào của coverage và sweep transfer.'),
        ('core-pex-coverage-run','101-case PEX coverage','Chọn cặp khó để chẩn đoán đảo mức.'),
        ('b10e6122','Transfer diagnosis','Cặp đảo mức làm đầu vào sweep tải/PWM.'),
        ('core-candidate-full-tt-run','800 fF / 50 ps full TT','Dữ liệu training ngưỡng scalar decoder.'),
        ('post49-decoder-diagnostic-run','52/128 decoder errors','Chẩn đoán thiếu mức và mở rộng calibration.'),
        ('post49-partition-full-cal-run','2+2 signed calibration','Ngưỡng frozen cho fresh holdout.'),
        ('post49-partition-full-holdout-run','0/256 decode errors','Kết quả kiểm cách đọc 2+2; tiền đề protocol RTL.'),
        ('stage7-two-read-regression','Two-read RTL regression','Kiểm trình tự đọc và phép cộng partial sum.')]
    table(['Cell trong bản 127 cell (đếm từ 1)','Kết quả cũ','Vai trò ở bước sau'],[
        [mapping[recipes[key]['metadata']['original_cell_id']],title,role] for key,title,role in stages])
    pairs=[
      ('../receipts/physical/core_pex_coverage.json','stage5_summary_sha256','../receipts/physical/stage5_summary.json'),
      ('core_transfer_diagnostics/measured.json','coverage_receipt_sha256','../receipts/physical/core_pex_coverage.json'),
      ('core_candidate_full_tt/measured.json','stage4p8_sha256','core_candidate_pex/measured.json'),
      ('post49_decoder_diagnostic.json','cell49_sha256','core_candidate_full_tt/measured.json'),
      ('post49_decoder_diagnostic.json','holdout_sha256','post49_holdout_tt/measured.json'),
      ('post49_row_partition/adjacent/measured.json','input_report_sha256.calibration','post49_calibration_tt/measured.json'),
      ('post49_partition_full_tt/calibration/measured.json','targeted_sha256','post49_row_partition/adjacent/measured.json'),
      ('post49_partition_full_tt/holdout/measured.json','calibration_sha256','post49_partition_full_tt/calibration/measured.json')]
    edges=[linked(root,BASE+child,field,BASE+parent) for child,field,parent in pairs]
    table(['Kết quả tiền đề','Bước dùng kết quả'],[[e['parent'],e['child']] for e in edges])
    route=read_report(root,PHYSICAL+'antenna_safe_srv_20261022_08/summary.json')['candidate_odb']
    current=flow.outputs['route_checkpoint']
    if route['sha256']!=current['sha256'] or fingerprint(Path(current['path']))!=route['sha256']:raise ValueError('Final streamout did not use the measured route candidate')
    table(['Tuyến kế thừa','Vai trò ở kết quả sau'],[
        ['Stage 4/5 → PEX → sweep → decoder → 2+2','Kết quả đo lỗi quyết định bước sửa tiếp theo.'],
        ['MHA reference / vector / schedule → RTL regression','Oracle số và thứ tự Q/K/V/O của flow cũ làm nền cho kiểm RTL.'],
        ['2+2 calibration và holdout → lựa chọn cách đọc','Tiền đề thiết kế; nhánh SAR hiện tại tự hiệu chuẩn 3 conversion riêng.'],
        ['ECO08 ODB → DEF/LEF → GDS hiện tại','Checkpoint route được dùng để xuất DEF/LEF/GDS.'],
        ['3 native SAR calibration → 30 holdout patterns → 32 Q/K/V/O','Chuỗi dữ liệu đầu cuối của phép đo MHA hiện tại.']])
    display(Markdown('127 cell cũ bao gồm phần thuyết minh, cấu hình, đo kiểm và orchestration. Bảng này xác định những kết quả có quan hệ đầu vào cụ thể, cùng các kết quả làm tiền đề lựa chọn thiết kế.'))
    EVIDENCE['verified_dependency_edges']=edges
    EVIDENCE['final_route_dependency']={'candidate':route,'streamout_route':current,'verified':True}
    path=flow.work/'measured_development_story.json';path.write_text(json.dumps(EVIDENCE,indent=2,ensure_ascii=False)+'\n')
    flow.outputs['measured_development_story']={'path':str(path),'sha256':fingerprint(path)}
    print('Measured development receipt:',path)
    return edges


def final_results(flow):
    """Conclude with measured outputs of this Run All session."""
    mha=json.loads(Path(flow.outputs['analog_adc_mha']['path']).read_text())
    geometry=json.loads(Path(flow.outputs['gds_geometry_proof']['path']).read_text())
    table(['Kết quả cuối','Giá trị','Nguồn'],[
        ['Analog/SAR calibration',str(mha['calibration']['measured_ADC_codes']),'3 native conversion receipts'],
        ['Q/K/V/O',str(mha['projection_transactions'])+' transactions / '+str(mha['unique_holdout_patterns'])+' unique holdout patterns','mha_end_to_end.json'],
        ['MHA relative L2 / quantized-context reference',mha['relative_l2'],'mha_end_to_end.json'],
        ['MHA relative L2 / floating-context reference',mha['floating_reference_relative_l2'],'mha_end_to_end.json'],
        ['GDS geometry',json.dumps(geometry),'gds_geometry_proof'],
        ['Timing digital TT / 25 MHz',json.dumps({k:v for k,v in flow.outputs['nominal_timing'].items() if k!='scope'}),'OpenRCX / OpenSTA'],
        ['Top GDS',flow.outputs['gds']['path'],'KLayout streamout']])
    return geometry
