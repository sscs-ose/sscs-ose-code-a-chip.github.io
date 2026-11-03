"""Authoring-only presentation of archived notebook cells; originals stay archived."""
LEGACY={
'archive-000': '# AutoMX-CIM — từ reference số đến phép đo PEX và top mixed-signal\n\nFlow theo kết quả: reference MHA → mạch ternary → layout/PEX → chẩn đoán sai số → chọn tải/PWM → decoder → đọc 2+2 → RTL → analog/SAR/MHA và GDS. Các bảng đo bổ sung phía dưới đọc trực tiếp JSON/log đã chạy.',
'archive-004': '## 1. Mục tiêu\n\nThực hiện projection ternary gần bộ nhớ, kiểm bằng reference MHA và dùng phép đo transistor/PEX để chọn cấu hình đọc.',
'archive-006': '## 3. Chuỗi triển khai\n\nReference và vector cố định cung cấp oracle cho controller. Mạch sinh tự động cung cấp layout/PEX; phép đo PEX cung cấp transfer, ngưỡng và mẫu kiểm decoder. Các sai số đo được định hướng lần sửa kế tiếp.',
'archive-007': '### 3.1 Cấu hình demonstrator\n\nReference cũ dùng T=4, hai head và lịch tile logic 32×8 trên core 4×4. Nhánh analog/SAR ở phần B đo riêng testcase 2 token × 4 chiều, hai head.',
'archive-010': '### 3.2 Môi trường thực thi\n\nĐọc receipt môi trường và phiên bản tool đã dùng; phần B kiểm lại môi trường env_mamba và tool native.',
'archive-022': '## 4. Thiết kế và đo kiểm mạch SKY130\n\n### 4.1 Giao diện mạch\n\nPin, trọng số P/N và view layout/PEX thống nhất để cùng stimulus được dùng từ schematic đến phép đo sau layout.',
'archive-023': '**Quan hệ trọng số:** $w_{r,c}=W^+_{r,c}-W^-_{r,c}\\in\\{-1,0,+1\\}$.',
'archive-028': '### 4.3 Layout và trích xuất\n\nReceipt Stage 5 liên kết GDS/LEF, kết quả LVS và netlist PEX. PEX này là đầu vào của chiến dịch 101 case và các phép đo transfer sau đó.',
'archive-031': '### 4.4 Mô hình transfer\n\nFit gain/offset từ các mẫu vật lý và so với reference số; bước kế tiếp mở rộng coverage lên 101 case để tìm các vùng đảo mức.',
'archive-034': '### 4.5 Coverage PEX: 101 case\n\n85 case code/activity và 16 pattern MHA cung cấp tập quan sát ban đầu. Độ lệch zero, swing và thời điểm lấy mẫu được đọc từ receipt; các cặp đảo mức được kiểm sâu ở 4.6.',
'archive-037': '### 4.6 Lỗi transfer: các mức tổng bị đảo thứ tự\n\nPhép đo ngspice schematic/PEX xác định các cặp signed-sum bị chồng lấn. Cell bổ sung bên dưới in case, sum và điện áp thực của từng cặp.',
'archive-040': '### 4.7 Sweep tải và PWM\n\nThay đổi điện dung tải và độ rộng PWM để giảm swing và phục hồi thứ tự điện áp trên các cặp khó đã phát hiện.',
'archive-043': '### 4.8 Kiểm lại candidate bằng PEX\n\nĐo các candidate 400 fF / 75 ps và 800 fF / 50 ps với parasitic đã trích xuất; kết quả làm đầu vào cho lần chạy full 101 case.',
'archive-046': '### 4.9 Candidate được chọn: 800 fF / 50 ps\n\n101/101 native PEX jobs hoàn tất. Bảng bổ sung hiển thị số mức, khoảng cách nhỏ nhất và overlap theo từng cột tại 1.9 ns.',
'archive-049': '### 4.10 Holdout MHA độc lập\n\n16 pattern mới được đo sau khi chọn candidate; report kết hợp 117 case giữ các mức theo thứ tự trong tập đã đo. Dữ liệu holdout này được dùng tiếp để kiểm decoder.',
'archive-052': '### 4.11 Các mốc đã thực hiện\n\nNhật ký phiên cũ được giữ làm nguồn tra cứu; flow tiếp tục ngay bằng các phép kiểm decoder và đo 2+2 bên dưới.',
'archive-053': '**Kế tiếp:** dùng điện áp holdout đã đo để đối chiếu sum kỳ vọng với sum decoder trả về.',
'archive-055': '### 4.12 Lỗi giải mã: 52 / 128 mẫu\n\nNgưỡng midpoint được fit bằng 101 case training rồi áp dụng cho 16 pattern holdout × 4 cột × 2 thời điểm. Cell bổ sung trích những dòng expected/predicted sai từ report thực.',
'archive-058': '### 4.12a Calibration mở rộng: 87 case\n\nBổ sung các signed-sum còn thiếu. Minimum differential gap đo được là −4.4212 mV, giúp xác định cần thay đổi cách đọc thay vì chỉ bổ sung ngưỡng.',
'archive-061': '### 4.12b Tách dữ liệu calibration và holdout\n\nGiữ tập rank MHA mới để dùng sau khi chọn cách đọc và khóa ngưỡng.',
'archive-062': '**Quan hệ dữ liệu:** fit trên calibration, đánh giá trên pattern holdout riêng.',
'archive-064': '### 4.12c So sánh feature giải mã\n\nDữ liệu differential và common-mode đã đo được dùng để chọn thử nghiệm đọc tách hàng 2+2.',
'archive-067': '### 4.12d Can thiệp: hai lần đọc, mỗi lần hai hàng\n\nĐọc các hàng [0,1] và [2,3] với precharge riêng. 32/32 targeted PEX jobs cung cấp hai transfer có thứ tự trong tập chọn.',
'archive-070': '### 4.12e Calibration 2+2: 78 / 78 jobs\n\n39 mức partial-sum cho mỗi phase được đo và dùng để khóa ngưỡng. Minimum gap: phase A 8.6143 mV, phase B 8.9214 mV.',
'archive-073': '### 4.12f Kết quả decoder 2+2: 0 / 256 lỗi\n\n32 pattern MHA mới × 4 cột × 2 thời điểm cho 256 kết quả tổng. Đây là phép đánh giá trên tập mới sau khi khóa ngưỡng 2+2; bảng bên dưới đối chiếu riêng denominator của hai chiến dịch.',
'archive-076': '### 4.13 Dữ liệu chuẩn bị corner\n\nGiữ nguồn deck và cấu hình corner của phiên cũ để tái lập phép đo.',
'archive-077': '**Nguồn thực nghiệm:** receipt bên dưới lưu cấu hình và deck đã chuẩn bị.',
'archive-079': '### 4.14 Kiểm khi có tải lấy mẫu\n\nCandidate tổng tải 820 fF gồm 800 fF bitline và 20 fF nút lấy mẫu. 174/174 jobs hoàn tất; số lỗi giải mã tổng holdout bằng 0, minimum training gap 6.57023 mV.',
'archive-081': '### 4.15 Sample/hold và timing cạnh\n\nĐọc các chiến dịch switch-level và aperture đã chạy. Các receipt liên kết phép đo drift và thời điểm lấy mẫu với deck/log tương ứng.',
'archive-089': '### 5.1b Kiểm giao thức hai lượt đọc\n\nKết quả PEX 2+2 dẫn tới regression controller hai phase: đọc riêng, giải mã partial sum rồi cộng số. Regression RTL kiểm số transaction, reset và kết quả theo oracle.',
'archive-092': '### 5.1e Ghép mạch và controller\n\nTop cũ ghép core Stage 5 với controller hai phase đã tổng hợp, cung cấp nền cho tích hợp vật lý tiếp theo.',
'archive-094': '### 5.1f Triển khai OpenLane và render GDS\n\nRecipe OpenLane gốc được giữ trong cell. Mặc định Run All đọc receipt và log phiên đã chạy; phần B xuất và render lại top từ checkpoint route đã kiểm hash.',
'archive-097': '### 5.1g Đọc kết quả triển khai\n\nĐối chiếu tag, đường dẫn report, metric và GDS hash của phiên triển khai tương ứng.',
'archive-099': '### 5.2 Dấu vết tích hợp wrapper\n\nGiữ receipt của mốc wrapper để truy nguồn quá trình phát triển. Các kết quả đo cụ thể tiếp tục ở phần B.',
'archive-100': '**Đầu ra tích hợp:** GDS, LEF, netlist, timing và các report tool liên kết bằng hash.',
'archive-102': '## 6. Kết quả triển khai cũ\n\nĐọc receipt theo tag để liên kết phép đo với artifact triển khai. Phần B bổ sung analog/SAR/MHA đầu cuối, synthesis, streamout, LVS và timing.',
'archive-103': '**Đối chiếu kết quả:** đọc số liệu và SHA từ report gốc của từng lần chạy.',
'archive-105': '## 7. Từ kết quả cũ đến flow hiện tại\n\nCác phép đo PEX, decoder, 2+2 và RTL ở trên làm tiền đề thực nghiệm. Phần B tiếp tục với SAR RTL ghép transistor, hiệu chuẩn riêng, projection MHA, synthesis và xuất top. Cuối flow có bảng dependency kiểm SHA và receipt tổng hợp.',
}
MODERN={
'8d4a68af': '## 5. Hiệu chuẩn trước holdout\n\nBa conversion native có tổng integer [0, −8, +8]; đo mã ADC, fit slope/offset và khóa hệ số trước Q/K/V/O. Calibration và holdout dùng pattern riêng.',
'7f88b3dd': '## 8. OpenROAD + KLayout: dựng top core mixed-signal\n\nXuất DEF/LEF từ ODB hậu ECO đã kiểm hash; merge GDS bằng KLayout native. Đối chiếu geometry, transform và hierarchy toàn bộ với GDS nguồn. Output cell giữ trạng thái và log của từng lượt kiểm KLayout; số routing violation được đọc riêng từ report OpenROAD ở bảng ECO.',
'fc80dbb4': '## 4. SAR RTL ghép analog transistor\n\nPWM E2M1 → CIM/acquisition → conditioner → transistor sampling → CDAC/comparator → SAR RTL gốc chạy Icarus → feedback → EOC và word. Shared-ngspice nối hai simulator theo từng phase. CDAC gộp 515 tụ signal tuyến tính mỗi phía, 1.4848 pF/phía, theo bảo toàn điện tích; clock phase và bottom driver do harness điều khiển. Kiểm word trên electrical bridge trùng RTL và ổn định 40 ns sau EOC.',
'c49e894a': '## 6. Tiny-MHA đầu cuối\n\nTestcase **2 token × 4 chiều, 2 head**, Q/K/V/O ternary; một cột 4 hàng được time-multiplex, attention/softmax chạy CPU. Mỗi pattern có waveform ngspice, trace RTL, EOC và receipt. So sánh với cả reference context lượng tử và reference floating, hiển thị hai sai số riêng.',
'769a8093': '## 7. Yosys: tổng hợp digital wrapper và SAR\n\nĐọc RTL wrapper, sequencer và SAR gốc; chạy hierarchy check, synthesis, map flop/ABC theo Liberty SKY130, check assertion và xuất mapped Verilog. Output cell giữ log native Yosys.',
'b48e59fe': '## 9. Netgen: LVS tín hiệu\n\nSPICE extract từ GDS nguồn được đối chiếu bằng Netgen. Trước khi tái sử dụng extraction, toàn bộ geometry và instance của GDS hiện tại phải trùng nguồn. Kết quả kiểm: unique signal match.',
'e803cdc7': '## 10. Nguồn, RC và timing digital\n\nKiểm liên thông VPWR/VGND trên ODB; OpenRCX trích RC và OpenSTA đo timing TT 1.8 V, 25°C, clock 40 ns / 25 MHz. Đọc lại digital LIB và giữ output/log native của từng tool.',
'3bed6f56': '## 11. Kết quả cuối\n\nManifest liên kết GDS/DEF/LEF, SPEF/SDC/LIB, mapped netlist, waveform ADC, kết quả MHA và receipt lịch sử bằng SHA256. Bảng dependency chỉ ra đường đi từ phép đo cũ tới đầu vào và artifact cuối.',
}

def legacy_prose(cid,source):
    if cid in LEGACY:return LEGACY[cid]
    if cid.startswith('server-flow-'):
        titles={'intro':'Phiên server trước','modes':'Cách tái lập phiên server','config-guide':'Cấu hình phiên server','provenance-guide':'Đối chiếu nguồn','mha-guide':'Reference và lịch thực thi','blocks-guide':'Các receipt mạch và RTL','execute-guide':'Recipe triển khai server','review-guide':'Report theo tag','render-guide':'Render GDS đã đối chiếu','postroute-guide':'Phép đo sau route','close-guide':'Artifact và manifest phiên server','appendix':'Nguồn notebook lịch sử'}
        key=cid.removeprefix('server-flow-')
        return '### '+titles.get(key,key)+'\n\nRecipe và receipt của phiên này được giữ để truy nguồn. Chuỗi kết quả đang dùng được trình bày ở phần A/B và bảng dependency cuối notebook.'
    source=source.removeprefix('Historical narrative (superseded):\n\n')
    if source.startswith('**Cell guide'):
        return source.split('\n\n**Readout:**')[0].replace('acceptance rule','measurement relation')
    return source
