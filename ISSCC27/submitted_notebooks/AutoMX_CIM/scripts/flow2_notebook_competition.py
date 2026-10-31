"""Competition reading route, applied without changing native code or outputs."""
from pathlib import Path
import json
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
PREFIX='competition-'

def apply_competition_front_matter(book):
    evidence=ROOT/'submission/ISSCC27/submitted_notebooks/automx_cim/data/evidence.json'
    if not evidence.is_file():return book
    data=json.loads(evidence.read_text())
    gaps={}
    for row in data['factorial']:
        jobs=row['jobs'];gaps[row['load_ff'],row['pwm_unit_ps']]=(
            jobs[1]['measurements_v']['diff_c0_t19']-jobs[0]['measurements_v']['diff_c0_t19'])*1000
    route='submission/ISSCC27/submitted_notebooks/automx_cim'
    abstract=f'''## Đóng góp và kết quả chính — Code-a-Chip

**Câu hỏi thiết kế:** Một core CIM ternary có thể đi qua đường đọc analog, SAR RTL thực và tạo đúng các projection attention hay không? Flow điều tra lỗi transfer vật lý, xác định tác động tải/PWM, rồi kiểm mã conversion và đầu ra MHA. Đóng góp tập trung vào tích hợp và kiểm chứng; SAR/decoder/OSR được kế thừa từ [SKY130_SAR-ADC1](https://github.com/efabless/SKY130_SAR-ADC1).

**Kết quả của các phép đo đã hoàn tất:** 3 pattern calibration độc lập; 30 pattern projection và 8 pattern challenge mới không trùng, **0/38 mismatch giải mã sum nguyên**. Tiny-MHA có 32 transaction Q/K/V/O, relative L2 = 0 với reference cùng lượng tử context và 0.114477 với context floating. Attention/softmax chạy CPU, một cột vật lý được dùng lại.

**Bản đọc ngắn và chạy độc lập:** [AutoMX_CIM_Code_a_Chip.ipynb]({route}/AutoMX_CIM_Code_a_Chip.ipynb). Bản này tính lại số đo từ log/record cung cấp, thêm lỗi dữ liệu có chủ đích để kiểm checker, thực thi SAR RTL và KLayout mới khi tool có sẵn. Toàn bộ implementation phân tích nằm trong cell. [README]({route}/README.md) ghi dependency, cách Run All, provenance và attribution. Các phép analog trong gói review được ghi rõ là dữ liệu đo đã có.

**Notebook native hiện tại** giữ toàn bộ cell thiết kế/đo kiểm trước đây và đường chạy tạo output mới. Các số ở đoạn mở đầu này là kết quả đã ghi nhận; bảng/log phía sau thuộc phiên native tương ứng. Thông tin tác giả/đơn vị/email được điền tại [TEAM.json]({route}/TEAM.json).'''
    results='''## Quyết định thiết kế rút ra từ đối chứng mới

Cùng cặp stimulus sum 11/sum 12, netlist PEX, TT/1.8 V/25 °C và thời điểm lấy mẫu 1.9 ns:

| Tải bitline | PWM unit | Gap s12 − s11 / mV |
|---|---|---|
'''+ '\n'.join(f'| {c} fF | {p} ps | {gaps[c,p]:+.4f} |' for c in (200,800) for p in (50,100))+'''

Chỉ rút PWM ở 200 fF đã khôi phục thứ tự (+29.2472 mV); chỉ tăng tải ở 100 ps cũng khôi phục thứ tự (+30.7722 mV). Thay đổi cả hai cho +19.5577 mV, nên hai tác động không cộng tuyến tính. Đối chứng mới cho cơ sở xem xét PWM ngắn trước khi tăng tải bốn lần; cặp stimulus này chưa đủ để kết luận cấu hình tối ưu cho toàn miền.

Tám challenge ADC mới giữ nguyên hệ số calibration đã khóa. Các cặp cùng sum ±3 nhưng activity 3 → 13 có mã ADC lệch 2 code, trong khi sum sau giải mã vẫn đúng. Phần review giữ sai số chưa làm tròn để thấy biến thiên này. Thí nghiệm PEX và thí nghiệm conversion partition được phân biệt, không suy mã ADC từ bảng PEX hai stimulus.'''
    reading='''## Tuyến đọc nhanh

1. Cơ sở lý thuyết và flow mixed-signal ngay dưới đây.
2. Các cell PEX trước/sau: xem lỗi thật và phép thay đổi có số đo.
3. Calibration → trace analog/SAR → projection Q/K/V/O → sai số MHA.
4. Synthesis, top GDS/render, signal connectivity, nguồn và RC/STA.
5. Mở bản Code-a-Chip để chạy đối chứng 2×2, 8 challenge và các checker từ gói dữ liệu độc lập.

Cell định nghĩa hàm không in banner; cell gọi tool hiển thị stdout/stderr thực tế. Các recipe kỹ thuật cũ vẫn được giữ làm cơ sở cho những phép kiểm phía sau.'''
    book.cells=[c for c in book.cells if not c.id.startswith(PREFIX)]
    index=next(i for i,c in enumerate(book.cells) if c.id=='combined-intro')+1
    book.cells[index:index]=[nbf.v4.new_markdown_cell(source,id=PREFIX+cid)
        for cid,source in [('abstract',abstract),('results',results),('route',reading)]]
    return book
