"""Create the ordered Run All notebook; preserve the complete previous edition."""
from pathlib import Path
import shutil
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'AutoMX_CIM_Sky130_MHA.ipynb'
ARCHIVE=ROOT/'docs/AutoMX_CIM_legacy_server_20261023.ipynb'


def build_compact():
    if not ARCHIVE.exists():shutil.copy2(BOOK,ARCHIVE)
    cells=[]
    def md(text):cells.append(nbf.v4.new_markdown_cell(text))
    def code(name,text):
        cell=nbf.v4.new_code_cell(text,id='runall-'+name);cells.append(cell)
    md('''# AutoMX-CIM — Run All: analog → SAR ADC → tiny-MHA → mixed-signal top core

Bản chạy prototype 23/10/2026. Chọn kernel **Python (env_mamba)** rồi **Restart Kernel and Run All**.
Các bước chức năng, tổng hợp và xuất view phải thành công; lỗi dừng cell và giữ log. Riêng DRC trong profile prototype có thể ghi timeout/violation thành waiver công khai để tiếp tục, tuyệt đối không tính là DRC-clean. Các bước đã chạy chỉ được tái dùng khi SHA-256 của input, output và log khớp; output cell ghi `REUSE (hash verified)` và hiện log native gốc.

**Kết quả đích:** waveform chuyển đổi transistor/RTL thật, tiny-MHA có projection đo riêng, mapped digital netlist, GDS/DEF/LEF top, SPEF, digital LIB, KLayout PNG và manifest kiểm hash.

**Chế độ nhanh trên máy EDA hiện tại:** synthesis chạy từ RTL; placement/routing dùng checkpoint đã route và kiểm hash. DEF/LEF/GDS được xuất lại từ checkpoint đó. Đây là Run All từ cell đầu trên workspace đã chuẩn bị, **không phải cold-start PnR từ PDK trống**. Đổi sequencer RTL cần route lại trước khi dùng checkpoint. Các receipt signoff lịch sử vẫn giữ nguyên.

Bản notebook cũ đủ 127 cell: [archive](docs/AutoMX_CIM_legacy_server_20261023.ipynb).''')
    md('''## 1. Cấu hình tập trung

Dùng trực tiếp Python trong `env_mamba`, tương đương `conda activate env_mamba`. PDK, OpenLane và Docker image được pin theo workspace hiện có. Work volume có dung lượng trống; không ghi hàng trăm MB intermediate vào phân vùng `/` đang gần đầy.

Giữ `reuse=True` cho Run All nhanh. Dùng **tag mới** để chạy lại toàn bộ phép đo chức năng mà vẫn giữ bằng chứng cũ; cần khoảng 33 conversion. Một conversion có timeout riêng; concurrency mặc định 3. Không chạy lại full-transistor ADC hàng giờ khi partition này đã đáp ứng mục tiêu prototype.''')
    code('config','''from pathlib import Path
import os, sys, json
ROOT = Path(os.environ.get("AUTOMX_CIM_ROOT", Path.cwd())).resolve()
if not (ROOT / "scripts/flow2_runall_support.py").is_file():
    raise FileNotFoundError("Open this notebook from the AutoMX-CIM project root")
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts.flow2_runall_support import Settings, Flow, item, verified, save
from scripts import flow2_runall_notebook as nb
from scripts import flow2_runall_physical as physical
settings = Settings(root=ROOT,
    cache=Path(os.environ.get("AUTOMX_RUNALL_CACHE", "/media/nam/EDABK/AutoMX_CIM_runall_20261023")),
    tag=os.environ.get("AUTOMX_RUNALL_TAG", "runall_srv_20261023_01"),
    reuse=True, timeout_s=180, jobs=3)
flow = Flow(settings)
print("Route mode: verified existing checkpoint; fresh synthesis and view export")''')
    code('environment','nb.environment(flow)')
    md('''## 2. Runtime ngspice shared và nguồn ADC gốc

Shared ngspice 44.2 được build riêng, không thay thư viện của conda/system. Nếu thiếu, helper build từ tar nguồn đã pin SHA (configure/make/install có log và timeout). Không cần kết nối mạng khi các dependency của workspace còn nguyên.

Nguồn ADC: [efabless/SKY130_SAR-ADC1](https://github.com/efabless/SKY130_SAR-ADC1), commit `892272208df28b6c7620101e129a9d8dd95ebab7`, cùng revision của macro ADC tích hợp. Các file RTL/SPICE giữ nguyên byte, có Git blob SHA và SHA-256 trong provenance.''')
    code('ngspice','shared_library = nb.prepare_shared(flow)')
    code('partition-sources','''from scripts.flow2_partition_mha import Experiment
experiment = Experiment(flow)
provenance = json.loads((ROOT / "third_party/SKY130_SAR_ADC1/mixed_signal_partition/provenance.json").read_text())
print("Pinned ADC revision:", provenance["commit"])
print("Verified native dependencies:", len(experiment.sources))
source, source_views, design, routed_run, config, pdk = physical.inputs(flow)
print("Source ODB:", item(source_views["odb"]))
print("Source GDS:", item(source_views["gds"]))''')
    md('''## 3. KLayout: xem macro analog và ADC thực

Các hình dưới đọc GDS macro thực từ cấu hình wrapper, không phải sơ đồ minh họa. Hàm `flow.render(gds, top, name)` gọi KLayout native, ghi log và nhúng PNG vào output. Hình layout không tự chứng minh chức năng analog.''')
    code('render-macros','''from scripts.render_flow2_components import catalog
macro_views = catalog(ROOT, design / "config.json")[:3]
for macro in macro_views:
    print(macro["title"], "—", macro["source"])
    flow.render(macro["source"], macro["cell"], macro["name"])''')
    md('''## 4. Partition đã chọn: SAR RTL thật + analog transistor

Đường tín hiệu: pulse E2M1 → CIM + acquisition schematic → conditioner schematic → input sampling transistor → CDAC/comparator transistor → quyết định comparator → **RTL SAR gốc chạy Icarus** → decoder/CDAC feedback → EOC và word.

Python nối hai simulator qua shared-ngspice API, clock từng phase và cung cấp stimulus PWM/PWL. Chưa đồng mô phỏng sequencer top với routing extracted. Không tính word bằng công thức quantizer lý tưởng, không ép EOC. Comparator phải resolve mức logic; word trên electrical bridge phải trùng RTL và giữ ổn định 40 ns sau EOC.

**Các xấp xỉ công khai:** CDAC gộp đúng 515 tụ signal tuyến tính mỗi phía (1.4848 pF) theo bảo toàn điện tích; bottom driver lý tưởng nhận decoder RTL thật. Nguồn VCM và clock phase bên ngoài lý tưởng. Giữ MOS/MIM comparator và input switch; bỏ các card varactor decoupling noise do mô hình charge mất hội tụ trong partition. Schematic core/conditioner, chưa phải full-chip RC/PEX. Không chứng minh asynchronous clock generator, reference startup, noise/mismatch/PVT hoặc độ tuyến tính 12-bit.''')
    md('''## 5. Hiệu chuẩn riêng trước holdout

Ba conversion native ở tổng integer `[0, -8, +8]`; khóa slope/offset trước Q/K/V/O. Mẫu calibration không được trùng mẫu holdout. Đây là hiệu chuẩn digital tuyến tính đơn giản, chưa phải characterization ADC toàn dải.''')
    code('calibration','calibration = experiment.calibrate()')
    md('''## 6. Tiny-MHA đầu cuối bằng projection đo riêng

Testcase **2 token × 4 chiều, 2 head**; Q/K/V/O ternary. Một cột vật lý 4 hàng được time-multiplex; attention/softmax chạy CPU. Context lượng tử E2M1 scale cố định 1 trước projection O. Mỗi pattern phải có raw ngspice, trace RTL, EOC và receipt; không dùng LUT ước lượng analog chưa đo.

Reference chính có cùng lượng tử context. Đồng thời báo sai số so với reference floating trước lượng tử context để tránh hiểu sai kết quả zero error. Không suy rộng sang trained MNIST/full-size 32×8 hoặc pipeline MHA hoàn toàn trên chip.''')
    code('measured-mha','mha = experiment.mha()')
    code('adc-waveform','''holdout_case = mha["jobs"][0]["case"]
conversion = nb.plot_conversion(flow, holdout_case)
print("Conversion summary:", {k: conversion[k] for k in (
    "expected_integer_sum", "measured_input_diff_v", "result_code_12bit", "cycles", "start_to_eoc_s")})''')
    code('mha-plots','''nb.plot_mha(flow, mha)
print("Quantized reference relative L2:", mha["relative_l2"])
print("Floating reference relative L2:", mha["floating_reference_relative_l2"])
print("Independent holdout patterns:", mha["unique_holdout_patterns"])
print("Unmeasured analog lookup estimates:", mha["unmeasured_analog_lookup_estimates"])''')
    md('''## 7. Yosys: tổng hợp lại full digital wrapper

Đọc RTL wrapper + sequencer thật; ba macro analog là blackbox vật lý. `hierarchy -check`, map flop/ABC theo Liberty SKY130, `check -assert` và kiểm không còn internal `$` cell. Mapped netlist là output synthesis mới; không tuyên bố netlist này vừa được PnR. Diện tích logic trong log không bao gồm area macro analog.''')
    code('synthesis','physical.synthesize_sar(flow)\nphysical.synthesize(flow)')
    md('''## 8. OpenROAD + KLayout: dựng lại top core mixed-signal

Đọc checkpoint ODB hậu ECO, xuất DEF/abstract LEF; merge đủ cell/macro GDS bằng KLayout trong image OpenLane pin. Native streamout phải xác nhận mọi LEF cell có GDS. Kiểm geometry/transform/hierarchy toàn bộ để ràng buộc GDS xuất lại với bằng chứng LVS từ GDS nguồn. KLayout bật rõ `beol=true`, `offgrid=true`; FEOL/seal/floating-metal chưa chạy. Report có violation hoặc timeout được công khai như waiver của prototype, không gọi là DRC-clean. Các report cũ không bật nhóm rule không được coi là bằng chứng DRC 0.''')
    code('streamout','top_gds = physical.streamout(flow)')
    code('gds-audit','gds_audit = physical.audit_gds(flow)\nprint(json.dumps(gds_audit, indent=2))')
    code('render-top','flow.render(top_gds, physical.TOP, "top")')
    md('''## 9. Netgen: LVS tín hiệu trên hình học top đã đối chiếu

Chạy lại Netgen trên SPICE **đã extract từ GDS nguồn thực**, reuse extraction chỉ sau phép đối chiếu toàn bộ geometry/instance của GDS mới. Boundary ba analog macro và chuẩn hóa formal PG/body của standard cell được công khai. Đây là signal/macro LVS; chưa phải full powered/body transistor LVS.''')
    code('signal-lvs','physical.lvs(flow)')
    md('''## 10. Liên thông nguồn và RC/STA/LIB digital nominal

PG checker dùng bản ODB trong bộ nhớ và chỉ sửa metadata direction của hai rectangle bridge VGND; bounds/net/kim loại published không đổi. Kiểm VPWR/VGND độc lập, chưa có padframe/IR/EM.

OpenRCX extract RC mới; STA TT 1.8 V, 25°C, clock 40 ns / 25 MHz. Chỉ các path digital được ràng buộc. Log giữ nguyên cảnh báo coverage, slew và fanout; setup/hold PASS không đóng các cảnh báo đó. ETM LIB là **digital**, đọc lại bằng OpenSTA, không có characterization analog ADC.''')
    code('power','power = physical.power(flow)')
    code('timing','timing = physical.timing(flow)\nphysical.parse_library(flow)')
    md('''## 11. Kết quả cuối và giới hạn còn mở

Manifest kiểm hash các output bắt buộc cùng log native. Các view lớn nằm trên work volume persistent. Receipt nhỏ trong `results/receipts/` trỏ tới manifest để tiếp tục phiên sau.

Profile này là **prototype partition + physical/digital integration**, `fabrication_ready=false`. Còn mở: ADC full transistor/PEX/noise/PVT, analog capture spec gốc, full powered LVS, full Magic DRC, antenna, coverage/slew/fanout, padframe/ESD/IR/EM và trained-model accuracy. Receipt strict `wrapper_signoff.json` không được đổi thành PASS bởi notebook này.''')
    code('manifest','manifest = nb.publish(flow)')
    book=nbf.v4.new_notebook(cells=cells)
    book.metadata={'kernelspec':{'display_name':'Python (env_mamba)','language':'python','name':'python3'},
        'language_info':{'name':'python','version':'3.11'},'automx':{'flow':'flow2_measured_partition_runall_v1','legacy_archive':str(ARCHIVE.relative_to(ROOT))}}
    nbf.write(book,BOOK)
    print(BOOK,len(cells),'cells;',sum(c.cell_type=='code' for c in cells),'code cells')

def build():
    # The default must preserve the complete combined flow requested by the user.
    import sys
    if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
    from scripts.build_flow2_fresh_notebook import build as build_combined
    return build_combined()

if __name__=='__main__':build()
