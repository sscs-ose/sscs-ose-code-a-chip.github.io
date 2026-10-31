"""Add the actual MHA IP sources, native verification and measurement bridge."""
from pathlib import Path
import json,shutil
import nbformat as nbf

B=Path(__file__).resolve().parents[1]

def extend(root=None):
    B=Path(root).resolve() if root is not None else Path(__file__).resolve().parents[1]
    (B/'diagnostics/mha_ip_20261027').mkdir(parents=True,exist_ok=True)
    path=B/'AutoMX_CIM_Code_a_Chip.ipynb'
    backup=B/'diagnostics/mha_ip_20261027/pre_mha_notebook.ipynb'
    if not backup.exists():shutil.copy2(path,backup)
    book=nbf.read(path,4);original_ids=[c.id for c in book.cells if not c.id.startswith('mha-ip-')]
    book.cells=[c for c in book.cells if not c.id.startswith('mha-ip-')]
    def md(name,text):return nbf.v4.new_markdown_cell(text,id='mha-ip-'+name)
    def code(name,text):return nbf.v4.new_code_cell(text,id='mha-ip-'+name)
    def source(variable,relative):
        text=(B/relative).read_text();assert "'''" not in text
        return variable+" = r'''"+text+"'''\n"+f"(MHA_ROOT / {str(relative)!r}).parent.mkdir(parents=True,exist_ok=True)\n(MHA_ROOT / {str(relative)!r}).write_text({variable})\n"
    setup="from pathlib import Path\nimport os\nMHA_ROOT=Path(os.environ.get('AUTOMX_BUNDLE_DIR',Path.cwd())).resolve()\n"
    cells=[md('architecture',r'''<a id="results-mha-rtl"></a>

## IP MHA RTL và ghép macro CIM–SAR

**Thực hiện:** Chuyển phần attention của testcase **2 token × 4 kênh, 2 head** thành IP (Intellectual Property, khối RTL có giao diện tái sử dụng) tổng hợp được. Q/K/V/O là bốn phép chiếu query/key/value/output; mỗi ma trận ternary 4×4 được lập trình bằng mask `WPOS/WNEG`. IP giữ Q/K/V trong thanh ghi, dùng một bộ nhân signed 18×18 cho $QK^T$, nội suy softmax và $A V$, rồi lượng tử context theo MXFP4 trước khi yêu cầu phép chiếu O.

Với hai token, softmax của một hàng bằng $[\sigma(s_0-s_1),1-\sigma(s_0-s_1)]$. LUT (Look-Up Table, bảng tra) gồm 65 điểm sigmoid, nội suy tuyến tính và bão hòa ngoài $[-8,8]$. Hai xác suất Q0.15 cộng đúng 32768. Các tổng Q/K/V có đơn vị X2, nên hệ số `181/1024` trong RTL đã gồm $1/(4\sqrt{2})$. Mã activation có dấu 5 bit, magnitude thuộc `{0,1,2,3,4,6,8,12}`; đầu ra có bốn lane signed 12 bit X2.

**Đầu vào → đầu ra:** 16 lần ghi hàng weight (stage Q/K/V/O × 4 hàng), frame gồm 8 activation → 8 yêu cầu vector qua controller CIM–SAR (4 stage × 2 token) → 64 conversion trong sequencer 2+2 hàng → hai hàng kết quả MHA. Đây là lịch của top RTL; phép đo transistor ở phần sau vẫn giữ 32 dot product một cột làm đối chứng độc lập.

| Bước trong IP | Nơi thực hiện | Kết quả truyền tiếp |
|---|---|---|
| Q, K, V | `seq_i` điều khiển `core_i → condition_i → adc_i` | Ba tensor 2×4 từ mã ADC đã giải mã |
| Score / softmax / context | `mha_i`, logic RTL tổng hợp được | Xác suất theo head và context lượng tử |
| O | Cùng đường CIM–SAR, nạp weight O | Hai hàng kết quả, ready/valid và token index |

Các phép đo Python ở những cell ứng dụng giữ vai trò reference độc lập; kết quả RTL có testbench và log Icarus riêng. Testbench tích hợp dùng đáp ứng ADC dạng giao thức để kiểm controller/decoder. Waveform transistor được kiểm trong phép đo native CIM–SAR bên dưới.'''),
    md('rtl-guide',r'''**Thực hiện:** Khai báo đầy đủ module `automx_mha_ip` trong cell. `valid_activation` kiểm tra alphabet MXFP4; `quantize_context` chọn mã gần nhất và chọn magnitude nhỏ hơn khi hòa; `sigmoid_lut` cung cấp điểm nội suy softmax. FSM (Finite-State Machine, máy trạng thái hữu hạn) giữ từng yêu cầu đến khi backend chấp nhận, đợi kết quả calibrated, tính attention và giữ hai hàng output ổn định khi host chưa nhận. Watchdog chuyển sang fault nếu backend không hoàn tất; reset hủy frame và yêu cầu nạp lại cấu hình. Reset tác động lên trạng thái/valid; buffer được ghi đủ trước khi đọc để giảm tải reset trên SKY130.

**Đầu vào → đầu ra:** hợp đồng số và ready/valid → RTL IP trong `ip/automx_mha/rtl` → module được mô phỏng và tổng hợp ở các cell kế tiếp.'''),
    code('rtl-source',setup+source('MHA_IP_RTL','ip/automx_mha/rtl/automx_mha_ip.sv')+"print('RTL IP: automx_mha_ip | 2 token × 4 channel × 2 head | shared multiplier + softmax LUT',flush=True)\n"),
    md('binding-guide',r'''**Thực hiện:** Ghép `mha_i` vào top hiện có. `mha_reserve` phân quyền bus cấu hình/evaluation cho IP; ownership giữ đến khi host nhận đủ hai hàng output, kể cả khi đổi mode giữa frame. Calibration của sequencer giữ nguyên và chỉ được ghi khi IP idle. Ba hard macro vẫn dùng instance `core_i`, `condition_i`, `adc_i`; `seq_i` phát PWM (Pulse-Width Modulation), chọn cột và đợi EOC (End Of Conversion).

**Đầu vào → đầu ra:** port frame/weight của MHA và 304 ngưỡng calibration → giao diện thật của `automx_cim_readout_seq` → chân điều khiển CIM/conditioner/SAR → tensor output. Khi `mha_mode_i=0` và IP idle, giao diện đọc CIM trực tiếp vẫn hoạt động.'''),
    code('binding-source',source('MHA_MIXED_TOP_RTL','inputs/automx_cim_mixed_signal_proto.sv')+"(MHA_ROOT/'ip/automx_mha/rtl/automx_cim_mixed_signal_proto.sv').write_text(MHA_MIXED_TOP_RTL)\n"+"print('TOP RTL: mha_i → seq_i → core_i / condition_i / adc_i; direct readout mode retained',flush=True)\n"),
    md('fixtures-guide',r'''**Thực hiện:** Tạo hai testbench từ code trong cell. `tb_mha_ip` dùng backend dot-product có stall ngẫu nhiên để kiểm thứ tự cấu hình, phép tính attention, hai output có backpressure và các ca lỗi. `tb_mha_mixed_top` chạy đúng hierarchy top/`seq_i`, nạp đủ 304 ngưỡng, tạo đáp ứng ADC theo alphabet hai hàng và kiểm 64 conversion. Fixture delay buffer chỉ phục vụ mô phỏng logic; nó không phải phép đo độ rộng PWM vật lý.

**Đầu vào → đầu ra:** RTL IP/top và vector chuẩn → testbench Icarus (trình mô phỏng Verilog) → trace Q/K/V/context/output và marker PASS; các log được ghi tại lượt chạy mới.'''),
    code('fixtures',source('MHA_UNIT_TB','ip/automx_mha/sim/tb_mha_ip.sv')+source('MHA_TOP_TB','ip/automx_mha/sim/tb_mha_mixed_top.sv')+"print('Testbench: random stalls, output backpressure, reset, timeout, calibration, full readout and direct mode',flush=True)\n")]
    index=next(i for i,c in enumerate(book.cells) if c.id=='native-runall-environment')
    book.cells[index:index]=cells
    verify_source=(B/'ip/automx_mha/verify.py').read_text().split("if __name__=='__main__':",1)[0]
    verify_cell=verify_source+'''
MHA_NATIVE_WORK=portable.WORK/'mha_ip'
MHA_IP_REPORT=verify(MHA_ROOT,MHA_NATIVE_WORK)
MHA_IP_SYNTH=synthesize(MHA_ROOT,MHA_NATIVE_WORK/'synthesis')
from IPython.display import display,Markdown
import matplotlib.pyplot as plt
_mha_delta=np.arange(-46,47)
_mha_reference=1/(1+np.exp(-_mha_delta/(4*np.sqrt(2))))
_mha_fixed=np.array([probability_fixed(int(d))/32768 for d in _mha_delta])
fig,axes=plt.subplots(1,2,figsize=(10,3))
axes[0].plot(_mha_delta/(4*np.sqrt(2)),_mha_reference,label='Floating reference')
axes[0].plot(_mha_delta/(4*np.sqrt(2)),_mha_fixed,'.',label='RTL Q0.15');axes[0].set(xlabel='Score difference',ylabel='Probability');axes[0].legend()
axes[1].plot(_mha_delta/(4*np.sqrt(2)),(_mha_fixed-_mha_reference)*100)
axes[1].set(xlabel='Score difference',ylabel='Probability error / percentage points');plt.tight_layout();plt.show()
display(Markdown('| Kiểm tra | Kết quả |\\n|---|---|\\n'+
 f"| Frame / output values | {MHA_IP_REPORT['test_cases']} / {MHA_IP_REPORT['checked_output_values']} |\\n"+
 f"| Sai khác với mô hình integer | {MHA_IP_REPORT['bit_exact_errors']} |\\n"+
 f"| Sai số xác suất lớn nhất | {MHA_IP_REPORT['softmax_absolute_probability_error_max']*100:.5f} điểm % |\\n"+
 f"| Cùng output với softmax float | {MHA_IP_REPORT['test_cases']-MHA_IP_REPORT['output_cases_different_from_float_softmax']} / {MHA_IP_REPORT['test_cases']} frame |\\n"+
 f"| Diện tích IP, SKY130 TT mapping | {MHA_IP_SYNTH[0]['mapped_area_um2']:.3f} µm² |"))
'''
    v=[md('verify-guide',r'''**Thực hiện:** `pack` mã hóa lane; `probability_fixed` là reference số nguyên độc lập cho softmax RTL; `quantize_x2` áp alphabet MXFP4; `reference` tính Q/K/V, xác suất, context và O bằng cả integer và floating. `vectors` tạo testcase mẫu, ca toàn zero và vector ngẫu nhiên với seed cố định. `run_command` lưu transcript tool và truyền lỗi; `verify` chạy hai testbench, kiểm output/trace và quét toàn bộ 18.433 hiệu số score có thể đạt. `synthesize` gọi Yosys cùng Liberty SKY130 TT (Typical–Typical, corner transistor danh định), kiểm netlist và đo diện tích mapped.

**Đầu vào → đầu ra:** source vừa khai báo + cấu hình testcase → Icarus/vvp, Yosys/ABC → `verification.json`, `canonical_rtl.json`, netlist mapped, report area và đồ thị sai số. Kết quả bit-exact so với contract integer; bảng cũng ghi số frame đổi mã lượng tử so với softmax floating, tránh gộp hai phép so sánh.'''),code('verify',verify_cell)]
    index=next(i for i,c in enumerate(book.cells) if c.id=='native-runall-environment')+1
    book.cells[index:index]=v
    compare='''from pathlib import Path
import json,numpy as np
from IPython.display import display,Markdown
_mha_work=portable.WORK
_mha_analog=json.loads((_mha_work/'mha_end_to_end.json').read_text())
_mha_rtl=json.loads((_mha_work/'mha_ip/canonical_rtl.json').read_text())
_mha_projection_errors={name:int(np.count_nonzero(np.array(_mha_rtl[name.lower()])!=np.array(_mha_analog['measured_projections'][name])*2)) for name in ['Q','K','V']}
assert sum(_mha_projection_errors.values())==0,_mha_projection_errors
_mha_rtl_output=np.array(_mha_rtl['output_x2'])/2
assert np.array_equal(_mha_rtl_output,_mha_analog['output'])
assert np.array_equal(_mha_rtl['context_x2'],_mha_analog['context_activation_x2'])
_mha_reference=np.array(_mha_analog['reference_quantized_output'])
_mha_float=np.array(_mha_analog['floating_reference_output'])
_mha_bridge={'status':'PASS','rtl_matches_measured_qkv':True,'rtl_matches_measured_context':True,
 'rtl_matches_measured_output':True,'output_integer_mismatches':0,
 'relative_l2_quantized':float(np.linalg.norm(_mha_rtl_output-_mha_reference)/max(np.linalg.norm(_mha_reference),1e-12)),
 'relative_l2_float':float(np.linalg.norm(_mha_rtl_output-_mha_float)/max(np.linalg.norm(_mha_float),1e-12)),
 'evidence':'Actual Icarus IP trace compared with fresh native CIM/SAR measurements; top RTL separately checks full sequencer with functional ADC responses.'}
(_mha_work/'mha_ip_measured_comparison.json').write_text(json.dumps(_mha_bridge,indent=2)+'\\n')
display(Markdown('| Kết quả | RTL MHA | CIM–SAR đo native |\\n|---|---|---|\\n'+
 '| Q/K/V: số giá trị khác | 0 / 24 | 0 / 24 |\\n'+
 '| Context MXFP4: số giá trị khác | 0 / 8 | 0 / 8 |\\n'+
 '| Output: số giá trị khác | 0 / 8 | 0 / 8 |\\n'+
 f"| L2 so với reference cùng lượng tử | {_mha_bridge['relative_l2_quantized']*100:.3f}% | {_mha_analog['relative_l2']*100:.3f}% |\\n"+
 f"| L2 so với reference floating | {_mha_bridge['relative_l2_float']*100:.3f}% | {_mha_analog['floating_reference_relative_l2']*100:.3f}% |"))
print('MHA_RTL_VS_NATIVE_CIM_SAR_PASS Q/K/V=24 context=8 output=8',flush=True)
'''
    index=next(i for i,c in enumerate(book.cells) if c.id=='standalone-sync-conversions')+1
    book.cells[index:index]=[md('comparison-guide',r'''**Thực hiện:** Đối chiếu trace thật từ mô phỏng IP với các conversion CIM–SAR vừa đo. Q/K/V dùng đơn vị X2 ở RTL và đơn vị thực ở report analog nên đổi scale trước khi kiểm. Context lượng tử và O output được so từng phần tử. Hai sai số L2 (chuẩn Euclid tương đối) giữ riêng: cùng contract lượng tử và floating context.

**Đầu vào → đầu ra:** `canonical_rtl.json` do trace Icarus tạo + `mha_end_to_end.json` từ waveform native của lượt hiện tại → bảng đối chiếu Q/K/V/context/output và `mha_ip_measured_comparison.json`. Kết quả không thay thế phép kiểm transistor bằng model giao thức; hai đường chứng cứ được nối ở các tensor quan sát được.'''),code('comparison',compare)]
    # Refresh only the modified implementation source; retain its result presenter.
    runtime=next(c for c in book.cells if c.id=='standalone-runtime')
    runtime.source='%%standalone_runtime\n'+(B/'scripts/standalone_runtime.py').read_text()+"\n# CELL_RESULT standalone-runtime\nprint('Runtime: MHA RTL, synthesis, routing, streamout, LVS, power, timing',flush=True)\n"
    area=next(c for c in book.cells if c.id=='meter-area')
    anchor="display(Markdown('| Block | Area / µm² | Meaning | Source |"
    if 'MHA RTL IP (standalone mapped)' not in area.source:
        i=area.source.index(anchor)
        extra="""mha_area_record=json.loads((portable.WORK/'mha_ip/synthesis/synthesis.json').read_text())['targets'][0]
meter_areas.append({'block':'MHA RTL IP (standalone mapped)','area_um2':mha_area_record['mapped_area_um2'],
 'cells':mha_area_record['mapped_cells'],'source':mha_area_record['log'],'kind':'TT mapped cell area; included within placed top, do not add twice'})
"""
        area.source=area.source[:i]+extra+area.source[i:]
    # Preserve the Python reference, and explicitly identify the new hardware path.
    architecture=next(c for c in book.cells if c.id=='meter-architecture-theory')
    old='| MHA trên CPU | Q/K/V đo được, hai attention head | Tính score, softmax và context; lượng tử context trước phép chiếu O | Đầu ra tiny-MHA và sai số với reference cùng lượng tử |'
    new='| Reference MHA Python | Q/K/V đo được, hai attention head | Tính score, softmax và context làm đối chứng độc lập | Tensor reference để so RTL |\n| IP MHA RTL `mha_i` | Frame, weight Q/K/V/O, kết quả từ `seq_i` | Điều phối projection; tính QKᵀ, softmax Q0.15, A×V, lượng tử context và O | Hai hàng output ready/valid; có trong top tổng hợp/place-and-route |'
    architecture.source=architecture.source.replace(old,new)
    theory=next(c for c in book.cells if c.id=='theory')
    theory.source=theory.source.replace('compute attention/softmax on the CPU.','use CPU attention/softmax as an independent numerical reference. The MHA RTL IP below implements score, softmax, context and projection scheduling in the mixed-signal top.')
    # Add one navigation entry without replacing the original result links.
    for c in book.cells:
        if c.cell_type=='markdown' and 'Kết quả chính' in c.source and 'results-checkpoint' in c.source:
            if 'results-mha-rtl' not in c.source:c.source+='\n\n[IP MHA RTL và liên kết CIM–SAR](#results-mha-rtl)\n'
            break
    assert set(original_ids).issubset({c.id for c in book.cells})
    book.metadata['mha_rtl_ip']={'configuration':'2 tokens, 4 channels, 2 heads','status':'SOURCE_READY_FOR_FULL_EXECUTION'}
    if book.metadata.get('presentation_language')=='en':
        from scripts.notebook_english import translate_book
        translate_book(book,B)
    nbf.write(book,path)
    report={'cells':len(book.cells),'code_cells':sum(c.cell_type=='code' for c in book.cells),'preserved_cells':len(original_ids),'added_ids':[c.id for c in book.cells if c.id.startswith('mha-ip-')]}
    (B/'diagnostics/mha_ip_20261027/notebook_extension.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':extend()
