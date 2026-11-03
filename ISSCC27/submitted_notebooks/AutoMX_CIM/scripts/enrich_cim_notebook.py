"""Add source-backed, executable CIM lessons and adjacent function-cell guides.

Only this authoring script reads strings from files. The generated notebook
contains the complete lesson implementations and needs no import of this module.
"""
from pathlib import Path
import ast
import copy
import json
import re
import sys
import nbformat as nbf

_AUTHORING_ROOT=Path(__file__).resolve().parents[1]
if str(_AUTHORING_ROOT) not in sys.path:sys.path.insert(0,str(_AUTHORING_ROOT))

REVISION = 'cell-to-macro-20261025-v3-deduplicated-notes'
OCP = 'https://www.opencompute.org/documents/ocp-microscaling-formats-mx-v1-0-spec-final-pdf'

ROADMAP = r'''## Đọc từ một phần tử số đến một macro CIM

Thuật ngữ được chú giải đầy đủ một lần tại nơi xuất hiện đầu tiên. Các hàm
hoặc hợp đồng dữ liệu có cùng nội dung sẽ dẫn về giải thích gốc; phần khác
nhau của từng bước vẫn được trình bày ngay trước code.

**Một cell ở đây là một phần tử nhân có dấu gồm 8 NMOS.** Hai transistor nối tiếp
tạo một nhánh điều kiện; bốn nhánh đưa tích dương về BLP và tích âm về BLN.
Thanh ghi `weight_pos_o/weight_neg_o` trong controller cung cấp `WPOS/WNEG`;
cell nhận các tín hiệu này ở cổng MOS. Từ đó, nhiều cell dùng chung bitline để
cộng dòng và điện tích. Chương thực hành ngay sau phần thiết lập sẽ xây lại
đúng netlist này, đối chiếu với schematic đầu vào và chạy ngspice ở mức leaf.

| Bước | Ta xây hoặc kiểm gì? | Sản phẩm dùng ở bước sau |
|---|---|---|
| F0 — thiết lập | namespace, đường dẫn bundle, thư mục lượt chạy | Mỗi phép đo có nơi ghi riêng |
| F1 — biểu diễn số | MXFP4 → `ACT_X2`; ternary → `WPOS/WNEG` | Oracle tổng nguyên, scale tách riêng |
| F2 — phần tử cơ sở | NMOS → nhánh 2T → cell vi sai 8T | SPICE leaf và bảng đường dẫn dẫn điện |
| F3 — ghép mảng | 4 cell/cột → 4 cột/core 4×4 | 16 cell, 128 NMOS, giao diện 50 chân |
| F4 — đọc analog | precharge → PWM → sample/hold → buffer/mux | Điện áp giữ ở HP/HN rồi AINP/AINN |
| F5 — kiểm trước layout | kích thích transistor, tổng nguyên, sweep tải/PWM | Chọn điểm làm việc có thể đọc được |
| F6 — kiểm sau layout | GDS/LEF → extraction → PEX → đo lại | Kết quả có R/C và hiệu ứng vật lý |
| F7 — chuyển đổi và ứng dụng | SAR, calibration/holdout, projection, MHA | Mã ADC → tổng nguyên → đầu ra số |
| F8 — tích hợp vật lý | RTL + ba macro → synthesis/PDN/place/CTS/route | Top GDS/DEF/LEF mới |
| F9 — kiểm và bàn giao | LVS, nguồn, RC/STA, render, manifest | Bộ kết quả của đúng lượt Run All |

Thứ tự **phụ thuộc thiết kế** là F1 → F9. Thứ tự **thực thi** có một phần song
song: cold PnR bắt đầu sớm, trong khi các phép đo analog đang chạy; các cell
phân tích cuối chờ đủ kết quả rồi mới kết luận. Khai báo hàm tạo công cụ cho
bước sau; các lệnh gọi hàm mới thực hiện phép đo hoặc chạy EDA. Mỗi cell khai
báo hàm bên dưới có thuyết minh riêng để chỉ rõ hai việc này.
'''

BOOT = '''from IPython.core.magic import register_cell_magic
import types as _cim_lesson_types
_cim_lesson_namespace = _cim_lesson_types.ModuleType("automx_cim_cell_lesson")
_cim_lesson_namespace.__dict__.update(
    EDU_ROOT=_design_review_namespace['BUNDLE'],
    EDU_OUT=_design_review_namespace['OUT']/'cell_to_macro')
@register_cell_magic
def cim_lesson(line, cell):
    """Execute one circuit lesson in its own namespace, outside native flow state."""
    exec(compile(cell, '<cim-lesson:'+line+'>', 'exec'), _cim_lesson_namespace.__dict__)
print('Chương cell → macro: namespace riêng; kết quả nằm trong cell_to_macro của lượt này.')
'''

LESSONS = [
('format',r'''## F1.1 — MXFP4 mang những bit nào?

MXFP4 dùng **32 phần tử E2M1 và một byte scale E8M0 dùng chung**, theo
[OCP MX v1.0, §5.2, §5.3.3 và §5.4.1](OCP_LINK). Phần tử có bit `s e1 e0 m`;
bit dấu tách khỏi ba bit chọn độ lớn. Trong source `automx_cim/mxfp4.py`, bảng
độ lớn là `0, 0.5, 1, 1.5, 2, 3, 4, 6`. Cell sau tự dựng bảng 16 mã và
minh họa một block 32 số; không phải phép cast sang số nguyên 4 bit.

Đặt `E` là byte E8M0 hữu hạn và `p` là giá trị E2M1 đã có dấu:

$$S=2^{E-127},\qquad \hat x=S p,\qquad A=\mathrm{ACT\_X2}=2p.$$

Suy ra công thức giao tiếp với mạch:

$$\boxed{\hat x=A\,2^{E-128}}.$$

`A` thuộc `{0, ±1, ±2, ±3, ±4, ±6, ±8, ±12}`. Mỗi block đóng gói tối thiểu
`32×4+8=136` bit, tức 17 byte hay 4,25 bit/phần tử trước padding/alignment.
Byte scale 0 vẫn là một scale khác 0; block toàn zero được biểu diễn bằng các
mã phần tử zero. Byte 255 là trường hợp NaN của scale, nên bài học chỉ nhận 0…254.
Mảng `codes` trong Python dùng container `uint8` cho từng nibble để dễ kiểm;
17 byte là kích thước payload sau khi pack hai nibble mỗi byte, không phải
`nbytes` của mảng NumPy chưa pack.

Nibble E2M1 là **4 bit mã floating-point**, còn `ACT_X2` ở giao diện RTL là
**số nguyên signed 5 bit**: `+12=01100`, `−12=10100` theo bù hai. Bus
`act_x2_i[19:0]` ghép bốn lane × 5 bit. Byte scale dùng chung vẫn được giữ
ở hợp đồng số phía ngoài core; không đưa mã E2M1 nguyên trạng vào bộ phát PWM.

Ví dụ `E=128`, phần tử `0101` có `p=3`, `A=6`: giá trị khôi phục là `6`.
Chia thêm 2 ở công thức cuối sẽ làm kết quả sai một nửa.

Codec hiện tại chọn scale bằng `ceil(log2(max(abs(x))/6))` và khi đúng giữa
hai mức thì chọn độ lớn nhỏ hơn. Đây là chính sách xác định trong source của
dự án. Bảng mã là E2M1; chính sách tie này cần đọc riêng với chế độ
round-to-nearest-even được nêu trong đặc tả. Cell minh họa cả hai để tránh
đồng nhất định dạng bit với một thuật toán lượng tử duy nhất.
'''.replace('OCP_LINK',OCP),r'''from pathlib import Path
import json, math, re, subprocess
from collections import Counter
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
EDU_OUT.mkdir(parents=True, exist_ok=True)
EDU_MAG = np.array([0., .5, 1., 1.5, 2., 3., 4., 6.])
def edu_table(headers, rows):
    display(Markdown('| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+
        '\n'.join('| '+' | '.join(map(str,row))+' |' for row in rows)))
def edu_decode(codes, scale_byte):
    codes=np.asarray(codes)
    if not 0<=int(scale_byte)<=254 or np.any((codes<0)|(codes>15)):
        raise ValueError('Mã E2M1 hoặc E8M0 hữu hạn không hợp lệ')
    p=np.where(codes & 8, -EDU_MAG[codes & 7], EDU_MAG[codes & 7])
    return p*np.exp2(int(scale_byte)-127)
def edu_quantize_block(values, tie='project'):
    values=np.asarray(values,dtype=float)
    if values.shape!=(32,) or not np.all(np.isfinite(values)):
        raise ValueError('Bài học nhận đúng một block gồm 32 số hữu hạn')
    maximum=float(np.max(abs(values)))
    e=-127 if maximum==0 else max(-127,min(127,math.ceil(math.log2(maximum/6))))
    distance=abs(abs(values/np.exp2(e))[:,None]-EDU_MAG[None,:])
    code=distance.argmin(axis=1)
    if tie=='rne':
        for i,row in enumerate(distance):
            nearest=np.flatnonzero(row==row.min())
            if len(nearest)>1:code[i]=next(int(k) for k in nearest if k%2==0)
    elif tie!='project':raise ValueError('tie phải là project hoặc rne')
    code=(code | (((values<0)&(code!=0)).astype(int)<<3)).astype(np.uint8)
    return code,e+127
edu_table(['Nibble','s','e1e0','m','p ở S=1','ACT_X2'],
    [[f'{i:04b}',i>>3,f'{(i>>1)&3:02b}',i&1,float(edu_decode([i],127)[0]),
      int(2*edu_decode([i],127)[0])] for i in range(16)])
edu_values=np.tile([0,.5,1,1.5,2,3,4,6],4)*np.where(np.arange(32)%3==0,-1,1)
edu_codes,edu_scale=edu_quantize_block(edu_values)
assert np.array_equal(edu_decode(edu_codes,edu_scale),edu_values)
assert edu_decode([0b0101],128)[0]==6
edu_tie=np.zeros(32);edu_tie[:2]=[.75,6]
edu_a,edu_e=edu_quantize_block(edu_tie,'project')
edu_b,_=edu_quantize_block(edu_tie,'rne')
print('32 phần tử; scale byte =',edu_scale,'; payload =',32*4+8,'bit = 17 byte')
print('Ví dụ tie 0.75, scale=1: project =',edu_decode(edu_a,edu_e)[0],
      '; nearest-even =',edu_decode(edu_b,edu_e)[0])
assert edu_decode(edu_a,edu_e)[0]==.5 and edu_decode(edu_b,edu_e)[0]==1
'''),
('ternary',r'''## F1.2 — Ternary là trọng số gì, được đưa vào mạch bằng cách nào?

Ternary có ba giá trị `−1, 0, +1`. Tại giao diện transistor:

$$w=WPOS-WNEG,\qquad (WPOS,WNEG)\in\{(1,0),(0,0),(0,1)\}.$$

`11` không phải một trọng số hợp lệ trong giao thức này. Nó mở cả các đường
P/N khi có activation, vì vậy controller chặn cấu hình có `cfg_wpos_i & cfg_wneg_i`.
Hai tín hiệu một-hot này là **mã điều khiển tại cell**; cách đóng gói ternary
ở file/model có thể khác. Ví dụ adapter QTEA dùng 5 trit/byte theo cơ số 3,
sau đó giải nén, chuyển trục `(output,input)` thành `(K,M)` và tạo hai mask.

Activation có dấu `A`: `A>0` phát PWM trên WLP, `A<0` phát PWM trên WLN,
`A=0` không phát xung. Độ lớn quyết định thời gian dẫn `T≈|A|τ`; dấu quyết định
nhánh dẫn. Cell dưới kiểm cả 3 trọng số × 15 activation nguyên có dấu = 45 tổ hợp.

Scale MXFP4 và hệ số trọng số được xử lý bên ngoài tích nguyên của leaf.
Trong đường base-only, một nhóm có hệ số `alpha` được khôi phục bằng
`alpha × 2^(E−128) × sum(A×T)`. Hệ số affine/residual của model, nếu dùng,
thuộc hợp đồng số riêng ở các cell reference; nó không được giấu vào `WPOS/WNEG`.
Ví dụ dựng tile ở chương này chọn `col_v=1`, `beta=0`, residual bằng 0;
payload QTEA tổng quát có thêm các nhánh hiệu chỉnh được giữ ở reference số.
''',r'''EDU_ALPHABET=np.array([0,1,2,3,4,6,8,12,-1,-2,-3,-4,-6,-8,-12],dtype=int)
def edu_weight_bits(weight):
    if weight not in (-1,0,1):raise ValueError('Trọng số phải là ternary')
    return int(weight==1),int(weight==-1)
def edu_active_paths(weight, activation):
    wp,wn=edu_weight_bits(weight);ap=int(activation>0);an=int(activation<0)
    return {'PP':wp*ap,'PN':wn*an,'NP':wn*ap,'NN':wp*an}
edu_truth=[]
for edu_w in (-1,0,1):
    for edu_a in EDU_ALPHABET:
        edu_paths=edu_active_paths(edu_w,int(edu_a))
        edu_signed=(edu_paths['PP']+edu_paths['PN']-edu_paths['NP']-edu_paths['NN'])*abs(int(edu_a))
        assert edu_signed==edu_w*edu_a
    for edu_sign in (-1,0,1):
        edu_truth.append([edu_w,edu_weight_bits(edu_w),edu_sign,edu_active_paths(edu_w,edu_sign),edu_w*edu_sign])
edu_table(['w','WPOS/WNEG','sign(A)','Nhánh bật','sign(wA)'],edu_truth)
print('PASS: 45 tổ hợp dấu/độ lớn; trọng số 0 luôn cho tích 0.')
'''),
('leaf',r'''## F2 — Từ NMOS đến một cell nhân vi sai 8T

MOS trong SPICE có thứ tự đầu cực `D G S B`. Leaf dùng model SKY130
`sky130_fd_pr__nfet_01v8`, mỗi transistor `W=0.84 µm`, `L=0.15 µm`, bulk nối
`VSUBS`. Hai MOS nối tiếp chỉ tạo đường xả khi cả tín hiệu trọng số và tín hiệu
activation cùng mở. Bốn nhánh sau thực hiện bảng dấu của phép nhân:

| Nhánh | Chuỗi nối | Điều kiện | Ý nghĩa |
|---|---|---|---|
| PP | BLP → MOS(WPOS) → NPP → MOS(WLP) → VGND | `w>0`, `A>0` | tích dương |
| PN | BLP → MOS(WNEG) → NPN → MOS(WLN) → VGND | `w<0`, `A<0` | tích dương |
| NP | BLN → MOS(WNEG) → NNP → MOS(WLP) → VGND | `w<0`, `A>0` | tích âm |
| NN | BLN → MOS(WPOS) → NNN → MOS(WLN) → VGND | `w>0`, `A<0` | tích âm |

BLP giảm nhiều hơn làm `V(BLN)−V(BLP)>0`; BLN giảm nhiều hơn làm đại lượng đó âm.
Như vậy tên bitline, dấu điện áp và oracle số thống nhất ngay ở leaf. Tín hiệu
trọng số được lưu trong register của controller, không phải trong tám NMOS này.
Precharge, tụ bitline, lấy mẫu và ADC là các mạch ngoại vi được ghép sau.

Cell mã tiếp theo **tự dựng cả tám dòng transistor**, rồi so từng dòng nối chân
với subcircuit thật trong `inputs/core_acquisition.spice`.
''',r'''EDU_BRANCHES=(('PP','BLP','WPOS','WLP','NPP'),('PN','BLP','WNEG','WLN','NPN'),
              ('NP','BLN','WNEG','WLP','NNP'),('NN','BLN','WPOS','WLN','NNN'))
def edu_leaf_netlist():
    rows=['.subckt automx_ternary_cell BLP BLN WLP WLN WPOS WNEG VGND VSUBS']
    for tag,bl,wgate,agate,middle in EDU_BRANCHES:
        rows += [f'X{tag}_W {bl} {wgate} {middle} VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15',
                 f'X{tag}_A {middle} {agate} VGND VSUBS sky130_fd_pr__nfet_01v8 W=0.84 L=0.15']
    return '\n'.join(rows+['.ends automx_ternary_cell'])+'\n'
def edu_subcircuits(text):
    result={};active=None
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith('*'):continue
        if line.startswith('+'):
            if active is None:raise ValueError('Continuation không có subckt')
            result[active][-1]+=' '+line[1:].strip()
        elif line.lower().startswith('.subckt '):
            active=line.split()[1];result[active]=[line]
        elif active is not None:
            result[active].append(line)
            if line.lower().startswith('.ends'):active=None
    return result
EDU_SOURCE=edu_subcircuits((EDU_ROOT/'inputs/core_acquisition.spice').read_text())
EDU_LEAF=edu_leaf_netlist()
assert EDU_LEAF.splitlines()==EDU_SOURCE['automx_ternary_cell']
(EDU_OUT/'ternary_cell.spice').write_text(EDU_LEAF)
print(EDU_LEAF)
print('PASS: 8 NMOS; 4 nhánh × 2 MOS; nối chân trùng schematic nguồn.')
'''),
('schematic',r'''### F2 — Nhìn đường dẫn điện trước khi nhân bản cell

Sơ đồ sau được vẽ từ chính `EDU_BRANCHES` vừa dùng tạo netlist. Hai nhóm trái/phải
ứng với hai bitline, mỗi cổng MOS ghi tên tín hiệu và tên instance. Nhờ dùng chung
dữ liệu topology, sơ đồ có thể đối chiếu với từng dòng SPICE ở cell trước.
Các đường bulk đều về VSUBS; ký hiệu gọn bỏ nét bulk lặp lại để dễ nhìn.
''',r'''def edu_draw_leaf():
    fig,ax=plt.subplots(figsize=(13,6));ax.set(xlim=(0,14),ylim=(0,8));ax.axis('off')
    for i,(tag,bl,wgate,agate,middle) in enumerate(EDU_BRANCHES):
        x=[2.0,5.0,9.0,12.0][i];color='#1767a4' if bl=='BLP' else '#b46019'
        ax.plot([x,x],[1,6.6],color=color,lw=2)
        for y,gate,suffix in [(5.2,wgate,'W'),(2.7,agate,'A')]:
            ax.plot([x,x],[y-.38,y+.38],color='white',lw=7)
            ax.plot([x,x],[y-.38,y+.38],color=color,lw=3)
            ax.plot([x-.15,x-.15],[y-.32,y+.32],color=color,lw=2)
            ax.plot([x-.8,x-.15],[y,y],color=color,lw=2)
            ax.text(x-.25,y+.48,gate,ha='right',weight='bold',fontsize=10)
            ax.text(x+.25,y,f'X{tag}_{suffix}',va='center',fontsize=9)
        ax.text(x+.2,3.9,middle,fontsize=10)
        ax.text(x,7.05,f'{tag}: '+('wA > 0' if bl=='BLP' else 'wA < 0'),ha='center',color=color,weight='bold')
    for x1,x2,bl,col in [(2,5,'BLP','#1767a4'),(9,12,'BLN','#b46019')]:
        ax.plot([x1,x2],[6.6,6.6],color=col,lw=3);ax.text((x1+x2)/2,6.75,bl,ha='center',color=col)
    ax.plot([2,12],[1,1],color='#334155',lw=2);ax.text(7,.65,'VGND',ha='center')
    ax.text(7,.08,'Mỗi MOS: W/L = 0.84/0.15 µm; bulk → VSUBS.  ΔV = V(BLN) − V(BLP).',ha='center',fontsize=11)
    fig.tight_layout();fig.savefig(EDU_OUT/'ternary_cell.svg');fig.savefig(EDU_OUT/'ternary_cell.png',dpi=150)
    plt.show();plt.close(fig)
edu_draw_leaf()
'''),
('column',r'''## F3.1 — Ghép bốn cell thành một cột 4×1

Bốn cell của một cột nối song song lên cùng `BLP/BLN`. Mỗi hàng có một cặp
wordline theo dấu activation và một cặp điều khiển trọng số. Tại bitline,
dòng của các hàng cộng theo định luật Kirchhoff; tích phân dòng làm thay đổi
điện tích trên tải. Trong vùng gần tuyến tính:

$$\Delta V_c \approx \frac{I_{unit}\tau}{C_{BL}}\sum_r A_rT_{r,c}.$$

Đây là mô hình để hiểu cơ chế, không phải công thức dùng thay các phép đo transistor.
Dòng phụ thuộc điện áp, NMOS mắc nối tiếp có node trung gian, tải và R/C thay đổi
theo layout; đó là lý do flow còn có sweep, PEX và calibration.

Cột 4×1 có 4 leaf, tức 32 NMOS. Hàm tạo cột dưới đây nối đúng vị trí chân
`BLP BLN WLP WLN WPOS WNEG VGND VSUBS` của mỗi leaf và đối chiếu nguồn thật.
''',r'''def edu_column_netlist(rows=4):
    pins=['BLP','BLN']+[p for r in range(rows) for p in (f'WLP{r}',f'WLN{r}',f'WPOS{r}',f'WNEG{r}')]+['VGND','VSUBS']
    lines=[f'.subckt automx_ternary_column_{rows}x1 '+' '.join(pins)]
    lines += [f'XCELL{r} BLP BLN WLP{r} WLN{r} WPOS{r} WNEG{r} VGND VSUBS automx_ternary_cell' for r in range(rows)]
    return '\n'.join(lines+[f'.ends automx_ternary_column_{rows}x1'])+'\n'
EDU_COLUMN=edu_column_netlist()
assert EDU_COLUMN.splitlines()==EDU_SOURCE['automx_ternary_column_4x1']
(EDU_OUT/'column_4x1.spice').write_text(EDU_LEAF+EDU_COLUMN)
print(EDU_COLUMN)
print('PASS: một cột = 4 leaf = 32 NMOS; 20 chân ở biên subcircuit.')
'''),
('array',r'''## F3.2 — Ghép bốn cột thành core CIM 4×4

Các cột có bitline riêng; các hàng chia sẻ `WLP_r/WLN_r` để cùng một activation
đi vào bốn trọng số khác nhau. Mỗi giao điểm `(r,c)` giữ một cặp dây điều khiển
`WPOS_r_c/WNEG_r_c`. Vì vậy một lượt compute tạo bốn tổng theo cột.

| Nhóm chân core | Số chân | Chức năng |
|---|---:|---|
| BLP/BLN theo cột | 8 | bốn kết quả analog vi sai |
| WLP/WLN theo hàng | 8 | dấu và PWM của bốn activation |
| WPOS/WNEG theo giao điểm | 32 | 16 trọng số ternary |
| VGND, VSUBS | 2 | đường xả và bulk |
| **Tổng** | **50** | giao diện leaf-array, chưa gồm ngoại vi |

Core có `4×4×8=128` NMOS. Các con số 4×4 vật lý và block MXFP4 32 phần tử
thuộc hai cấp khác nhau: scheduler tái sử dụng core theo các lát của trục K.
Cell sau tạo cả hierarchy SPICE, kiểm chân/kết nối với source và vẽ vị trí
logic của 16 leaf; đây là sơ đồ tổ chức, không phải một phép place-and-route.
''',r'''def edu_core_netlist(rows=4,cols=4):
    pins=[p for c in range(cols) for p in (f'BLP{c}',f'BLN{c}')]
    pins += [p for r in range(rows) for p in (f'WLP{r}',f'WLN{r}')]
    pins += [p for r in range(rows) for c in range(cols) for p in (f'WPOS_{r}_{c}',f'WNEG_{r}_{c}')]+['VGND','VSUBS']
    lines=[f'.subckt automx_ternary_cim_{rows}x{cols}_core '+' '.join(pins)]
    for c in range(cols):
        rp=[p for r in range(rows) for p in (f'WLP{r}',f'WLN{r}',f'WPOS_{r}_{c}',f'WNEG_{r}_{c}')]
        lines.append(f'XCOL{c} BLP{c} BLN{c} '+' '.join(rp)+f' VGND VSUBS automx_ternary_column_{rows}x1')
    return '\n'.join(lines+[f'.ends automx_ternary_cim_{rows}x{cols}_core'])+'\n'
EDU_CORE=edu_core_netlist()
assert EDU_CORE.splitlines()==EDU_SOURCE['automx_ternary_cim_4x4_core']
assert len(EDU_CORE.splitlines()[0].split()[2:])==50
(EDU_OUT/'core_4x4.spice').write_text(EDU_LEAF+EDU_COLUMN+EDU_CORE)
print(EDU_CORE)
fig,ax=plt.subplots(figsize=(10,5));ax.set(xlim=(-1.7,4.5),ylim=(-.7,4.8));ax.axis('off')
for r in range(4):
    y=3-r
    ax.plot([-.6,3.7],[y,y],color='#20948b',lw=2)
    ax.text(-.8,y,f'WLP{r}/WLN{r}',ha='right',va='center',fontsize=9)
    for c in range(4):
        ax.plot([c,c],[-.35,3.7],color='#3574b3',lw=1.2,zorder=0)
        ax.add_patch(plt.Rectangle((c-.32,y-.25),.64,.5,facecolor='white',edgecolor='#334155',zorder=2))
        ax.text(c,y,f'8T\n(r{r},c{c})',ha='center',va='center',fontsize=9,zorder=3)
for c in range(4):ax.text(c,4.05,f'BLP{c}/BLN{c}',ha='center',fontsize=9)
ax.set_title('Core 4×4: wordline dùng chung theo hàng; bitline dùng chung theo cột')
fig.tight_layout();fig.savefig(EDU_OUT/'core_4x4.svg');plt.show();plt.close(fig)
print('PASS: 16 leaf, 128 NMOS, 50 chân; hierarchy khớp schematic nguồn.')
'''),
('analog',r'''## F4 — Biến core trần thành macro có thể lấy mẫu và đọc

Core trần chỉ xả điện tích. Macro `core_i` còn ghép **acquisition**:

1. **Precharge:** PMOS `XPRE_Pc/XPRE_Nc` nạp BLP/BLN lên VPWR khi `PRE_B=0`.
2. **Compute:** nhả precharge, phát WLP hoặc WLN; cell xả bitline theo tích có dấu.
3. **Track/hold:** transmission gate NMOS+PMOS nối BLP→HP, BLN→HN lúc track,
   rồi ngắt để giữ điện áp trên tụ MIM `XCH`. Hai inverter tạo `TRACK_B/TRACK_N`.
4. **Tải bitline:** bank tụ MIM `XBLCH` tạo tải thật trong schematic/layout;
   ngân sách tải ảnh hưởng độ nhạy lẫn thời gian ổn định.
5. **Conditioner/mux:** `condition_i` có bias, source follower và transmission
   gate chọn một cặp HP/HN thành AINP/AINN cho ADC dùng chung.

Một cặp TG cần cả MOS N và P để truyền dải điện áp rộng hơn một pass-NMOS.
Giữ HP/HN tách khỏi bitline giúp ADC có thời gian quyết định sau khi compute.
Đổi cột phải điều khiển select, khoảng chết và settling để tránh trộn mẫu.
Cell sau đọc trực tiếp schematic, đếm đệ quy transistor/tụ và in đường ghép
`XCORE → XACQ`, thay vì ước lượng số linh kiện từ tên block.
''',r'''EDU_CONDITIONER=edu_subcircuits((EDU_ROOT/'inputs/conditioner.spice').read_text())
EDU_HIER={**EDU_SOURCE,**EDU_CONDITIONER}
def edu_model_of(line):
    tokens=line.split();end=next((i for i,t in enumerate(tokens) if '=' in t),len(tokens))
    return tokens[end-1]
def edu_inventory(name, seen=()):
    if name in seen:raise ValueError('Hierarchy có vòng lặp')
    total=Counter()
    for line in EDU_HIER[name][1:-1]:
        if not line.upper().startswith('X'):continue
        model=edu_model_of(line)
        if model in EDU_HIER:total.update(edu_inventory(model,seen+(name,)))
        else:total[model]+=1
    return total
edu_table(['Subcircuit','NMOS','PMOS','MIM'],[[name,
    edu_inventory(name)['sky130_fd_pr__nfet_01v8'],
    edu_inventory(name)['sky130_fd_pr__pfet_01v8'],
    edu_inventory(name)['sky130_fd_pr__cap_mim_m3_1']] for name in
    ['automx_ternary_cell','automx_ternary_column_4x1','automx_ternary_cim_4x4_core',
     'automx_cim_acquisition_4col_proto','automx_cim_core_acquisition_proto','automx_cim_condition_mux_proto']])
assert edu_inventory('automx_ternary_cim_4x4_core')['sky130_fd_pr__nfet_01v8']==128
edu_acq=EDU_SOURCE['automx_cim_acquisition_4col_proto']
edu_hold=sum(x.startswith('XCH_') for x in edu_acq)
edu_load=sum(x.startswith('XBLCH_') for x in edu_acq)
assert (edu_hold,edu_load)==(8,160)
print('Acquisition: 8 tụ hold + 160 phần tử MIM tải bitline; 8 đường sample dùng TG.')
print('\n'.join(EDU_SOURCE['automx_cim_core_acquisition_proto'][1:-1]))
(EDU_OUT/'hierarchy_inventory.json').write_text(json.dumps({n:dict(edu_inventory(n)) for n in EDU_HIER},indent=2))
'''),
('leaf-spice',r'''## F5 — Kiểm cell nhỏ nhất bằng transistor thật trước khi tin vào mảng

Cell này chạy **ngspice DC trên đúng leaf 8 NMOS vừa dựng**. Có 9 cấu hình:
3 trọng số × 3 dấu activation. Hai bitline được fixture giữ ở 1 V; gate logic
được đặt 0 hoặc 1,8 V. Ta đọc dòng xả `I_P/I_N` qua hai nguồn bias để xác nhận
nhánh dẫn đúng bảng dấu. Leaf chỉ dùng NFET nên deck nạp nguyên file model TT
và mismatch của `nfet_01v8`, cùng scale hình học 1 µm, từ PDK đi kèm. Hai file
này chính là các include NFET trong `libs.tech/ngspice/corners/tt.spice`;
không cần nạp hàng loạt model RF/HV và linh kiện khác cho bài thử nhỏ này.

Theo chiều dòng của nguồn SPICE, dòng cấp vào leaf là `I_P=−I(VBP)` và
`I_N=−I(VBN)`, nên đại lượng có dấu là `I_P−I_N=I(VBN)−I(VBP)`.
Chỉ đo dòng ở mức DC giúp kiểm đường nhân nhanh, không cần giải một transient
rất dài cho bài học. **9 điểm này kiểm dấu ở transistor**; 45 tổ hợp giá trị
nguyên đã được kiểm ở bảng logic F1.2. Độ lớn activation được mang bằng thời gian
PWM, không phải bằng đổi biên độ gate DC. Các cell factorial/PEX/waveform phía
sau tiếp tục kiểm động học, tải, sample/hold và khả năng giải mã nhiều hàng.
''',r'''def edu_leaf_dc():
    models=EDU_ROOT/'pdks/analog/sky130A/libs.ref/sky130_fd_pr/spice'
    lines=['.title Nine DC sign states of the source-matched 8T leaf',
           '.param mc_mm_switch=0 mc_pr_switch=0','.option scale=1u',
           f'.include "{models}/sky130_fd_pr__nfet_01v8__tt.pm3.spice"',
           f'.include "{models}/sky130_fd_pr__nfet_01v8__mismatch.corner.spice"',
           EDU_LEAF,'.temp 27','.option reltol=1e-4']
    cases=[]
    for w in (-1,0,1):
        for a in (-1,0,1):
            i=len(cases);wp,wn=edu_weight_bits(w)
            nodes=[f'{p}{i}' for p in ('BP','BN','AP','AN','WP','WN')]
            bp,bn,ap,an,p,n=nodes
            lines += [f'VBP{i} {bp} 0 1',f'VBN{i} {bn} 0 1',
                      f'VWP{i} {p} 0 {1.8*wp}',f'VWN{i} {n} 0 {1.8*wn}',
                      f'VAP{i} {ap} 0 {1.8*int(a>0)}',f'VAN{i} {an} 0 {1.8*int(a<0)}',
                      f'XC{i} '+' '.join(nodes)+' 0 0 automx_ternary_cell']
            cases.append({'weight':w,'activation_sign':a,'truth_sign':w*a})
    lines += ['.control','op']
    for i in range(len(cases)):
        lines += [f'let leaf_{i}=i(VBN{i})-i(VBP{i})',f'print leaf_{i}']
    lines += ['quit','.endc','.end']
    deck=EDU_OUT/'leaf_dc9.spice';deck.write_text('\n'.join(lines)+'\n')
    command=['ngspice','-b',str(deck)];log=EDU_OUT/'leaf_dc9.ngspice.log'
    print('RUN:', ' '.join(command),flush=True)
    with log.open('w') as stream:
        result=subprocess.run(command,cwd=EDU_OUT,stdout=stream,stderr=subprocess.STDOUT,text=True,timeout=45)
    transcript=log.read_text();print(transcript,flush=True)
    if result.returncode:raise RuntimeError('ngspice DC leaf không hoàn tất')
    measured=dict((int(k),float(v)) for k,v in re.findall(r'^leaf_(\d+)\s*=\s*([-+\d.eE]+)',transcript,re.M))
    assert len(measured)==9
    for i,row in enumerate(cases):
        row['differential_current_a']=measured[i]
        if row['truth_sign']==0:assert abs(measured[i])<1e-10,(i,row)
        else:assert measured[i]*row['truth_sign']>1e-7,(i,row)
    (EDU_OUT/'leaf_dc9.json').write_text(json.dumps(cases,indent=2))
    return cases
EDU_LEAF_MEASURED=edu_leaf_dc()
edu_table(['w','sign(A)','sign(wA)','I_P − I_N / µA'],
    [[r['weight'],r['activation_sign'],r['truth_sign'],r['differential_current_a']*1e6] for r in EDU_LEAF_MEASURED])
fig,ax=plt.subplots(figsize=(9,4))
ax.bar(np.arange(9),[r['differential_current_a']*1e6 for r in EDU_LEAF_MEASURED],color='#1767a4')
ax.set(xticks=np.arange(9),xticklabels=[f"w={r['weight']}, a={r['activation_sign']}" for r in EDU_LEAF_MEASURED],
       ylabel='I_P − I_N / µA',title='Ngspice TT: bảng dấu DC của leaf 8T, bitline bias 1 V')
ax.tick_params(axis='x',labelrotation=45);ax.axhline(0,color='#334155',lw=1)
fig.tight_layout();fig.savefig(EDU_OUT/'leaf_signed_current.png',dpi=150);plt.show();plt.close(fig)
print('PASS: 9/9 dấu/zero từ dòng transistor; 45/45 tổ hợp nguyên được kiểm riêng ở F1.2.')
'''),
('tiling',r'''## F7 — Một block MXFP4 32 phần tử đi qua core 4 hàng như thế nào?

Với một nhóm K=32, scheduler chia thành 8 lát, mỗi lát 4 activation. Bốn cột
cho bốn output của projection. Sau các lượt đọc, tổng nguyên từng lát được cộng
lại rồi mới áp dụng shared scale và `alpha` của nhóm. Cell dưới chứng minh phép
chia lát không đổi kết quả: `sum(tile_sums) == ACT_X2 @ T` và kết quả khôi phục
bằng phép nhân số thực trên chính các giá trị MXFP4 đã decode.

Trong `rtl/automx_cim_readout_seq.sv`, top vật lý thực hiện **hai phase 2+2**,
đọc lần lượt bốn cột bằng ADC chung: 8 conversion cho một lát 4×4. Khi triển khai
đủ một block 32×4 theo giao thức này, lịch có 8 lát × 8 = 64 conversion.
Các record co-simulation ở phần study phía sau là phép đo từng pattern bốn hàng
qua partition SAR; phép fit affine ba điểm của study và LUT 2+2 trong controller
là hai hợp đồng calibration được trình bày riêng. Cell này kiểm phép cộng/tile
và giao diện số, không thay các phép đo transistor/RTL ấy.
''',r'''def edu_tiled_projection(act_x2,ternary,scale_byte,alpha):
    act_x2=np.asarray(act_x2,dtype=int);ternary=np.asarray(ternary,dtype=int)
    if act_x2.shape!=(32,) or ternary.shape!=(32,4) or not np.isin(ternary,[-1,0,1]).all():
        raise ValueError('Cần một block 32×4 và trọng số ternary')
    partial=np.stack([act_x2[k:k+4]@ternary[k:k+4] for k in range(0,32,4)])
    phases=np.stack([np.stack([act_x2[k:k+2]@ternary[k:k+2],act_x2[k+2:k+4]@ternary[k+2:k+4]])
                     for k in range(0,32,4)])
    assert np.array_equal(phases.sum(axis=1),partial)
    summed=partial.sum(axis=0);assert np.array_equal(summed,act_x2@ternary)
    return summed*np.exp2(int(scale_byte)-128)*np.asarray(alpha),partial,phases
edu_vector=np.tile(np.arange(8,dtype=np.uint8),4)
edu_vector[1::3]|=8
edu_x2=(2*edu_decode(edu_vector,127)).astype(int)
edu_t=np.random.default_rng(7).integers(-1,2,size=(32,4))
edu_alpha=np.array([.5,.25,1.,2.])
edu_y,edu_partial,edu_phases=edu_tiled_projection(edu_x2,edu_t,128,edu_alpha)
edu_reference=(edu_decode(edu_vector,128)@edu_t)*edu_alpha
assert np.array_equal(edu_y,edu_reference)
edu_table(['Lát K','Tổng cột 0…3','2 phase nguyên'],
    [[f'{4*k}…{4*k+3}',edu_partial[k].tolist(),edu_phases[k].tolist()] for k in range(8)])
print('Tổng được khôi phục:',edu_y,'; reference:',edu_reference)
print('PASS: MX block32 → 8 lát4×4 → tích lũy nguyên → scale; lịch top2+2 có 64 conversions/block32×4.')
'''),
]

BRIDGE = r'''## F4 → F9 — Các cell nhỏ trở thành top mixed-signal

| Mức | Đối tượng cụ thể trong bundle | Vai trò ở flow |
|---|---|---|
| MOS | model `nfet_01v8`, `pfet_01v8`, `cap_mim_m3_1` | phương trình thiết bị và linh kiện vật lý |
| Nhánh/leaf | `automx_ternary_cell` | tích có dấu bằng bốn đường xả |
| Cột/core | `automx_ternary_column_4x1`, `automx_ternary_cim_4x4_core` | cộng bốn hàng, tạo bốn output |
| Macro nguồn | `automx_cim_core_acquisition_proto` → `core_i` | core, precharge, sample/hold, MIM |
| Đường đọc | `automx_cim_condition_mux_proto` → `condition_i` | bias, buffer, chọn cột đến AINP/AINN |
| ADC | `adc_top` → `adc_i` | chuyển điện áp vi sai thành mã số |
| Controller | `automx_cim_readout_seq` → `seq_i` | register trọng số, PWM, 2+2, select, handshake, calibration |
| Top | `automx_cim_mixed_signal_proto` | nối bốn instance trên, clock/reset và nguồn |

### F6 — Từ sơ đồ 8T sang hình học vật lý

Ở cấp layout, mỗi NMOS có vùng active trong nền p, poly cắt active tạo gate,
contact đưa source/drain/gate lên mạng kim loại và tap nối bulk về VSUBS.
Hai MOS nối tiếp phải cùng có node giữa NPP/NPN/NNP/NNN; BLP và BLN phải tách
đúng hai nhóm nhánh. Khi lặp thành mảng, router giữ wordline theo hàng và
bitline theo cột, rồi đặt chân biên cho LEF. Ngoại vi thêm PMOS trong n-well,
well/tap về VPWR và các tụ MIM ở lớp kim loại phù hợp của PDK.

Trình tự kiểm là: dựng hình học → DRC theo PDK → extract transistor → LVS với
schematic → PEX R/C → mô phỏng lại cùng stimulus. Trong recipe Stage5,
`expected_nfets=4×4×8` được đối chiếu với netlist layout trước Netgen.
Vì vậy kiểm 128 NMOS là kiểm số lượng; LVS tiếp tục kiểm đúng kết nối, còn
PEX trả lời thay đổi điện áp/timing sau layout. Sơ đồ mảng vừa vẽ là sơ đồ
logic; ảnh hình học thật nằm ở các cell KLayout macro và top phía sau.

### F7 — Thanh ghi trọng số và bộ giải mã đọc

Controller giữ hai mask 16 bit cho 16 trọng số, cập nhật theo hàng khi
`cfg_valid_i && cfg_ready_o`; điều kiện ready loại mã `WPOS=WNEG=1`.
Mỗi lane ACT_X2 là 5 bit bù hai. Bộ đọc 2+2 có 39 mức partial sum reachable,
từ −24 đến +24 nhưng không phải mọi số nguyên ở giữa đều reachable. Có
38 ngưỡng giữa các mức × 4 cột × 2 phase = **304 threshold 12 bit**,
đúng với mảng `thresholds[0:303]` và address 9 bit trong RTL. Như vậy LUT này
được tổ chức theo phase/cột; phép fit ba điểm của study SAR có contract riêng.

Trình tự top controller được đọc từ RTL là:
`BOOT → IDLE → PRE → RELEASE → PULSE → HOLD → DEAD → SETTLE → EOC_LOW → START →
WAIT_EOC → WORD_SETTLE → CAPTURE → DECODE → ADVANCE → RESULT`.
`ADVANCE` lặp qua cột và phase; `FAULT` xử lý lỗi/timeout; `CAL_PREV/CAL_NEXT`
kiểm láng giềng khi ghi threshold. Có handshake nên một kết quả chỉ được chốt
khi ADC thực sự báo hoàn thành, và được giữ khi phía nhận chưa ready.

**Tại sao vẫn cần schematic, layout, LEF và PEX?** Schematic diễn tả kết nối;
layout đặt diffusion/gate/contact/metal/well và các tụ; LEF cho top placer biết
outline, chân và vùng cản; PEX gắn R/C trích từ layout để đo lại. SPICE được tạo
ở chương này là schematic source; các cell layout/PEX giữ bên dưới kiểm phần
vật lý, còn cold PnR ghép các hard-macro IP với digital wrapper để tạo top mới.
Các phép so sánh topology không được coi là đã tái sinh GDS từ netlist.

Ngay sau chương này, tuyến cũ tiếp tục: reference/schedule → sinh mạch → đo lỗi
transfer → chọn tải/PWM → SAR/calibration/holdout → MHA → cold top → LVS/PG/STA.
Như vậy bài học leaf có đầu ra SPICE và phép đo riêng, còn kết quả top tiếp tục
dựa trên các cell đo kiểm và tool log đã có trong notebook.
'''

# stage, operation, rationale, input -> output. One context per function cell.
CONTEXT = {}
def context(ids, stage, operation, rationale, io):
    for cid in ids.split():CONTEXT[cid]=(stage,operation,rationale,io)

context('argument-bootstrap full-lab-config native-runall-config','F0',
 'Tạo cell magic, namespace và nơi ghi source/log cho các cell tiếp theo.',
 'Các chương phân tích và implementation có nhiều tên hàm trùng nhau; tách môi trường giúp ghép được chúng mà không đổi hợp đồng dữ liệu.',
 'Cấu hình bundle và thứ tự notebook → bộ thực thi cell, module trong kernel và thư mục lượt chạy.')
context('standalone-runtime','F0, F6, F8–F9',
 'Khai báo bộ chạy standalone: dựng config cold PnR, gọi tool, xuất view, đo/check vật lý và nối evidence mới vào phần phân tích.',
 'Một lượt chạy phải tạo top và bản ghi mới từ RTL/IP/PDK đi kèm; các bước dùng chung cần thống nhất đường dẫn, timeout và điều kiện chấp nhận.',
 'Source bundle + work directory → các hàm container/start/streamout/lvs/power/timing/export/publish; lệnh gọi xuất hiện ở từng bước tương ứng.')
context('setup native-inline-presentation','F0',
 'Khai báo helper trình bày bảng, đọc JSON, lưu figure và in số đo/log.',
 'Kết quả số phải có cách đọc thống nhất, để người xem theo được từ input đến quyết định thiết kế.',
 'Dữ liệu trong lượt chạy → bảng, figure và output cell; không tạo số đo transistor.')
context('architecture','F1 → F9',
 'Khai báo khối và mũi tên để vẽ đường activation/weight → CIM → ADC → MHA.',
 'Sơ đồ hệ thống đặt tên các giao diện trước khi đi sâu vào mạch hoặc phần mềm.',
 'Nhãn và tọa độ khối → figure kiến trúc; số liệu đo đến từ các cell thực nghiệm phía sau.')
context('native-inline-history native-inline-story native-restored-archive-104','F5–F9 / đọc ngữ cảnh',
 'Khai báo hàm đọc và tóm tắt report, lần theo quan hệ input/output và hiển thị trạng thái artifact.',
 'Cần phân biệt kết quả làm tiền đề thiết kế với bản ghi mà lượt mới đang dùng để chấm.',
 'Report và metadata → bảng nguồn/kết quả. Một hàm được định nghĩa ở đây chưa đồng nghĩa recipe đó đã được thực thi.')
context('native-restored-archive-009','F0',
 'Xác định thư mục dự án bằng các file đặc trưng thay vì dựa vào đường dẫn tùy ý.',
 'Các import và đường dẫn PDK/RTL phải xuất phát từ cùng một root.',
 'Working directory/cấu trúc source → project root cho recipe tham chiếu.')
context('native-inline-legacy_attention native-inline-attention','F1, F7',
 'Khai báo projection/reference attention, softmax ổn định và thước đo sai số.',
 'Mạch trả các tổng có dấu; cần oracle độc lập để phân biệt sai số chuyển đổi với sai số lượng tử của ứng dụng.',
 'X, Q/K/V/O hoặc projection đo được → đầu ra MHA và relative L2.')
context('native-inline-legacy_schedule','F1 → F3',
 'Tạo và kiểm lịch tái sử dụng tile cho Q/K/V, attention và output projection.',
 'Block32 và core4 hàng có kích thước khác nhau; schedule phải giữ đúng thứ tự phụ thuộc và cộng partial sum.',
 'Kích thước tensor/tile → danh sách transaction và manifest lịch.')
context('native-inline-legacy_stage4_generator','F2–F5',
 'Dựng SPICE theo hierarchy cell → column → core và tạo testbench/PWM/precharge/measurement.',
 'Cùng một định nghĩa chân phải được dùng ở mọi cấp; generator giúp tăng kích thước mảng mà không chép nhầm dây.',
 'Config mạch + model SKY130 → netlist, deck và danh sách phép đo cho leaf/cột/mảng.')
context('native-inline-legacy_stage4_runner','F5',
 'Khai báo runner ngspice và thu các measurement của manifest mạch.',
 'Một deck chỉ là mô tả bài toán; cần return code, log và đủ measurement mới coi là phép đo hoàn tất.',
 'SPICE jobs → transcript, giá trị đo và report thực thi.')
context('native-inline-legacy_stage5 native-restored-archive-030','F6',
 'Kiểm giao diện core, chuẩn bị layout/LEF, chạy hoặc đọc DRC/LVS/PEX và audit tool.',
 'Schematic đúng chưa bảo đảm layout đúng; pin/ground landing và model trích xuất phải dùng được ở cấp top.',
 'Core schematic/PDK/config → view vật lý, report connectivity và PEX cho đo sau layout.')
context('native-inline-legacy_stage6','F6 → F7',
 'Fit mô hình transfer từ các mẫu vật lý và dùng nó trong phép chiếu/MHA.',
 'Độ lớn điện áp không tự là tổng nguyên; mô hình trung gian cho phép đánh giá cách đọc trước khi tích hợp ADC đầy đủ.',
 'Bản ghi điện áp/tổng chuẩn → transfer model và sai số ứng dụng.')
context('native-inline-fresh-pilot native-story-transfer_error native-restored-archive-036 native-restored-archive-039','F5–F6',
 'Tạo hoặc phân tích stimulus có tổng chuẩn đã biết, đo bitline và phát hiện cặp mức đảo thứ tự.',
 'Nếu hai tổng liền kề không có thứ tự điện áp ổn định thì scalar decoder chưa có cơ sở để hoạt động.',
 'Activation/ternary, tải, PWM và schematic/PEX → điện áp, gap và mẫu khó cho bước can thiệp.')
context('native-restored-archive-042 native-restored-archive-045 native-restored-archive-048 native-story-candidate_result factorial-result','F5–F6',
 'So sánh các lựa chọn tải/PWM, đối chiếu schematic–PEX và tính gap cho cùng cặp stimulus.',
 'Thay nhiều tham số cùng lúc không cho biết nguyên nhân; factorial và phép đo ghép cặp tách tác động tải khỏi thời gian xung.',
 'Điều kiện baseline/candidate và log ngspice → bảng gap, interaction và lựa chọn điểm đọc.')
context('native-restored-archive-051 native-restored-archive-063','F6–F7',
 'Sinh các mẫu holdout và kiểm kết quả bằng calibration đã được cố định.',
 'Dùng lại pattern fit để chấm sẽ không kiểm được khả năng giải mã dữ liệu mới.',
 'Fit/reference và payload mới → report holdout có oracle độc lập.')
context('native-restored-archive-054 native-restored-archive-057 native-restored-archive-060 native-story-decoder_errors native-restored-archive-066','F6–F7',
 'Phân tích các mức chồng lấn, ngưỡng giải mã, độ bao phủ calibration và feature đọc.',
 'Có điện áp chưa đủ để nói có phép tính đúng; phải đếm lỗi giải mã và biết mức nào thiếu hoặc khó phân biệt.',
 'Measurement có nhãn tổng nguyên → decoder, confusion/error report và cơ sở chọn cách đọc.')
context('native-restored-archive-069 native-restored-archive-072 native-restored-archive-075 native-story-partition_result','F6–F7',
 'Chia phép đọc bốn hàng thành 2+2, đo/calibrate các partial sum rồi cộng lại số.',
 'Giảm số hàng đồng thời có thể giảm chồng lấn mức; đổi protocol phải kéo theo phép đo và ngưỡng riêng.',
 'Mẫu khó, phép đọc hai phase và fit đã khóa → partial sums, tổng khôi phục và lỗi holdout.')
context('native-restored-archive-078','F6',
 'Liệt kê model corners và tạo các smoke test theo mẫu tải/xung khó.',
 'Mức điện áp và tốc độ phụ thuộc model thiết bị; cấu hình corner phải rõ trước khi so kết quả.',
 'Section PDK và tập mẫu chọn → deck/report theo corner của recipe này.')
context('native-restored-archive-085 native-restored-archive-088 native-restored-archive-091','F7–F8',
 'Sinh vector và testbench Icarus cho phép cộng, reset, backpressure và protocol hai lượt đọc.',
 'Controller có thể sai thứ tự hoặc mất dữ liệu ngay cả khi từng tổng analog đúng; cần kiểm giao thức tách khỏi phép đo transistor.',
 'Oracle nguyên, lịch giao dịch và stimulus → RTL log và kết quả regression.')
context('native-restored-archive-095 native-restored-archive-101','F8–F9',
 'Kiểm macro pin/outline/PDN và cấu hình OpenLane trước hoặc sau tích hợp.',
 'Top cần outline/LEF và đường nguồn phù hợp với GDS của macro; không thể chỉ nối tên module ở RTL rồi bỏ qua vật lý.',
 'RTL, LEF/GDS, placement và config → preflight/audit cho floorplan và routing.')
context('native-inline-geometry_common native-inline-support','F0, F6, F8–F9',
 'Khai báo runner, quản lý artifact/log, helper geometry, constraints và parsing kết quả EDA.',
 'Các stage cần cùng cách định nghĩa input, output và lỗi tool để checker không nhận nhầm một lần chạy dở thành kết quả đúng.',
 'Lệnh/tool inputs → process return code, log, receipt, view và helper đọc báo cáo. Runtime standalone cung cấp đường chạy cold đang dùng.')
context('native-inline-pg-worker-source','F9 / helper tham chiếu',
 'Khai báo cách xác định vị trí bridge nguồn/ground từ geometry.',
 'Liên kết rail của macro cần được đặt tại chân và strap thật; tọa độ hoặc tên net riêng lẻ chưa chứng minh connectivity.',
 'Macro placement và hình kim loại → vị trí bridge. Kiểm nguồn active dùng native Tcl trong standalone-runtime.')
context('native-inline-waveforms raw-reader','F5, F7',
 'Đọc waveform ngspice, nội suy mẫu và trích các mốc lấy mẫu/điều khiển.',
 'Một giá trị summary không cho thấy được thời điểm sample hay settling; waveform giúp kiểm quan hệ thời gian.',
 'Raw waveform và log → vector thời gian/điện áp, sample witness và dữ liệu vẽ.')
context('native-inline-klayout_checks','F6, F9',
 'Tóm tắt report DRC theo nhóm rule và kiểm độ hoàn tất của lần chạy.',
 'Không thấy violation trong report dở không đồng nghĩa một deck DRC đã chạy hết.',
 'XML/log và nhóm rule đã bật → trạng thái hoàn tất, số violation hoặc trạng thái timeout.')
context('native-inline-adc_partition native-inline-cosim','F4–F7',
 'Dựng partition ADC và cầu điều khiển giữa SAR RTL Icarus với transistor ngspice.',
 'Mã SAR phải xuất phát từ chuỗi quyết định comparator theo điện áp, không phải được tính thẳng từ tổng chuẩn.',
 'Schematic ADC/core, stimulus, điều khiển SAR và model thiết bị → waveform, state transcript và mã conversion.')
context('native-runall-partition-sources native-runall-calibration native-runall-measured-mha','F7',
 'Quản lý payload conversion, đo calibration, yêu cầu projection và ghép kết quả MHA.',
 'Cần dùng cùng đường analog/ADC cho fit và inference, giữ khóa fit rồi mới đưa các payload chưa thấy vào chấm.',
 'Activation/ternary và 3 điểm calibration → fit, mã ADC, các tổng projection và báo cáo MHA.')
context('native-runall-render-macros native-runall-render-top','F6, F8–F9',
 'Khai báo cách đọc GDS, chọn đúng top cell và render macro/top bằng KLayout.',
 'Ảnh phải xuất phát từ view thật để đối chiếu hierarchy, vị trí block và routing với mô tả mạch.',
 'GDS + tên top → PNG/SVG hoặc ảnh output của chính artifact đó.')
context('validate-evidence','F7 / trước chấm điểm',
 'Tạo oracle tổng nguyên, đọc state RTL, kiểm record và kiểm tập calibration/holdout không trùng payload.',
 'Bảng kết quả chỉ đáng dùng nếu input, mã ADC và trạng thái hoàn thành được đối chiếu độc lập.',
 'Case JSON, log SAR và ngspice → tập record hợp lệ hoặc lỗi bị reject trước khi fit/score.')
context('calibration-holdout','F7',
 'Fit hệ số từ ba điểm calibration rồi decode holdout bằng hệ số đã khóa.',
 'Cần chuyển từ mã ADC về đại lượng tổng nguyên mà không thay ngưỡng theo đáp án của holdout.',
 'Calibration codes và oracle → frozen fit; holdout codes → decoded sums/residuals.')
context('native-runall-adc-waveform native-runall-mha-plots','F7',
 'Vẽ các đường điện áp/điều khiển hoặc tensor ứng dụng từ record vừa đo.',
 'Figure nối kết số đo với thứ tự SAR và với kết quả MHA để người đọc kiểm được nguồn của kết luận.',
 'Conversion/MHA report của lượt mới → waveform/tensor plots và figure lưu theo lượt.')
context('mha-recompute','F7',
 'Tái dựng Q/K/V/O từ mapping các record và tính attention/softmax độc lập.',
 'Khớp mã ADC chưa tự chứng minh phép ghép ứng dụng đúng; cần kiểm trục tensor và cả reference lượng tử lẫn floating.',
 'Measured projection records + X/weights → MHA output và hai relative L2.')
context('rtl-testbench rtl-native','F7',
 'Tạo testbench và runner Icarus cho các case SAR, thu transcript thực thi.',
 'Kiểm lại RTL từ input và state đã ghi giúp phát hiện sai mapping chân hoặc mã ở giao diện ADC.',
 'Stimulus/expected code và SAR RTL → executable vvp, tool log và đối chiếu từng case.')
context('native-story-routing_progress','F8',
 'Đọc và trình bày tiến trình implementation của top đang dựng.',
 'Cần nối kết đường source RTL/macro với kết quả routing được đưa sang streamout.',
 'Run/config/receipt hiện tại → thông tin route và nguồn artifact của lượt này.')
context('physical-reports','F9',
 'Đọc chính xác setup/hold slack từ vùng marker của STA và tổng hợp LVS/PG/geometry/DRC.',
 'Một log có nhiều số tương tự nhau; chỉ đúng phép đo và đúng scope mới hỗ trợ kết luận về top.',
 'Báo cáo top mới → bảng trạng thái và ảnh; giữ riêng router DRC với full-layout DRC.')
context('native-restored-server-flow-provenance native-restored-server-flow-mha native-restored-server-flow-execute','F0 → F9 / recipe tham chiếu',
 'Định nghĩa quản lý phiên, numerical receipts hoặc đọc kết quả CLI cho recipe server được giữ lại.',
 'Giữ được cách tái lập và kiểm đầu vào của tuyến cũ giúp hiểu nguồn gốc các quyết định thiết kế.',
 'Settings và report phiên → provenance/summary. Khối RUN_LEGACY_CAMPAIGNS quyết định có chạy recipe này hay chỉ giữ định nghĩa.')
context('native-story-dependencies native-story-final_results','F9',
 'Liên hệ các bước thực thi mới và tóm tắt kết quả conversion/MHA/physical cuối.',
 'Kết luận cần lần ngược được tới phép đo và artifact đã tạo, thay vì chỉ có một ảnh GDS.',
 'Flow receipts/outputs → bảng kết quả cuối và sổ các bước native của lượt chạy.')

LESSON_CONTEXT = {
 'format':('F1','Dựng decoder E2M1/E8M0, bộ lượng tử block32 và bảng mã 16 phần tử.','Chốt đúng scale và ACT_X2 trước khi phát PWM.','Bit code/32 số hữu hạn → số đã decode, ví dụ tie và assertion scale.'),
 'ternary':('F1 → F2','Tạo mã WPOS/WNEG và hàm xác định bốn nhánh dẫn điện.','Bảng dấu phải đúng cho cả trọng số zero và activation âm.','Ternary/ACT_X2 → nhánh dẫn và 45 phép đối chiếu tích nguyên.'),
 'leaf':('F2','Sinh SPICE leaf 8T và parser subcircuit để so topology nguồn.','Mô tả mạch phải khớp từng đầu cực với schematic đang tích hợp.','Bảng bốn nhánh → tám transistor, file SPICE và assertion kết nối.'),
 'schematic':('F2','Vẽ đường điện, gate, node trung gian và rail của leaf bằng Matplotlib.','Người đọc cần thấy hai MOS nối tiếp thực hiện dấu phép nhân như thế nào.','Cùng bảng topology đã sinh SPICE → sơ đồ và SVG/PNG của leaf.'),
 'column':('F3','Sinh một cột từ bốn instance leaf dùng chung bitline.','Cộng trong CIM đến từ chia sẻ node vật lý, không phải một toán tử cộng được đặt vào leaf.','Leaf interface → cột4×1/32 NMOS và đối chiếu source.'),
 'array':('F3','Sinh core4×4, đánh số trọng số theo hàng/cột và vẽ sơ đồ mảng.','Giữ đúng sharing theo hàng và cột khi tăng cấp hierarchy.','Cột4×1 → core16 leaf/128 NMOS, 50 chân và file hierarchy.'),
 'analog':('F4','Đọc schematic và đếm đệ quy MOS/MIM trong core/acquisition/conditioner.','Cần biết ngoại vi nào biến dòng trên bitline thành điện áp giữ được cho ADC.','Subcircuit nguồn → bảng linh kiện, tụ hold/tải và dây ghép macro.'),
 'leaf-spice':('F5','Tạo và chạy ngspice DC9 case với leaf thật cùng nguồn bias bitline.','Kiểm dấu và zero ở transistor trước khi giải thích kết quả nhiều hàng.','Leaf + PDK TT → transcript ngspice, 9 dòng vi sai, assertion và biểu đồ dấu.'),
 'tiling':('F1, F3 → F7','Chia block32 thành tám lát4 hàng, cộng partials và khôi phục scale.','Tránh nhầm block kích thước số với kích thước core vật lý hoặc quên một hệ số2.','ACT_X232×T32×4 và scale/alpha → cùng kết quả với reference đã decode.'),
}
from scripts.cim_paper_lesson import SCHEMATIC_CODE, DEVICE_MARKDOWN, DEVICE_CODE
_paper_lessons=[]
for _key,_markdown,_code in LESSONS:
    _paper_lessons.append((_key,_markdown,SCHEMATIC_CODE if _key=='schematic' else _code))
    if _key=='schematic':_paper_lessons.append(('device',DEVICE_MARKDOWN,DEVICE_CODE))
LESSONS=_paper_lessons
LESSON_CONTEXT['device']=('F2','Vẽ phóng to NMOS bốn cực, mặt bằng lớp và mặt cắt khái niệm.',
    'Nối ký hiệu điện với hình dáng thiết bị, cách gate điều khiển kênh và contact nối các cực.',
    'Cực D/G/S/B và W/L nguồn → hình vector thiết bị; giữ riêng với GDS thực tế.')
for key,value in LESSON_CONTEXT.items():CONTEXT['cim-edu-'+key]=value
CONTEXT['cim-edu-bootstrap']=('F0','Đăng ký magic cim_lesson và namespace dành riêng cho bài học cell→macro.',
    'Các hàm minh họa không được đổi tên biến, fit hoặc trạng thái của native implementation.',
    'Bundle/OUT đã thiết lập → môi trường bài học và thư mục cell_to_macro trong lượt chạy.')

def definitions(source):
    cleaned='\n'.join('# IPython magic' if line.lstrip().startswith(('%','!')) else line
                       for line in source.splitlines())
    tree=ast.parse(cleaned)
    return [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]

def guide(cell,state=None):
    from scripts.cim_function_reference import function_records,function_task,data_contract,glossary_for
    records=function_records(cell.source)
    nodes=[node for _,node in records]
    # Code in a generated Python script is still explained at its containing cell.
    embedded=not nodes and bool(re.search(r'^\s*(?:async\s+)?def\s+',cell.source,re.M))
    if not nodes and not embedded:return None
    if cell.id not in CONTEXT:
        raise KeyError('Cần thuyết minh cụ thể cho cell: '+cell.id)
    stage,operation,reason,_old_io=CONTEXT[cell.id]
    received,produced,next_step=data_contract(cell.id)
    if state is None:state={}
    for group in ('introductions','functions','contracts','terms'):state.setdefault(group,{})
    anchor='guide-'+cell.id
    intro=f'{operation} {reason}'
    text=f'''<a id="{anchor}"></a>

### Trước cell `{cell.id}` — {stage}

'''
    if intro in state['introductions']:
        prior=state['introductions'][intro]
        text+=f'**Thực hiện:** Cùng nhóm thao tác đã giải thích ở [cell `{prior}`](#guide-{prior}).\n'
    else:
        state['introductions'][intro]=cell.id
        text+=f'**Thực hiện:** {intro}\n'
    # Use the complete text to find terminology, including the shared tasks
    # whose explanations will be replaced with links in the rendered guide.
    complete=intro+'\n'+received+'\n'+produced+'\n'+next_step
    function_refs={};function_anchors=[]
    text+='''

**Nhiệm vụ từng hàm:**

| Hàm và tham số | Nhiệm vụ, kết quả và tác động |
|---|---|
'''
    for fullname,node in records:
        signature=fullname+'('+ast.unparse(node.args)+')'
        signature=signature.replace('|','\\|').replace('\n',' ')
        description=function_task(cell.id,fullname,node)
        complete+='\n'+description
        if description in state['functions']:
            prior_name,prior_anchor=state['functions'][description]
            function_refs[fullname]=prior_anchor
            description=f'Cùng tác vụ với [`{prior_name}`](#{prior_anchor}).'
            left='`'+signature+'`'
        else:
            fn_anchor='fn-'+cell.id+'-'+fullname.replace('.','-')
            state['functions'][description]=(fullname,fn_anchor)
            function_anchors.append(fn_anchor)
            left='<a id="'+fn_anchor+'"></a>`'+signature+'`'
        text+='| '+left+' | '+description.replace('|','\\|')+' |\n'
    contract=(received,produced,next_step)
    contract_ref=None
    if contract in state['contracts']:
        contract_ref=state['contracts'][contract]
        text+=f'\n**Dữ liệu và bước sử dụng tiếp:** Dùng [hợp đồng đã mô tả ở cell `{contract_ref}`](#data-{contract_ref}).\n'
    else:
        state['contracts'][contract]=cell.id
        text+=f'''
<a id="data-{cell.id}"></a>

**Dữ liệu vào, kết quả và bước sử dụng tiếp:**

- **Nhận từ đâu, cấu trúc/đơn vị gì:** {received}
- **Trả về hoặc ghi ra đâu:** {produced}
- **Chuyển cho bước nào:** {next_step}
'''
    terms=glossary_for(cell.source+'\n'+complete)
    new_terms=[];term_refs={}
    for term,description in terms:
        if term in state['terms']:
            term_refs[term]=state['terms'][term]
        else:
            term_anchor='term-'+str(len(state['terms'])+1)
            state['terms'][term]=term_anchor
            new_terms.append((term,description,term_anchor))
    if new_terms:
        text+='\n**Chú giải bổ sung tại lần xuất hiện đầu:**\n\n| Tên | Nghĩa và vai trò ở đây |\n|---|---|\n'
        for term,description,term_anchor in new_terms:
            text+='| <a id="'+term_anchor+'"></a>`'+term+'` | '+description.replace('|','\\|')+' |\n'
    return nbf.v4.new_markdown_cell(text,id='explain-'+cell.id,
        metadata={'automx_explains':cell.id,'cim_education_revision':REVISION,
                  'documented_functions':[name for name,_ in records],
                  'function_anchors':function_anchors,'function_references':function_refs,
                  'data_contract_reference':contract_ref,
                  'used_glossary':[term for term,_ in terms],
                  'glossary_references':term_refs,
                  'local_glossary':[term for term,_,_ in new_terms]})

def deduplicate_old_notes(cells):
    """Keep equations, unique context and every cell ID; remove repeated prose."""
    seen=set()
    for i,cell in enumerate(cells):
        if cell.cell_type!='markdown':continue
        upcoming=next((c for c in cells[i+1:] if c.cell_type=='code'),None)
        covered=upcoming is not None and bool(definitions(upcoming.source))
        kept=[];removed=0
        for paragraph in re.split(r'\n\s*\n',cell.source):
            key=' '.join(paragraph.split())
            # An expanded function prelude replaces the old one-line caption.
            if covered and paragraph.lstrip().startswith('**Cell guide'):
                removed+=1;continue
            plain=(len(key)>70 and not any(x in paragraph for x in ('$$','```','<a ','|')))
            if plain and key in seen:removed+=1;continue
            if plain:seen.add(key)
            kept.append(paragraph)
        if removed:
            cell.source='\n\n'.join(kept).strip()
            cell.metadata['cim_duplicate_note_removed']=True
    return cells

PROJECT_TITLE = 'AutoMX-CIM: An MXFP4–Ternary Mixed-Signal Compute-in-Memory Core for Attention Projections'
PROJECT_AUTHORS = (
    ('Minh D. Nguyen', 'Lead'),
    ('Tien Thinh Nguyen', 'Member'),
    ('Dang Vinh Pham', 'Member'),
    ('Anh Tu Phung', 'Member'),
)
PROJECT_AFFILIATION = 'Hanoi University of Science and Technology'

def present_project(book):
    """Apply the laboratory title/author layout without changing executable cells."""
    header = f'''# {PROJECT_TITLE}

---

**Code-a-Chip · ISSCC 2027**

```text
Copyright 2026 EDABK Laboratory
SPDX-License-Identifier: Apache-2.0
```
'''
    authors = '''| Name | Affiliation | Email | IEEE Member | SSCS Member |
|:--|:--|:--|:--:|:--:|
'''
    for name, role in PROJECT_AUTHORS:
        display = name + (' (Lead)' if role == 'Lead' else '')
        authors += f'| {display} | {PROJECT_AFFILIATION} |  | No | No |\n'
    # Replace the old distribution preface; retain its ID for existing references.
    intro = next(c for c in book.cells if c.id == 'standalone-introduction')
    intro.source = header
    book.cells = [c for c in book.cells if c.id != 'project-authors']
    book.cells.insert(book.cells.index(intro) + 1,
                      nbf.v4.new_markdown_cell(authors, id='project-authors'))
    title = next(c for c in book.cells if c.id == 'title')
    lines = title.source.splitlines()
    if lines and lines[0].startswith('# '):
        lines[0] = '## Abstract'
    title.source = '\n'.join(lines)
    title.source = title.source.replace(
        '**A reproducible SKY130 mixed-signal design investigation · Code-a-Chip ISSCC 2027**\n\n', '')
    title.source = title.source.replace(
        'Team and contact are supplied in [`TEAM.json`](TEAM.json). ', '')
    roadmap = next(c for c in book.cells if c.id == 'argument-roadmap')
    marker = '    **Restart Kernel & Run All** from this folder.'
    if marker in roadmap.source:
        roadmap.source = roadmap.source.split(marker, 1)[0].rstrip() + '''

**Local execution:** select the **env_mamba** kernel, then **Restart Kernel & Run All**.
Each execution writes new measurements, logs, figures and physical views under
`runs/fresh_*`. The complete tool implementations remain visible in the cells.
'''
    for cell in book.cells:
        if cell.cell_type != 'markdown':
            continue
        # Distribution labels are prose only. Preserve actual function/file names,
        # HTML anchors and link targets so the documented implementation stays exact.
        cell.source = cell.source.replace('tuyến standalone active', 'tuyến thực thi hiện tại')
        cell.source = cell.source.replace('standalone active lấy', 'luồng hiện tại lấy')
        cell.source = re.sub(r'(?<![\w.-])standalone(?![\w.-])',
                             'của notebook', cell.source, flags=re.I)
    book.metadata['project'] = {
        'title': PROJECT_TITLE, 'copyright': 'Copyright 2026 EDABK Laboratory',
        'authors': [dict(name=name, role=role, affiliation=PROJECT_AFFILIATION,
                         email='', ieee_member='No', sscs_member='No')
                    for name, role in PROJECT_AUTHORS],
    }
    return book

def enrich(book):
    book=copy.deepcopy(book)
    from scripts.cim_measurement_extension import patch_sources,insert_extensions
    book=patch_sources(book)
    from scripts.cim_output_presentation import patch as patch_output
    book=patch_output(book)
    # Idempotent enrichment: preserve all source cells/outputs, replace our additions.
    prior_validation=book.metadata.get('cim_cell_to_macro',{}).get('validation')
    prior_outputs={c.id:(c.source,c.get('outputs',[]),c.get('execution_count'),copy.deepcopy(c.metadata)) for c in book.cells
                   if c.cell_type=='code' and c.id.startswith('cim-edu-')}
    base=[c for c in book.cells if not c.id.startswith(('cim-edu-','explain-'))]
    base=deduplicate_old_notes(base)
    by_id={c.id:c for c in base}
    if 'standalone-prepare' not in by_id:raise ValueError('Bản này cần notebook standalone đã port')
    # Correct the one old textual formula; implementation is preserved verbatim.
    for c in base:
        if c.cell_type=='markdown':
            c.source=c.source.replace('2^(E8M0-128) * ACT_X2[k] / 2','2^(E8M0-128) * ACT_X2[k]')
    first_code=next(i for i,c in enumerate(base) if c.cell_type=='code')
    base.insert(first_code,nbf.v4.new_markdown_cell(ROADMAP,id='cim-edu-roadmap'))
    lesson_cells=[nbf.v4.new_code_cell(BOOT,id='cim-edu-bootstrap')]
    for key,markdown,code in LESSONS:
        # Raw authoring fragments use doubled backslashes; notebook Python and
        # MathJax need one escape character in the resulting cell source.
        markdown=markdown.replace(chr(92)*2,chr(92))
        code=code.replace(chr(92)*2,chr(92))
        lesson_cells += [nbf.v4.new_markdown_cell(markdown,id='cim-edu-'+key+'-theory'),
                         nbf.v4.new_code_cell('%%cim_lesson '+key+'\n'+code,id='cim-edu-'+key)]
    lesson_cells.append(nbf.v4.new_markdown_cell(BRIDGE,id='cim-edu-bridge'))
    index=base.index(by_id['standalone-prepare'])+1
    base[index:index]=lesson_cells
    result=[];note_state={}
    for cell in base:
        if cell.cell_type=='code':
            pre=guide(cell,note_state)
            if pre is not None:result.append(pre)
            if cell.id in prior_outputs and cell.source==prior_outputs[cell.id][0]:
                _,cell.outputs,cell.execution_count,cell.metadata=prior_outputs[cell.id]
        result.append(cell)
    book.cells=result
    book.metadata['cim_cell_to_macro']={'revision':REVISION,'lesson_code_cells':len(LESSONS)+1,
        'original_code_changed':True,'function_guides':sum(c.id.startswith('explain-') for c in result),
        'native_updates':'Current/energy probes, native PEX runner and deterministic GDS rendering; original cell IDs retained.',
        'format_reference':OCP,'source_netlist':'inputs/core_acquisition.spice',
        'notes_deduplicated':True,
        'unique_term_definitions':len(note_state['terms']),
        'unique_function_explanations':len(note_state['functions']),
        'unique_data_contracts':len(note_state['contracts']),
        'validation':'New lesson cells require execution; earlier native outputs retain their original run identity.'}
    current_lessons=[c for c in result if c.cell_type=='code' and c.id.startswith('cim-edu-')]
    if (isinstance(prior_validation,dict) and prior_validation.get('status')=='PASSED'
        and all(c.id in prior_outputs and c.source==prior_outputs[c.id][0] for c in current_lessons)):
        book.metadata['cim_cell_to_macro']['validation']=prior_validation
    book=insert_extensions(book)
    book=present_project(book)
    from scripts.cim_output_presentation import decorate
    book=decorate(book)
    nbf.validate(book)
    return book

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('notebook',nargs='?',default=str(Path(__file__).resolve().parents[1]/'AutoMX_CIM_Code_a_Chip.ipynb'))
    args=parser.parse_args();p=Path(args.notebook)
    original=nbf.read(p,4);updated=enrich(original);nbf.write(updated,p)
    print(json.dumps({'notebook':str(p),'cells':len(updated.cells),
        'code_cells':sum(c.cell_type=='code' for c in updated.cells),
        **updated.metadata['cim_cell_to_macro']},indent=2))
