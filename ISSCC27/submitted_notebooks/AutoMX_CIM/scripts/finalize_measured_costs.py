"""Publish a verified local execution, preserving every executable cell object."""
from pathlib import Path
import json,shutil,re
import nbformat
from scripts.enrich_cim_notebook import enrich

b=Path(__file__).resolve().parents[1]
executed=nbformat.read(b/'AutoMX_CIM_Code_a_Chip.executed.ipynb',4)
u=enrich(executed)
assert [c for c in executed.cells if c.cell_type=='code']==[c for c in u.cells if c.cell_type=='code']
assert len(u.cells)==383
report=json.loads((b/'docs/measured_costs_validation_20261026.json').read_text())
verified=json.loads((b/'standalone_verification.json').read_text())
assert report['status']=='PASSED' and verified['code_cells']==129
u.metadata['measured_costs']=report
md='\n'.join(c.source for c in u.cells if c.cell_type=='markdown')
anchors=re.findall(r'<a id="([^"]+)"',md)
refs=re.findall(r'\]\(#((?:fn-|guide-|data-|term-)[^)]+)\)',md)
assert not set(refs)-set(anchors)
for i,c in enumerate(u.cells):
    if c.cell_type=='code' and any(x.metadata.get('automx_explains')==c.id for x in u.cells):
        assert u.cells[i-1].metadata.get('automx_explains')==c.id
assert enrich(u)==u
nbformat.validate(u)
for name in ['AutoMX_CIM_Code_a_Chip.ipynb','AutoMX_CIM_Code_a_Chip.executed.ipynb']:
    nbformat.write(u,b/name)
w=Path(report['run'])/'full_native/full_native'
energy=json.loads((w/'energy_comparison.json').read_text())
area=json.loads((w/'area_comparison.json').read_text())
ca=report['candidate_all'];ba=report['baseline_all']
delta=100*(ca['mean_conversion_pj']/ba['mean_conversion_pj']-1)
cal=[]
for mode,folder in [('PWM50',w),('PWM100',w/'matched_pwm100')]:
    refs=json.loads((w/'calibration.json').read_text())['source_cases']
    cal.append([mode,sum(json.loads((folder/Path(v['path']).parent.name/'summary.json').read_text())['energy']['monitored_total_j'] for v in refs.values())*1e12])
readme_add=f'''## Bảng chi phí đo từ Run All — 2026-10-26

Bản hiện tại có **383 cells / 129 code cells**. Run All trong env_mamba hoàn tất **129/129**, không exception, **{verified['elapsed_s']/60:.2f} phút**. Kết quả: `runs/fresh_20261026_163634_350813/`.

- `meter-architecture-theory`: pin input/weight, nơi lưu weight, ranh giới transistor/SAR/CPU; phân biệt fit affine của partition với LUT 2+2 của top.
- `meter-early-checkpoints`: bảng logic, dòng DC 8T, số chân/leaf và sai số block32; các cell PEX thêm năng lượng VDD 0–3 ns vào log/table.
- `meter-baseline` / `meter-energy`: 33 pattern baseline mới, 64 dòng conversion và 10 dòng tổng hợp projection; PWM50 **{ca['mean_conversion_pj']:.3f} pJ/conversion**, PWM100 **{ba['mean_conversion_pj']:.3f} pJ/conversion**, cả hai 0 lỗi trên 32 giao dịch.
- `meter-area`: LEF/ODB và Yosys; controller **166.569,754 µm²**, SAR digital **8.415,571 µm²**. Footprint ADC macro **170.469 µm²** đã gồm digital gốc.
- KLayout dùng palette cố định: overview met3–met5, detail met1–met5, không chồng text. Hai cell render overview khớp từng pixel.

Năng lượng là tích phân rail analog và công net qua các bridge ADC trong cửa sổ transient từ operating point precharge tới đoạn giữ sau EOC. Switching nội bộ RTL/CPU được tách khỏi số analog này. Hai mode dùng cùng phần cứng, chỉ đổi PWM; mỗi mode có fit calibration riêng. Diện tích không đổi; mode50 tiêu thụ nhiều hơn **{delta:.3f}%** trong cửa sổ đo này. Calibration được tách khỏi 32 projection.

Kiểm độc lập: **74 waveform raw** được tích phân lại; tổng macro khớp ODB; payload baseline khớp; routing 0 violation. Xem `docs/measured_costs_validation_20261026.json`, `standalone_verification.json` và `docs/MEASURED_COSTS_PROGRESS_20261026.md`.

'''
for name in ['README.md','scripts/standalone_readme.md']:
    p=b/name;s=p.read_text().replace('**372 cells / 125 code cells**','**383 cells / 129 code cells**')
    first,rest=s.split('\n',1)
    if '## Bảng chi phí đo từ Run All — 2026-10-26' not in s:
        s=first+'\n\n'+readme_add+rest.lstrip('\n')
    p.write_text(s)
rows='\n'.join(f"| {r['block']} | {r['area_um2']:.4f} | {r['kind']} |" for r in area['blocks'])
prows='\n'.join(f"| {r['mode']} | {r['stage']} | {r['conversions']} | {r['decode_errors']} | {r['energy_pj']:.5f} | {r['mean_conversion_pj']:.5f} |" for r in energy['per_projection'])
(b/'docs/MEASURED_COSTS_PROGRESS_20261026.md').write_text(f'''# Đo chi phí và kiểm Run All — hoàn tất 2026-10-26

Notebook chính: `AutoMX_CIM_Code_a_Chip.ipynb` — 383 cells, 129 code cells.
Kernel: `/home/nam/anaconda3/envs/env_mamba/bin/python`.
Run: `{report['run']}`.
Log: `diagnostics/full_run_measured_costs_20261026.log`.

## Kiểm chạy

129/129 code cells đã chạy từ kernel mới, không exception, {verified['elapsed_s']/60:.3f} phút. Có 41 conversion chính, 33 conversion baseline bổ sung, 8 phép đo PEX. 38 holdout không lỗi giải mã; 32 projection MHA khớp tham chiếu cùng lượng tử. Top được dựng cold từ RTL/IP: routing 0 violation, signal macro-boundary LVS match, hai rail nguồn PASS. DRC giữ trạng thái timeout của deck bounded; TT setup/hold {verified['review']['setup_slack_ns']:+.2f}/{verified['review']['hold_slack_ns']:+.2f} ns, ghi đúng kết quả tool.

Kiểm độc lập ở `scripts/verify_measured_costs.py`: 74 waveform raw tích phân lại, lệch lớn nhất {report['maximum_energy_reintegration_difference_j']:.3e} J; 32 cặp payload khớp; tổng footprint macro khớp ODB; hai cell render overview khớp pixel.

## Năng lượng theo lịch projection

| Mode | Stage | Conversions | Decode errors | Energy/stage / pJ | Mean/conversion / pJ |
|---|---|---|---|---|---|
{prows}

Đây là năng lượng cấp trong cửa sổ transient của rail core/acquisition, conditioner, ADC và công net qua bridge ADC, giữ dấu năng lượng trả về. Operating point ban đầu đã precharge. Năng lượng khởi tạo DC, driver input/weight, switching nội bộ RTL và CPU softmax không cộng vào số analog này. PWM50 so PWM100 tăng {delta:.3f}% trên workload này, cùng diện tích và cùng 0 lỗi. Không suy ra tiết kiệm so với digital MAC.

Calibration đo riêng ba payload/mode: {cal[0][1]:.5f} pJ (PWM50), {cal[1][1]:.5f} pJ (PWM100); chưa cộng vào 32 projection và có thể amortize khi dùng lại fit.

Bảng PEX đầu flow dùng cửa sổ 0–3 ns và tải quét trên core PEX; bảng conversion dùng cùng physical MIM/core/conditioner/ADC và policy 0→EOC+hold ở TT/1.8 V/25 C. Mỗi bảng so sánh trong điều kiện của chính nó.

## Diện tích

| Block | Area / µm² | Phạm vi |
|---|---|---|
{rows}

SAR tổng hợp độc lập là breakdown tham khảo; footprint ADC đã gồm digital gốc nên không cộng hai lần. Hai mode PWM dùng cùng hardware. Controller top chứa 32 bit mask weight, 304×12 bit thresholds và 304 bit valid; leaf 8T nhận weight từ controller. Chứng minh MHA dùng một cột với fit affine ba điểm, còn top sequencer dùng hai phase 2+2 và LUT; notebook phân biệt hai đường.

## Render và khả năng chạy lại

KLayout dùng palette/lớp cố định, tắt grid/text chồng nhau; overview met3–met5, detail met1–met5. Cách hiển thị giữ nguyên geometry GDS. Script viết đầy đủ trong notebook; macro views có lớp thiết bị. Bản chính nhận toàn bộ output mới và giữ 260 source cell IDs. Chỉ chỉnh Markdown sau chạy để làm rõ phạm vi và giữ guide sát cell; cả 129 code-cell objects/source/output/execution_count/execution metadata không đổi so với bản vừa chạy.

Tái kiểm: `python scripts/verify_standalone_run.py` và `python scripts/verify_measured_costs.py` trong env_mamba. Run mới: `./run_all.sh` hoặc Restart Kernel & Run All. Yêu cầu hiện tại đã hoàn tất.
''')
r=Path('/home/nam/Vihn/interface_verify/fpga_export_18x18_mnist_softreset/test_folder/AutoMX-CIM')
for name in ['scripts/cim_measurement_extension.py','scripts/enrich_cim_notebook.py','scripts/render_flow2_wrapper_gds.py',
             'scripts/adapt_flow2_standalone_notebook.py','scripts/verify_measured_costs.py','scripts/standalone_readme.md',
             'docs/measured_costs_validation_20261026.json','docs/MEASURED_COSTS_PROGRESS_20261026.md']:
    shutil.copy2(b/name,r/name)
print('FINAL_NOTEBOOK',len(u.cells),'cells; all 129 executable cell objects unchanged from full execution.')
print('Energy delta %',delta,'calibration pJ',cal)
print('Reports and authoring scripts synchronized.')
