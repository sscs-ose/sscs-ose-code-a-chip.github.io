"""Authoring-only front matter for the mixed-signal notebook."""
from base64 import b64encode
import nbformat as nbf

INTRO=r'''# AutoMX-CIM — thiết kế và kiểm chứng lõi mixed-signal

Notebook đi từ phép nhân ma trận trong MHA đến đường tín hiệu **digital → analog → digital** trên SKY130: activation được mã hóa thành PWM, core CIM tích lũy tín hiệu vi sai, mạch acquisition/conditioner đưa tín hiệu vào ADC, rồi mã ADC được dùng để tính các projection Q/K/V/O. Kết quả chức năng được đối chiếu với reference số và liên kết với netlist, layout, timing cùng log tool.

Đọc phần lý thuyết và flow dưới đây trước khi chạy. Chọn kernel **Python (env_mamba)** → **Restart Kernel & Run All**. Mỗi lượt mặc định tạo thư mục output mới; cell thực thi hiển thị command, stdout/stderr, return code và số đo. RTL, PDK, netlist PEX, thư viện GDS và checkpoint routing được khai báo tại các cell sử dụng chúng.'''


def diagram_svg():
    """Portable SVG, embedded in Markdown so another session needs no image path."""
    boxes=[(20,169,135,66,'Đặc tả hệ thống','Số học · timing · PVT','blue'),
           (185,169,150,66,'Phân hoạch kiến trúc','Giao diện analog/digital','blue'),
           (375,35,175,70,'Schematic analog','SPICE · transistor','analog'),
           (590,35,175,70,'Layout analog','DRC · LVS · PEX','analog'),
           (375,299,175,70,'RTL và kiểm chức năng','Synthesis · netlist','digital'),
           (590,299,175,70,'Triển khai digital','Floorplan · CTS · route','digital'),
           (810,169,160,66,'Tích hợp mixed-signal','RC · co-simulation','blue'),
           (1005,169,140,66,'Kiểm tra cuối','GDS · timing · log','blue')]
    colors={'blue':('#e9f0fc','#2c5282'),'analog':('#fff0de','#95531b'),'digital':('#e5f3e9','#21633c')}
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1165" height="430" viewBox="0 0 1165 430" role="img" aria-label="Flow thiết kế mixed-signal, hai nhánh analog và digital tích hợp rồi kiểm tra sau layout">',
           '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#526170"/></marker></defs>',
           '<rect width="1165" height="430" fill="white"/>',
           '<g fill="none" stroke="#526170" stroke-width="2" marker-end="url(#arrow)">',
           '<path d="M155 202 H185"/><path d="M335 202 H350 V70 H375"/><path d="M350 202 V334 H375"/>',
           '<path d="M550 70 H590"/><path d="M550 334 H590"/>',
           '<path d="M765 70 H785 V202 H810"/><path d="M765 334 H785 V202"/>',
           '<path d="M970 202 H1005"/><path d="M1075 235 V400 H260 V235" stroke-dasharray="6 4"/>','</g>']
    for x,y,w,h,title,subtitle,kind in boxes:
        fill,stroke=colors[kind]
        parts.extend([f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>',
            f'<text x="{x+w/2}" y="{y+27}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="12" font-weight="bold" fill="{stroke}">{title}</text>',
            f'<text x="{x+w/2}" y="{y+48}" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="11" fill="#263445">{subtitle}</text>'])
    parts.extend(['<rect x="345" y="383" width="665" height="31" fill="white"/>',
        '<text x="675" y="404" text-anchor="middle" font-family="DejaVu Sans, sans-serif" font-size="13" fill="#35465a">Đo → chẩn đoán → sửa mạch/RTL/layout → trích xuất → kiểm lại</text>','</svg>'])
    return ''.join(parts)


def sections():
    diagram=b64encode(diagram_svg().encode()).decode()
    return [
('theory-mha-cim',r'''## Cơ sở lý thuyết 1 — từ MHA đến phép tích lũy CIM

Với đầu vào token $X$, mỗi head của attention tính:

$$Q_h=XW_{Q,h},\qquad K_h=XW_{K,h},\qquad V_h=XW_{V,h},$$
$$A_h=\operatorname{softmax}\!\left(\frac{Q_hK_h^T}{\sqrt{d_h}}\right),\qquad H_h=A_hV_h,$$
$$Y=\operatorname{Concat}(H_1,\ldots,H_H)W_O.$$

Các phép projection Q/K/V/O chứa nhiều phép nhân–cộng nên là phần được ánh xạ xuống CIM. Trong phép đo tiny-MHA của notebook, attention/softmax được tính bằng CPU; projection lấy kết quả từ các conversion analog/ADC thực sự đã chạy. Testcase này có **2 token × 4 chiều, 2 head**.

Core vật lý có bốn hàng, trọng số ternary được biểu diễn bằng hai nhánh P/N:

$$t_{r,c}=W^+_{r,c}-W^-_{r,c}\in\{-1,0,+1\},\qquad s_c=\sum_{r=0}^{3}a_r t_{r,c}.$$

$a_r$ là activation nguyên `ACT_X2`. Với scale cố định trong testcase hiện tại, giá trị số tương ứng là $x_r=a_r/2$, nên projection reference là $\sum_r x_rt_{r,c}=s_c/2$. Dấu activation chọn phase PWM dương/âm; độ lớn activation quyết định độ rộng xung. Tách rõ **sum nguyên**, **điện áp analog** và **mã ADC** giúp đối chiếu từng chặng của đường tín hiệu.'''),
('theory-charge-sampling',r'''## Cơ sở lý thuyết 2 — điện tích, transfer vi sai và lấy mẫu

Trong khoảng tích lũy, dòng dẫn phụ thuộc activation, trọng số và trạng thái transistor. Gọi $I_P,I_N$ là dòng xả dương về VGND của hai nhánh P/N; với tải gần đối xứng, mô hình trực giác là:

$$Q_{\mathrm{diff}}=\int_{t_0}^{t_1}\!\bigl(I_P(t)-I_N(t)\bigr)\,dt,\qquad
\Delta V=V_{BLN}-V_{BLP}\approx\frac{Q_{\mathrm{diff}}}{C_{\mathrm{eff}}}.$$

Biểu thức này giải thích vì sao tải bitline và độ rộng PWM ảnh hưởng swing. Transistor, parasitic, activity của các hàng và thời điểm lấy mẫu cùng quyết định transfer thực; vì vậy notebook dùng ngspice/PEX để đo điện áp thay vì suy ra điện áp chỉ từ sum nguyên.

Để giải mã hai mức $s_i<s_j$ bằng ngưỡng điện áp, xét khoảng điện áp đo được $\mathcal V(s)$ và gap:

$$g_{i,j}=\min\mathcal V(s_j)-\max\mathcal V(s_i).$$

$g_{i,j}<0$ thể hiện hai khoảng bị chồng lấn hoặc đảo thứ tự; $g_{i,j}>0$ tạo khoảng đặt ngưỡng giữa hai mức. Với sai số điện áp có biên $\epsilon_V$ ở mỗi mức, điều kiện khoảng cách tương ứng là $g_{i,j}>2\epsilon_V$.

Sau tích lũy, acquisition/sample-and-hold giữ điện áp trong quá trình ADC so sánh. Với mô hình RC bậc nhất, phần sai số settling còn lại tỷ lệ $e^{-t_s/(R_{eq}C_{eq})}$, nên thời điểm lấy mẫu phải được xét cùng tải và hằng số thời gian. Các cell đầu flow đo **cùng hai stimulus** ở hai cấu hình tải/PWM, in native log và vẽ gap trước/sau thay đổi.'''),
('theory-sar-interface',r'''## Cơ sở lý thuyết 3 — SAR ADC và giao tiếp hai miền

SAR ADC hoạt động theo vòng **sample → đặt mã thử lên DAC → comparator quyết định → cập nhật thanh ghi → EOC**. DAC và comparator tạo phản hồi analog/digital để tìm mã biểu diễn điện áp đã lấy mẫu. Mô tả kiến trúc tham khảo từ [Analog Devices — SAR ADC](https://www.analog.com/en/resources/technical-articles/successive-approximation-registers-sar-and-flash-adcs.html).

Trong notebook, comparator/input switch được mô phỏng transistor bằng ngspice; SAR RTL gốc chạy bằng Icarus. Harness trao đổi quyết định comparator và vector điều khiển CDAC theo từng phase. **Trace RTL và điện áp**, cùng mã word/EOC, là dữ liệu dùng để kiểm việc hoàn thành conversion.

Với CDAC tuyến tính và nút top cô lập, bảo toàn điện tích cho một chuyển tiếp cho:

$$\sum_i C_i(\Delta V_{top}-\Delta V_{bottom,i})=0
\quad\Longrightarrow\quad
\Delta V_{top}=\frac{\sum_i C_i\Delta V_{bottom,i}}{\sum_i C_i}.$$

Công thức này là cơ sở quy đổi mạng tụ trong partition: inventory **515 tụ signal mỗi phía**, tổng **1.4848 pF/phía**, được lấy từ nguồn mạch. Vector điều khiển và chu kỳ quyết định vẫn lấy từ RTL. Với ADC lý tưởng $N$ bit, $LSB=V_{FS}/2^N$ là bước lượng tử tham chiếu; phép đo ở đây kiểm mã và diễn biến conversion trực tiếp.

Ở giao diện cần theo dõi reset/start, cửa sổ sample/hold, comparator decision, EOC và khoảng ổn định của word. Cell waveform đối chiếu các tín hiệu này trên cùng trục thời gian; log SAR cho thấy từng quyết định cho đến khi EOC lên 1.'''),
('theory-design-flow',f'''## Flow thiết kế mixed-signal từ đặc tả đến GDS

Quy trình chia thành hai nhánh analog và digital, thống nhất giao diện trước khi ghép top và kiểm lại sau layout. Nhánh triển khai số gồm synthesis, floorplan, placement, CTS, routing và finishing theo [OpenROAD Flow](https://openroad-flow-scripts.readthedocs.io/en/latest/mainREADME.html).

<img alt="Flow thiết kế mixed-signal: đặc tả, hai nhánh analog/digital, tích hợp và kiểm tra cuối" src="data:image/svg+xml;base64,{diagram}" width="1165" />

| Giai đoạn | Công việc và đầu ra dùng cho bước tiếp theo |
|---|---|
| 1. Đặc tả hệ thống | Chốt miền số, kích thước phép toán, điện áp, clock, latency và mục tiêu sai số. |
| 2. Phân hoạch kiến trúc | Chọn phần xử lý analog/digital; quy định pin, polarity, scale, reset và handshake. |
| 3. Thiết kế analog | Vẽ schematic, chọn transistor/tụ, mô phỏng transient và các điều kiện PVT; chọn điểm làm việc và thời điểm lấy mẫu. |
| 4. Thiết kế digital | Viết RTL điều khiển/SAR, xây reference và testbench; kiểm reset, trình tự transaction và kết quả. |
| 5. Kiểm ghép chức năng | Co-simulation hai miền; theo dõi đường stimulus → điện áp → mã → kết quả ứng dụng. |
| 6. Layout analog | Bố trí mạch, nguồn và đường tín hiệu; kiểm DRC/LVS, trích parasitic để có netlist sau layout. |
| 7. Triển khai digital | Tổng hợp netlist; floorplan và PDN, placement, CTS, route; xuất database và các view vật lý. |
| 8. Tích hợp top | Ghép view analog và digital theo pin/nguồn/clock; kiểm liên thông và hình học của top. |
| 9. Kiểm sau layout | Dùng RC để đánh giá timing/settling và kiểm lại chức năng; sửa ECO khi số đo yêu cầu. |
| 10. Tổng hợp kết quả | Đối chiếu các report DRC/LVS, timing, nguồn và chức năng; xuất GDS, netlist, timing view và log tương ứng. |

Các vòng sửa có thể quay về schematic, RTL hoặc layout tùy nguyên nhân của phép đo. Mỗi lần sửa cần cập nhật những phép kiểm phụ thuộc vào đầu ra vừa thay đổi.'''),
('theory-verification',r'''## Ý nghĩa các phép kiểm và cách đọc kết quả

Các kiểm tra trả lời những câu hỏi khác nhau. Quy tắc vật lý, kết nối schematic/layout và trích xuất parasitic được mô tả trong [SKY130 — Physical & Design Verification](https://skywater-pdk.readthedocs.io/en/main/verification.html).

| Phép kiểm | Câu hỏi cần trả lời | Kết quả cần đọc |
|---|---|---|
| Mô phỏng transistor / co-simulation | Điện áp, thời điểm và mã số có đáp ứng stimulus không? | Waveform, measure điện áp, quyết định comparator, word và EOC. |
| Regression RTL | Trình tự điều khiển và kết quả logic có đúng reference không? | Transaction, reset/handshake, expected/actual và số mismatch. |
| DRC | Geometry có thỏa các rule được bật không? | Rule, vị trí marker, số violation và trạng thái hoàn tất tool. |
| LVS | Kết nối và các phần tử extract có tương ứng schematic/reference không? | Match/mismatch, net hoặc device gây sai khác. |
| PEX / RCX | Điện trở và điện dung parasitic nào cần đưa vào kiểm sau layout? | Netlist RC hoặc SPEF, nguồn extraction và các nút/net được trích. |
| STA | Đường digital có thỏa clock và ràng buộc timing không? | Setup/hold slack, path report, slew/capacitance/fanout. |
| Kiểm nguồn | Các terminal nguồn có nối tới mạng nguồn tương ứng không? | Kết nối VPWR/VGND và kết quả checker. |

OpenRCX trích R/C của routing và có thể xuất SPEF để dùng trong phân tích timing, theo [OpenROAD — Parasitics Extraction](https://openroad.readthedocs.io/en/latest/main/src/rcx/README.html).

Hiệu chuẩn tuyến tính dùng quan hệ $d\approx\alpha s+\beta$ giữa mã ADC $d$ và sum nguyên $s$. Khóa $\alpha,\beta$ bằng tập calibration rồi mới tính $\widehat s=(d-\beta)/\alpha$ trên holdout. Reference cùng lượng tử context và reference floating được báo riêng khi đối chiếu MHA:

$$e_{rel}=\frac{\lVert Y_{measured}-Y_{reference}\rVert_2}{\max(\lVert Y_{reference}\rVert_2,\varepsilon)}.$$

Một dòng mismatch hoặc violation là dữ liệu chẩn đoán cho vòng sửa tiếp theo. Đọc kèm stimulus, điều kiện đo và log của bước đó để hiểu nguyên nhân.'''),
('theory-notebook-map',r'''## Ánh xạ flow vào các cell của notebook

| Nhóm cell | Vai trò trong flow | Dữ liệu đi tiếp |
|---|---|---|
| Cấu hình và định nghĩa hàm | Chọn env_mamba, thư mục chạy và chuẩn bị implementation trong cell. | Tham số phiên và hàm dùng cho các bước thực thi. |
| PEX trước/sau thay đổi | Chạy ngspice cho cùng cặp sum 11/sum 12 ở 200 fF / 100 ps và 800 fF / 50 ps. | Điện áp mới, gap/overlap và đồ thị so sánh. |
| Calibration và analog/SAR/MHA | Đo ba conversion hiệu chuẩn, khóa hệ số, đo projection Q/K/V/O và tính attention. | Mã ADC, trace RTL, waveform và sai số MHA. |
| Synthesis | Chạy Yosys trên SAR RTL và digital wrapper. | Mapped netlist và thống kê tổng hợp. |
| Top mixed-signal | Dùng ODB routing được khai báo làm đầu vào cho OpenROAD/KLayout export và ghép GDS. | DEF/LEF/GDS mới, kiểm geometry và hình render. |
| LVS, nguồn, RC/STA | Kiểm ghép tín hiệu, liên thông nguồn, extraction và timing digital. | Report Netgen/checker, SPEF, SDC, LIB và slack. |
| Tổng hợp đầu ra | Đọc các kết quả vừa tạo và liệt kê bước tool đã chạy. | Bảng số đo, artifact và log của phiên. |

Trong đoạn triển khai vật lý hiện tại, ODB đã route là đầu vào thiết kế cho các bước xuất view và kiểm tra; cell synthesis là phép tổng hợp riêng từ RTL. Các recipe đo kiểm được giữ trong notebook cung cấp cách tạo stimulus và diễn giải kết quả. Cell chỉ định nghĩa hàm sẽ im lặng; cell chạy process in command và stdout/stderr thực tế.''')]


def apply_front_matter(book):
    """Change only Markdown; leave every code cell and saved output untouched."""
    inserted={cid for cid,_ in sections()}
    keep=[]
    for cell in book.cells:
        if cell.cell_type=='markdown' and (cell.id=='combined-progress-index' or cell.id in inserted):continue
        if cell.cell_type=='markdown' and 'CODEX_PROGRESS' in cell.source:
            cell.source='\n\n'.join(p for p in cell.source.split('\n\n') if 'CODEX_PROGRESS' not in p)
            if not cell.source.strip():continue
        keep.append(cell)
    intro=next(cell for cell in keep if cell.id=='combined-intro')
    intro.source=INTRO
    start=keep.index(intro)+1
    keep[start:start]=[nbf.v4.new_markdown_cell(text,id=cid) for cid,text in sections()]
    book.cells=keep
    from scripts.flow2_notebook_competition import apply_competition_front_matter
    return apply_competition_front_matter(book)
