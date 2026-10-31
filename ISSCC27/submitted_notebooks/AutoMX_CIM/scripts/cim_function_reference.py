"""Vietnamese function reference for the actual inline notebook implementation.

Descriptions are keyed by function/method identity, not generated from a name
translation. Missing entries fail authoring so newly added helpers get reviewed.
"""
import ast
import re

TASKS={}
def task(names,text):
    for name in names.split():TASKS[name]=text

task('design_review','Nhận nhãn và toàn bộ mã của cell magic, biên dịch rồi thực thi trong vùng biến riêng của phần phân tích; ghi lại source dùng để kiểm kết quả mà không ghi đè biến của tuyến EDA.')
task('standalone_runtime','Tạo module automx_standalone từ nguyên nội dung cell, đưa module vào bộ nhớ Python và công bố biến portable; các cell chạy tool sau đó gọi đúng các hàm vừa khai báo này.')
task('cim_lesson','Biên dịch và chạy mã bài học trong module riêng automx_cim_cell_lesson; các tên EDU_* và helper minh họa không thay calibration hay trạng thái native flow.')
task('native_lab','Nhận mã của một cell phòng thí nghiệm, đăng ký mã định danh vào sổ thứ tự rồi chạy native hoặc trình bày output tham chiếu tùy chế độ; chuyển tiếp stdout về output notebook.')
task('flush_stream','Rút phần chữ còn đệm trong luồng output, giải mã và hiển thị ngay để log tool không bị giữ đến cuối cell.')
task('inline_module','Tách phần định nghĩa khỏi đoạn NOTEBOOK_RUN, tạo module Python riêng, chạy phần định nghĩa trong module rồi mới thực hiện đoạn gọi hàm ở namespace notebook.')
task('eda_source','Ghi nguyên nội dung script tool đang hiển thị trong cell ra thư mục source của lượt chạy; các lệnh Magic/KLayout/OpenROAD sử dụng file đó thay vì một script bị giấu ngoài notebook.')
task('save _write','Tạo thư mục cha khi cần và ghi đối tượng dữ liệu thành JSON; nơi có file tạm thì thay file đích sau khi ghi xong để tránh để lại JSON ghi dở.')
task('container container_command','Dựng danh sách đối số docker run với executable, thư mục làm việc, image và mount của bundle; trả lệnh cho runner, chưa khởi động process ở bước này.')
task('guard_old_checkout','Đăng ký audit hook cho thao tác mở file của Python, chặn các đường dẫn checkout/PDK cũ trong manifest; trả tập tiền tố bị chặn để ghi nhận điều kiện chạy độc lập.')
task('audit','Callback của audit hook: kiểm sự kiện open và đường dẫn đang được mở, ném PermissionError nếu file thuộc một tiền tố thiết kế cũ bị cấm.')
task('relocate_bundle','So root hiện tại với assembled_root trong standalone.json, đổi tiền tố các cấu hình PDK đã ghi nhận khi thư mục được chuyển ổ, rồi ghi lại đường dẫn model SPICE tại root mới.')
task('prepare_pnr','Tạo thư mục cold_pnr/design mới, điền RTL/LEF/GDS của ba macro vào config và sinh script PDN cùng bridge ground M4/M5; trả design directory và config cho OpenLane.')
task('start','Kiểm image Docker và tool host, nạp image từ archive nếu cần, gọi prepare_pnr rồi khởi động OpenLane nền; lưu PID, lệnh và log để analog có thể chạy song song với place-and-route.')
task('cleanup','Khi kernel kết thúc, kiểm process cold PnR còn chạy hay không; nếu còn thì dừng đúng container của lượt này để không bỏ lại job nền.')
task('inputs','Lấy các đường dẫn ODB, GDS, design directory, run directory, config và PDK của cold PnR đang được quản lý; không tự đọc một checkpoint top cũ thay thế.')
task('wait_pnr','Đọc nối tiếp log OpenLane đang chạy, in tiến độ, áp dụng timeout, kiểm return code và sự tồn tại của routed ODB/GDS/netlist; ghi receipt rồi mới cho streamout tiếp tục.')
task('synthesize','Chờ cold flow do start đã khởi động và nhận các view synthesis/routing thật qua wait_pnr; không thực hiện một lượt tổng hợp giả chỉ để in thống kê.')
task('synthesize_sar','Tạo script Yosys đọc SAR RTL và Liberty SKY130, tổng hợp/ánh xạ standard cell rồi xuất adc_core_digital.mapped.v; lưu log và khai báo mapped_sar trong outputs.')
task('streamout','Đọc routed ODB bằng OpenROAD để xuất DEF/abstract LEF, rồi đưa GDS vừa streamout bởi cold flow vào bộ view của lượt này; trả đường dẫn GDS để kiểm và render.')
task('audit_gds','Dùng KLayout so geometry/hierarchy của GDS bàn giao với GDS nguồn cold flow, đếm cell/instance/master; chạy deck DRC trong thời gian giới hạn và ghi rõ clean, có violation hay chưa hoàn tất.')
task('remove_dangling_power_ports','Sau khi bỏ chân PG standard-cell theo scope hai phía, chỉ loại nhãn VPWR_uq*/VGND_uq* thật sự không có endpoint và vẫn có rail chuẩn; gặp nhãn còn nối mạch thì báo lỗi, không xóa tín hiệu bị short.')
task('lvs','Xuất DEF/netlist từ ODB mới, extract bằng Magic, chuẩn hóa chân PG standard-cell đối xứng ở cả hai phía và so bằng Netgen; chỉ nhận verdict cuối Circuits match uniquely rồi đăng ký log signal_lvs.')
task('power','Đọc đúng routed ODB và chạy check_power_grid riêng cho VPWR/VGND bằng Tcl native; kiểm cả marker hoàn tất lẫn lỗi in trong log trước khi ghi báo cáo rail PASS.')
task('timing','Tạo SDC cho clock 40 ns, trích SPEF bằng OpenRCX, chạy setup/hold STA rồi xuất mô hình thời gian Liberty; lưu slack đo được và các view SPEF/LIB/SDC, không tự đổi slack âm thành PASS timing.')
task('parse_library','Cho OpenSTA đọc lại Liberty vừa tạo và yêu cầu marker hoàn tất; kiểm cú pháp/interface của file Liberty trước khi nó được đưa vào manifest.')
task('prepare_shared','Liên kết runtime libngspice đi kèm bundle vào thư mục tool của lượt mới, chạy probe version bằng ctypes và đăng ký file runtime report cho co-simulation.')
task('environment','Chạy các lệnh version của Icarus, vvp, KLayout, Yosys và OpenROAD ở đúng môi trường host/container; lưu log để xác định executable thực tế được dùng.')
task('export_factorial','Đo bổ sung hai điểm tải/PWM còn thiếu, ghép với baseline/candidate đã đo trong lượt này và chuyển đường dẫn deck/log sang evidence của review; khôi phục hai nhãn pilot để biểu đồ trước/sau không bị đổi.')
task('export_conversions','Ghi protocol và fit đã khóa trước khi đo challenge, chạy tám payload challenge, ghép 41 case hiện tại với mapping Q/K/V/O và waveform; ghi evidence.json chỉ trỏ tới record của lượt đang chạy.')
task('export_physical','Nối các report geometry/PG/DRC/STA/LVS mới vào evidence review, sao chép figure của ba macro và top, nén GDS hiện tại cho cell đọc/render độc lập.')
task('publish','Kiểm các artifact bắt buộc đã tồn tại và còn đúng nội dung, tập hợp views/receipts vào runall_manifest.json rồi in vị trí top GDS cuối; ghi rõ top được dựng cold từ RTL.')
task('table edu_table','Ghép headers và các hàng dữ liệu thành bảng Markdown rồi hiển thị trong output cell; chỉ trình bày dữ liệu đã nhận, không tạo thêm phép đo.')
task('record _json read_json','Đọc JSON tại đường dẫn được truyền hoặc đường dẫn tương đối dưới BASE và trả cấu trúc Python cho bước phân tích kế tiếp.')
task('savefig','Căn bố cục figure hiện tại, lưu vào thư mục OUT, hiển thị rồi đóng figure để hình của các bước sau không bị vẽ chồng.')
task('public_values','Duyệt cấu trúc dict/list để giữ các giá trị phục vụ đọc kết quả và lọc trường định danh kỹ thuật khỏi phần in; không thay dữ liệu report nguồn.')
task('pretty','Đổi dữ liệu đã lọc thành biểu diễn JSON dễ đọc với tùy chọn thụt lề rồi in ra output cell.')
task('block','Vẽ một khối chữ nhật bo góc tại tọa độ x/y với chiều rộng, nội dung và màu truyền vào; trả phần hình dùng cho sơ đồ kiến trúc.')
task('arrow','Nối hai vị trí bằng mũi tên và đặt nhãn ở giữa để biểu diễn chiều dữ liệu giữa các khối trong sơ đồ.')
task('file_hash fingerprint digest _digest _hash _sha _file_sha256','Đọc bytes của file và tính dấu kiểm SHA-256 trả về dạng chuỗi hex; các bước gọi dùng giá trị này để phát hiện input/log thay đổi, không phải một số đo điện.')
task('summarize_values','Duyệt report theo độ sâu cho phép để rút các giá trị đo và trạng thái có ý nghĩa thành bản tóm tắt, tránh in toàn bộ cấu trúc lồng nhau.')
task('review_reports','Mở các report theo danh sách đường dẫn, trình bày trạng thái và số đo kèm log khi được yêu cầu; giữ phân biệt dữ liệu thiếu, cũ và có kết quả lỗi.')
task('scan','Hàm con của bộ đọc report: đi qua các dict/list lồng nhau để thu trường trạng thái hoặc measurement cần đưa vào phần trình bày.')
task('plot_saved_transfer','Đọc các khoảng điện áp đã được đo cho từng mức tổng, vẽ bao mức và mẫu để nhìn chồng lấn/đảo thứ tự; không tự sinh một đường fit làm dữ liệu đo.')
task('find','Hàm duyệt/tìm nội bộ: tìm dữ liệu hoặc gốc nhóm trong cấu trúc đang xử lý; tham chiếu tên hàm cha ở bảng để phân biệt tìm trường report với tìm đại diện nhóm node R/C.')
task('linked','Mở report con, đi theo trường input được chỉ định và so dấu kiểm với file cha hiện tại; trả một cạnh phụ thuộc đã xác nhận thay vì suy ra quan hệ từ thứ tự cell.')
task('safe','Đổi giá trị sang chuỗi có thể đặt vào ô bảng Markdown mà không làm ký tự phân cách phá cấu trúc bảng.')
task('find_project_root','Tìm thư mục chứa package, requirements và scripts theo các điểm xuất phát được hỗ trợ; trả root hợp lệ hoặc báo không tìm thấy project.')
task('core_pins','Sinh danh sách chân theo đúng thứ tự: cặp BLP/BLN theo cột, WLP/WLN theo hàng, WPOS/WNEG từng giao điểm rồi rail/bulk; dùng để nối SPICE và kiểm interface.')
task('Case.sums','Tính trực tiếp từng tổng cột sum(A_r*T_r,c) từ activation và ma trận ternary của case; trả oracle nguyên độc lập với điện áp ngspice.')
task('make_deck','Dựng testbench cho một case 4×4: model PVT, nguồn/precharge, tải bitline, PWM, trọng số và các lệnh sample BLP/BLN/vi sai; trả chuỗi SPICE để runner ghi và chạy.')
task('make_screen_deck','Giữ cùng stimulus và schematic của cặp đang chẩn đoán, thay riêng tải bitline và đơn vị PWM; trả deck để quét ảnh hưởng hai tham số có kiểm soát.')
task('make_pex_deck','Dùng cùng nguồn/PWM/tải như deck schematic nhưng thay subcircuit bằng PEX đã trích; nhờ đó chênh lệch số đo có thể gắn với R/C sau layout.')
task('measure_pair','Tạo thư mục mới cho một cặp tải/PWM, chạy hai pattern khó với ngspice, kiểm đủ các measurement hữu hạn và lưu measured.json; trả hai điện áp cùng gap của điều kiện đó.')
task('terminate','Callback timeout kiểm process ngspice còn chạy, đánh dấu hết hạn và kill process đó để runner không treo vô thời hạn.')
task('plot_progress','Đọc baseline/candidate vừa đo và vẽ khoảng cách mức trước/sau, ghi figure/report vào work directory của lượt này.')
task('fresh_activity','Duyệt receipts, kiểm mọi log nằm trong cache của phiên và được tạo sau fresh_start, xác nhận reuse=False/không có kết quả có sẵn rồi ghi sổ các tool đã chạy.')
task('TinyMHAWeights.__post_init__','Kiểm hình dạng và tính hợp lệ các ma trận trọng số Q/K/V/O ngay khi tạo đối tượng; ngăn phép nhân ma trận sai chiều đi tiếp vào reference.')
task('TinyMHAWeights.as_mapping','Trả các ma trận Q/K/V/O dưới dạng mapping theo tên projection để scheduler và exporter có thể dùng cùng một giao diện.')
task('softmax','Trừ giá trị lớn nhất trên trục cần chuẩn hóa, lấy hàm mũ rồi chia tổng; giảm nguy cơ tràn số khi tạo trọng số attention.')
task('_validate_input','Kiểm tensor đầu vào hữu hạn và có chiều đặc trưng d_model phù hợp với trọng số trước khi tính MHA.')
task('mha_from_projections attention','Chia Q/K/V theo head, tính QKᵀ/sqrt(d_head), softmax và tổ hợp V, sau đó ghép các head; hàm có output_projection còn áp dụng phép chiếu đầu ra.')
task('mha_fp32','Tính Q/K/V/O bằng số thực độ chính xác cao từ X và trọng số gốc rồi chạy attention; tạo reference số chưa đưa sai số lượng tử/CIM vào.')
task('ternary_projection_from_matrix','Lượng tử ma trận theo ngưỡng tỷ lệ thành -1/0/+1 và các hệ số nhóm của payload base-only; trả mô tả trọng số tương thích đường projection.')
task('mxfp4_ternary_projection','Mã hóa activation theo block MXFP4, gọi oracle tổng nguyên/fixed-point cho từng token rồi khôi phục hệ số; trả tensor projection cho reference lượng tử.')
task('mha_mxfp4_ternary','Dùng đường MXFP4/ternary cho Q/K/V/O, giữ phần attention số riêng và tổng hợp các thống kê lượng tử của phép chạy.')
task('error_metrics relative_l2','So reference và candidate cùng hình dạng, tính độ lệch tuyệt đối và/hoặc chuẩn L2 tương đối theo hàm hiện có; kết quả dùng để tách lỗi model, quantization và đọc macro.')
task('run_stage1','Từ config và seed xác định, sinh input/trọng số tiny-MHA, chạy reference gốc lẫn oracle MXFP4/ternary và trả tensor cùng các chỉ số so sánh.')
task('write_stage1_receipt','Ghi các tensor Stage1 và JSON số liệu/config để stage schedule, characterization và RTL regression có nguồn input có thể đối chiếu.')
task('TileCommand.to_mapping Stage4Artifact.to_mapping','Chuyển đối tượng mô tả command hoặc artifact thành dict/list thuần Python có thể ghi JSON; giữ các trường cấu hình, job và measurement của đối tượng.')
task('_projection_command','Tạo một lệnh projection cho token và tile output cụ thể, gán thứ tự phụ thuộc và tham số hình dạng từ config; trả TileCommand cho lịch MHA.')
task('build_tiny_mha_schedule','Sinh đồ thị lệnh theo Q/K/V, attention rồi O với các cạnh phụ thuộc và lượt dùng lại tile; trả lịch thực thi xác định.')
task('validate_schedule','Kiểm ID, thứ tự, kích thước và quan hệ phụ thuộc của các command để loại lịch hỏng trước khi chuyển sang controller/testbench.')
task('schedule_manifest','Tóm tắt config, số command, kiểu command và tài nguyên/lượt projection của lịch thành một manifest JSON.')
task('write_stage2_schedule','Sinh và kiểm lịch Stage2, ghi lịch và manifest vào thư mục đích rồi trả các đường dẫn cho các stage RTL/export kế tiếp.')
task('discover_sky130_model_library','Tìm sky130.lib.spice dưới PDK root được truyền, biến môi trường hoặc cấu trúc Volare/Ciel; trả đúng file model, báo rõ khi không tìm thấy.')
task('_header','Tạo phần tiêu đề/comment SPICE gắn tên mạch và cấu hình để các netlist được sinh có thông tin xuất xứ thống nhất.')
task('_cell','Sinh subcircuit leaf với tám NMOS và thứ tự chân BLP/BLN/WLP/WLN/WPOS/WNEG/VGND/VSUBS; bốn đường xả thực hiện bảng dấu ternary.')
task('_column','Nhân bản leaf theo số hàng, nối chung hai bitline và đưa từng cặp wordline/trọng số ra chân cột; trả hierarchy SPICE leaf+cột.')
task('_macro','Ghép các cột, chia sẻ wordline theo hàng và giữ bitline theo cột; trả hierarchy và interface của core gồm cả các mask trọng số từng giao điểm.')
task('_tb_header','Tạo phần chung cho testbench gồm model/corner, VDD, nhiệt độ, lựa chọn solver, precharge và monitor công suất; phần stimulus cụ thể được thêm sau.')
task('_precharge','Thêm hai PMOS precharge, hai tụ tải có điều kiện đầu và một monitor điện áp vi sai vào danh sách dòng testbench cho một cặp bitline.')
task('_dc','Thêm nguồn DC logic 0 hoặc VDD cho node điều khiển được chọn, để kích thích trọng số hoặc tín hiệu enable trong deck.')
task('_wl','Thêm nguồn PWM có độ rộng tỷ lệ với magnitude khi magnitude khác 0; magnitude bằng 0 tạo nguồn giữ wordline ở 0.')
task('_finish','Thêm phép tích phân công suất, transient analysis và kết thúc deck; để ngspice giải operating point precharge thay vì áp UIC gây offset giả.')
task('_add_delay','Thêm phép đo delay từ cạnh wordline đến điện áp vi sai ±1 mV, chọn chiều cạnh theo dấu tổng chuẩn; trả tên measurement cho manifest.')
task('_cell_tb','Sinh các instance leaf và stimulus quét trọng số/độ lớn activation, đặt phép đo vi sai và delay; trả deck cùng các nhãn oracle.')
task('_column_tb','Sinh bài thử cột với số hàng hoạt động và dấu khác nhau, tải chung bitline và các measurement; kiểm phép cộng dòng của nhiều leaf.')
task('_patterns','Tạo các activation và ma trận trọng số mẫu cho mảng có số hàng/cột chỉ định, bao gồm các cấu hình dấu và mức hoạt động cần kiểm.')
task('_macro_tb','Dùng các pattern mảng để sinh deck nhiều core, tính oracle từng cột, thêm sample vi sai/delay và trả các định nghĩa measurement.')
task('_column_case_tb','Tạo một deck cột cho đúng dấu và số hàng hoạt động, đặt tải theo số hàng và oracle tương ứng; tách thành job nhỏ để chạy song song.')
task('_macro_pattern_tb','Tạo deck của riêng một pattern mảng và các measurement của nó thay vì dồn toàn bộ pattern vào một bài mô phỏng lớn.')
task('_levels','Chuẩn hóa và kiểm các mức hierarchy cần chạy theo thứ tự cell/column/macro, loại yêu cầu mức không được hỗ trợ.')
task('generate_stage4_spice','Đi qua các mức được chọn, sinh netlist/testbench/jobs cho leaf/cột/mảng, ghi ra cây thư mục và trả manifest Stage4.')
task('emit','Hàm con của generator ghi netlist và một testbench cho stage/level chỉ định, lập bản mô tả artifact và thêm nó vào manifest.')
task('emit_jobs','Hàm con của generator ghi một netlist cùng nhiều deck con đã chia job, gắn oracle/measurement của từng job vào manifest để runner có thể chạy độc lập.')
task('_version _tool_version','Chạy executable với tùy chọn version được hỗ trợ, thu phần định danh phiên bản để report gắn với đúng bản tool cài trên máy.')
task('_run_job','Chạy một deck bằng executable ngspice trong timeout, ghi stdout/stderr, parse các phép đo yêu cầu và trả trạng thái/job result cho Stage4.')
task('run_stage4_manifest','Đọc manifest, chạy từng mức hierarchy theo thứ tự và chạy các deck con trong cùng mức bằng worker song song; tổng hợp kết quả và dừng khi một điều kiện bắt buộc không đạt.')
task('parse_spice_subckt_pins','Đọc khai báo subcircuit kể cả dòng tiếp nối, lấy danh sách chân theo đúng vị trí của core để so với interface RTL/LEF.')
task('_canonicalize_pex_interface','Bọc interface PEX theo thứ tự chân chuẩn của Stage4 nhưng giữ nguyên mạng trích xuất bên trong; tạo file PEX có thể cắm vào cùng testbench.')
task('_spice_device_count','Phân tích subcircuit và đệ quy qua instance để đếm primitive mục tiêu ở top, kể cả khi primitive nằm trong các cell con.')
task('expand','Hàm con của bộ đếm thiết bị mở rộng từng subcircuit, nhân số instance con và phát hiện vòng lặp hierarchy trước khi cộng primitive.')
task('_validate_stage4_deck_receipt','So deck, stimulus và receipt mô phỏng Stage4 để bảo đảm receipt PASS thuộc đúng mạch/input mà Stage5 đang dùng.')
task('validate_core_contract','So danh sách/chính xác thứ tự chân schematic core với blackbox RTL, loại chân chỉ thuộc wrapper và trả bản giao diện hợp lệ trước khi triển khai layout.')
task('discover_pdk','Xác định root PDK sky130A với các tech file cần cho Magic/KLayout và model; báo thiếu thay vì chọn ngầm một bộ PDK khác.')
task('_find_tool','Tìm đường dẫn executable theo tên trong môi trường thực thi và trả trạng thái sẵn có cho preflight.')
task('tool_inventory','Gom danh sách các executable EDA cần dùng, đường dẫn và phiên bản thành bảng inventory trước khi chạy layout.')
task('_version_tuple','Tách các thành phần số của chuỗi version để so mức phiên bản tool thay vì so chuỗi ký tự theo thứ tự từ điển.')
task('_write_core_lef_with_vgnd_landing','Đối chiếu hình VGND xuất từ Magic, chỉ công bố pad M4 đủ chỗ đặt via làm pin nguồn và biến các bar còn lại thành obstruction; không thay kim loại GDS của macro.')
task('_now','Trả thời gian hiện tại theo định dạng dùng trong receipt để sắp thứ tự các lần chuẩn bị/chạy tool.')
task('_read_pass_receipt passed_receipt','Mở receipt được yêu cầu, kiểm định dạng/trạng thái thành công và tính hiện hữu của dữ liệu; thiếu file hoặc trạng thái không hợp lệ thì không nhận làm bằng chứng PASS.')
task('_relative_delta','Tính thay đổi tương đối của số đo post-layout so với pre-layout, có xử lý mẫu số và dữ liệu không hợp lệ theo kiểm tra trong hàm.')
task('_run','Chạy lệnh với cwd, môi trường, input tùy chọn và timeout; thu mã thoát/log để runner stage quyết định có nhận artifact hay không.')
task('_magic','Gọi Magic không giao diện với tech file và script Tcl đã cho, thu transcript của extraction/layout trong thời gian giới hạn.')
task('_klayout_deck','Xác định deck kiểm KLayout nằm trong PDK đang chọn để DRC dùng đúng layer/rule set của tiến trình.')
task('write_preflight_receipt','Kiểm tool/PDK và hợp đồng core trước chạy Stage5, ghi receipt các điều kiện đầu vào để kết quả layout không phụ thuộc một môi trường chưa kiểm.')
task('run_stage5','Điều phối kiểm core, dựng/xuất view vật lý, DRC/extraction/LVS và PEX; kiểm số NFET trích xuất bằng 128 rồi ghi receipts dùng cho characterization.')
task('main','Điểm vào của recipe kiểm Stage5: đọc cấu hình/đường dẫn, gọi các kiểm liên quan và in kết quả để người dùng biết artifact nào có thể dùng tiếp.')
task('shown','Định dạng một đường dẫn hoặc trạng thái file để hiển thị trong bảng kết quả mà không làm thay đổi artifact.')
task('nonempty','Trả điều kiện file tồn tại và có nội dung, dùng để tránh gọi một đường dẫn rỗng là kết quả của tool.')
task('_finite','Kiểm một giá trị có thể dùng như số hữu hạn, ném lỗi kèm nhãn trường nếu gặp NaN/Inf hoặc giá trị không đúng kiểu số.')
task('build_characterization','Kiểm chuỗi receipts hiện tại, thu điện áp/độ trễ/năng lượng từ các mẫu schematic/PEX rồi fit và thống kê model transfer TT.')
task('CIMMacroModel.__post_init__','Kiểm characterization có đúng format và trạng thái PASS_TT_MODEL trước khi cho surrogate macro dùng các hệ số fit.')
task('CIMMacroModel.tile','Nhận 32 activation ACT_X2 và trọng số ternary 32×8, chia thành các lát vật lý4×4 rồi áp gain/fit từng cột; đồng thời đếm các trường hợp ngoại suy miền đã đo.')
task('CIMMacroModel.project','Chia token theo block32, dùng tile model để lấy partial sums rồi áp hệ số của payload và cộng nhóm thành vector output.')
task('evaluate_mha','Chạy MHA qua surrogate TT và so riêng với reference floating và oracle ternary/fixed-point; báo sai số model cùng các bộ đếm ngoại suy.')
task('write_stage6','Tạo characterization/đánh giá MHA Stage6 và ghi model/report để bước phân tích decoder có nguồn dữ liệu số và điện tương ứng.')
task('_matrix','Sinh ma trận ternary4×4 cho số hàng hoạt động và phép xoay chỉ định, phục vụ quét mức/dấu có tính lặp lại.')
task('weight','Hàm con sinh giá trị ternary của một ô từ chỉ số hàng/cột và quy tắc pattern; không truy vấn kết quả mô phỏng để chọn trọng số.')
task('sweep_cases','Tạo bộ case quét các code activation, dấu và số hàng hoạt động hợp lệ để kiểm độ bao phủ transfer của core.')
task('mha_cases','Lấy các pattern core xuất hiện trong MHA xác định, chọn cả pattern phổ biến và cực trị để bổ sung vào bộ kiểm vật lý.')
task('extremes','Tính đặc trưng cực trị từ activation/trọng số của một pattern, dùng làm khóa xếp hạng khi chọn case MHA khó.')
task('pvt_points','Trả danh sách corner/điện áp/nhiệt độ cho smoke test hoặc sweep đầy đủ theo cờ full.')
task('summarize_jobs','Gom các job hoàn tất, so oracle với dấu/khoảng điện áp và mức hoạt động; trả chẩn đoán transfer thụ động, không diễn giải thành độ chính xác ADC.')
task('_expected_measurements _expected','Tạo tập tên measurement mà deck tương ứng bắt buộc phải có; runner dùng tập này để phát hiện log chạy dở hoặc sai thời điểm sample.')
task('_validated_checkpoint','Chỉ nhận job trước đó khi metadata deck/input và nội dung log đều còn khớp, measurement đầy đủ; trả điều kiện tái dùng cho recipe đã bật checkpoint.')
task('write_receipt write_report','Hàm con của runner đóng gói trạng thái cùng kết quả đang tích lũy và ghi JSON report của lần chạy, kể cả khi cần giữ phần đã hoàn tất để chẩn đoán lỗi.')
task('_number','Lấy một measurement từ job theo key, chuyển sang số và kiểm tính hữu hạn trước khi dùng tính khoảng mức.')
task('analyze_jobs','Gom mẫu theo cột và tổng nguyên, tìm hai mức có khoảng điện áp giao nhau hoặc thứ tự đảo tại sample đang kiểm; trả các cặp cần đo lại.')
task('make_targeted_deck','Giữ drivers/tải giống nhau giữa schematic và PEX, chỉ thay netlist và thêm các mốc sample BLP/BLN/vi sai để định vị nguồn chênh lệch.')
task('_safe_deck','Đọc deck trong phạm vi root cho phép và kiểm dấu nội dung được ghi trong report trước khi đưa nó sang phép so sánh.')
task('_selected_time_comparison','Đối chiếu một cặp mức khó ở các thời điểm sample đã chọn trên schematic và PEX, tách đảo mức do thời điểm đọc khỏi sai khác sau layout.')
task('transfer_error','Trình bày cặp tổng chuẩn bị đảo thứ tự từ baseline PEX đã đo trong lượt mới, kèm các điện áp và gap làm tiền đề chọn tải/PWM.')
task('selected_cases','Lấy các pattern gốc tạo nên những cặp mức lỗi trong report để sweep dùng lại đúng stimulus, không đổi bài toán khi đổi tham số.')
task('summarize_point','Tính gap và kiểm mức zero tại một cặp load_ff/pwm_unit_ps từ measurement, trả hàng kết quả cho bảng sweep schematic.')
task('candidate_points','Chọn các điểm sweep schematic đã có thứ tự mức phù hợp để đem kiểm lại PEX; đây là bước chọn ứng viên trước đo sau layout.')
task('summarize_candidate','So mức của các pattern đã chọn, mức zero và hai mốc sample trên PEX; trả chỉ số thứ tự/aperture của từng ứng viên tải/PWM.')
task('_read _read_reports','Đọc một hay nhiều JSON report được chỉ định và trả nội dung cho bước phân tích; phiên bản nhiều report gom đúng các nguồn training/holdout cần so.')
task('selected_candidate','Kiểm điểm được chọn thực sự nằm trong các điều kiện đã đo và đạt tiêu chí ordering của report trước, rồi trả load/PWM cho sweep đầy đủ.')
task('_provenance','Gom danh tính config/netlist/model và report cha để gắn mỗi bộ measurement với đúng chuỗi input đã tạo ra nó.')
task('analyze_transfer','Gom khoảng mức theo tổng chuẩn, kiểm active-zero và khoảng thời gian sample1.9/2.1ns để đánh giá ordering/aperture của candidate.')
task('_checkpoint','Mở checkpoint của đúng deck, PEX, model và phiên bản ngspice, xác nhận các measurement còn đúng rồi mới trả record có thể dùng lại.')
task('_matches_selected','So các measurement của case quét đầy đủ với measurement đã ghi ở phép chọn candidate, nhằm phát hiện việc đổi input/điểm đo giữa hai chiến dịch.')
task('candidate_result','Trình bày số đo của cùng cặp pattern tại điểm tải/PWM candidate và so với baseline để chỉ ra can thiệp nào làm gap đổi dấu.')
task('parse_measurements','Dùng biểu thức chính quy đọc tên và số của measurement ngspice trong transcript, trả mapping để tính factorial từ log thật.')
task('heldout_cases new_holdout_cases fresh_holdout_cases','Sinh tập pattern mới từ lịch MHA hoặc hạng pattern xác định, loại các payload đã xuất hiện trong tập trước và trả danh sách case kiểm độc lập.')
task('_verified_stage49','Kiểm netlist/model/candidate và các report Stage4.9 đang dùng cùng provenance trước khi nhận chúng làm calibration nền cho holdout.')
task('_spec_gaps','Đọc các điều kiện/độ thiếu trong specification report để bảng inspect có thể chỉ ra yêu cầu nào chưa có dữ liệu đáp ứng.')
task('_baseline_gaps','Tóm tắt các điều kiện còn thiếu của baseline prototype riêng với các phép kiểm signoff, giúp bảng inspect không gộp hai mức bằng chứng.')
task('analyze_decoder','Fit các ngưỡng midpoint chỉ từ khoảng mức training, áp cùng ngưỡng lên training/holdout và đếm lỗi dưới ngân sách nhiễu điện áp đã đặt.')
task('reachable_sums reachable_two_row_sums','Liệt kê các tổng nguyên có thể đạt từ bảng ACT_X2 và ternary của số hàng đang xét; bảng mức là cơ sở chọn stimulus calibration và số ngưỡng decoder.')
task('calibration_cases','Tạo pattern hợp lệ cho từng mức reachable cần calibrate, thay đổi phân rã activation/trọng số và cột theo recipe để bao phủ các mức chưa được đo.')
task('_observation','Rút điện áp, nhãn tổng, cột và thời điểm của một job thành observation theo feature yêu cầu, dùng chung định dạng cho fit và chấm.')
task('analyze_feature_training','Chọn feature và fit ngưỡng đơn điệu từ riêng training measurements, trả decoder cố định cùng khoảng mức/noise margin.')
task('analyze_feature_holdout','Áp feature/ngưỡng được training chọn lên case holdout, tính decoded sums và số lỗi dưới error budget, không điều chỉnh theo đáp án holdout.')
task('_verified_calibration','Kiểm file calibration, PEX/model và report cha còn đúng với phép đọc đang dùng; trả fit đã được xác nhận để holdout không tự chọn lại ngưỡng.')
task('observations','Tính lại tổng chuẩn và metadata từ activation/trọng số của từng job thay vì tin nhãn đã cache, sau đó trả bộ điểm training/query nhất quán.')
task('_nearest','Tìm observation training gần query theo khoảng cách vi sai/common-mode và điều kiện hoạt động đã chọn; trả dự đoán cho một query.')
task('_score','Áp luật dự đoán lên một tập query, so với nhãn chuẩn và trả số lỗi/mức cải thiện để so các family feature.')
task('_select_training_candidates','Chọn cấu hình thắng trong từng family bằng training và chỉ đề cử khi tốt hơn feature vi sai gốc; không lấy holdout để chọn winner.')
task('analyze','Gom các phép chấm family feature trên training và tập kiểm, lập bảng so sai số và chỉ rõ lựa chọn xuất phát từ tập nào.')
task('select_hard_cases','Xếp hạng các lỗi scalar decoder bằng dữ liệu training, giữ case cũ đã biết và chọn tối đa max_cases để thử cách đọc tách hàng.')
task('errors','Hàm con đánh giá lỗi dự đoán với tùy chọn loại chính case đang chấm khỏi training; dùng để chọn mẫu khó mà không tự khớp bản thân mẫu.')
task('split_case','Giữ nguyên ma trận16 trọng số nhưng đặt PWM các hàng ngoài partition về0; tạo hai case con tương ứng cặp hàng trên/dưới.')
task('summarize_partition','Gom phép đo các partial sums của từng partition, kiểm thứ tự mức và khả năng cộng lại, giữ scope là điện áp đã đo.')
task('_within','Chuẩn hóa đường dẫn tương đối và kiểm nó vẫn nằm dưới root được cho phép trước khi mở file/report.')
task('_verify_jobs','Đối chiếu deck/log/model/PEX/version của từng job calibration hoặc holdout và yêu cầu đủ measurement trước khi fit/chấm.')
task('_verify_targeted','Kiểm report targeted2+2 và các input định danh còn khớp với nguồn hiện tại để không dùng calibration khác điểm làm việc.')
task('_budget','Đọc ngân sách sai số điện áp đã được khai báo cho prototype, trả giá trị dùng chung trong training và holdout.')
task('_prepare_and_run','Từ case cha tạo các deck con theo partition, ghi source/job metadata và tùy cờ execute chạy ngspice; trả danh sách job có measurement hoặc trạng thái chuẩn bị.')
task('_calibration_analysis','Fit ngưỡng theo phase/cột từ các job calibration và đối chiếu các mẫu targeted dưới cùng noise budget.')
task('run_calibration','Điều phối kiểm input, sinh các mức partial-sum, chạy/đọc calibration2+2 và ghi bộ ngưỡng để cố định trước holdout.')
task('_holdout_analysis','Dùng bộ ngưỡng đã khóa để decode hai phase của case mới, cộng partials, so với tổng cha và đếm lỗi có/không noise budget.')
task('run_holdout','Kiểm bộ calibration và nguồn mạch, chọn pattern chưa dùng, thực hiện hai lượt đọc rồi ghi report holdout với decoder cố định.')
task('partition_result','Vẽ và tóm tắt kết quả pilot trước/sau của phiên mới; giữ phần recipe2+2 để tham chiếu cách đọc thay vì gọi lại log cũ làm measurement mới.')
task('model_sections','Đọc đúng các khai báo .lib trong model file và trả corner có thể chọn, không suy tên corner từ tên model hoặc file include.')
task('select_worst_cases','Chọn các pattern cực trị tạo nên gap pooled nhỏ nhất ở từng cột để smoke test tập trung vào trường hợp khó.')
task('make_smoke_deck','Sinh deck của case được chọn tại một bộ corner/VDD/nhiệt độ với cùng PEX và phép sample để so độ nhạy theo PVT.')
task('summarize_point','Gom measurement tại một điểm điều kiện, tính khoảng mức/gap và trạng thái đạt của các cặp đang theo dõi; tên point phải đọc cùng nhóm input được nêu ở phần dữ liệu của cell.')
task('_vectors','Tạo hoặc tải vector activation, ternary và kết quả chuẩn từ hợp đồng fixed-point dùng cho regression RTL.')
task('_testbench','Sinh mã Verilog testbench cho controller/macro-model, đưa vector vào theo handshake và chèn assertion so output với oracle.')
task('signed_literal','Biểu diễn một số nguyên có dấu thành literal Verilog đúng độ rộng bits, xử lý dấu âm tường minh để frontend không suy sai kích thước.')
task('_scale','Thực hiện phép khôi phục scale số nguyên theo code E8M0/fixed-point để testbench stress có expected value nhất quán với datapath.')
task('make_vectors','Đóng gói activation/trọng số/alpha và scale thành vector bus cùng expected output cho một giao dịch RTL.')
task('scenarios','Liệt kê các kịch bản reset/backpressure/protocol cần stress thay vì chỉ thử giao dịch liên tục không có gián đoạn.')
task('_testbench_2p2','Từ oracle/vector đã cố định, thay macro-model bằng mô hình hai lần đọc và sinh testbench kiểm số transaction, partial sum và kết quả cộng.')
task('locate_openlane_flow','Tìm entrypoint flow.tcl của OpenLane từ các đường dẫn/biến môi trường mà recipe hỗ trợ trước khi dựng lệnh triển khai.')
task('_gds_hierarchy','Đọc các structure/reference trong GDS và xây đồ thị cell gọi cell, dùng để xác nhận macro vật lý thật có trong top.')
task('_gds_reaches','Duyệt đồ thị hierarchy từ source tới target, trả điều kiện top có thể đi đến cell macro cần tìm.')
task('_lef_pins_and_size _lef_size','Đọc outline SIZE và, với hàm tương ứng, tên/chân từ LEF; trả kích thước micromet dùng để kiểm placement và diện tích macro.')
task('_lef_has_ground_met4_landing','Kiểm LEF có pad VGND trên M4 đủ diện tích nối via và các bar khác được đánh dấu cản phù hợp; trả điều kiện giao diện ground hợp lệ.')
task('_snapshot','Chụp các nguồn/config/đường dẫn liên quan vào thư mục theo tag trước khi triển khai để kết quả có thể truy lại input.')
task('_top_metric_reasons','Đọc metrics OpenLane, liệt kê các kiểm thiếu hoặc vi phạm; coi giá trị sentinel -1 là chưa có kết quả thay vì số đo hợp lệ.')
task('_pdn_ground_reasons','Kiểm DEF, log PDN và LEF core có liên kết thật từ pad VGND M4 qua via tới M5; trả danh sách lý do ground chưa đạt.')
task('_audit','Ghi tập lý do và metrics của top theo tag thành report audit để trạng thái cuối không chỉ phụ thuộc việc file GDS có tồn tại.')
task('_placement','Đọc cấu hình vị trí macro và yêu cầu có instance thực, loại file rỗng hoặc chỉ có comment; trả placement phục vụ preflight.')
task('preflight','Đối chiếu source/config, footprint LEF, placement và sự có mặt tool trước khi cho flow tích hợp đi tiếp; trả trạng thái và các lỗi input cần sửa.')
task('receipt_status','Đọc trạng thái một receipt tương đối trong cây kết quả và trình bày giá trị/trường hợp thiếu để bảng không mặc định PASS.')
task('tag_ok','Kiểm tag chỉ chứa ký tự được phép để tên thư mục/container của một lượt chạy không làm hỏng câu lệnh hoặc trỏ sai nơi lưu.')
task('_verified verified verified_item','Mở artifact được mô tả bằng path và dấu kiểm, yêu cầu file tồn tại/nội dung còn khớp rồi trả path hoặc dữ liệu để consumer không dùng file đã đổi.')
task('_rc_audit','Phân tích mạng R/C trích xuất, tìm đảo chỉ có tụ hoặc đường nối chỉ gồm R=0; trả số liệu/điều kiện để PEX có parasitic thật chứ không chỉ là file rỗng.')
task('source','Đọc report nguồn theo tag và xác nhận các artifact/receipt cần dùng cho recipe vật lý, trả report cùng các đường dẫn đã kiểm.')
task('component_masters','Đọc tên master/loại component trong view được truyền để thống kê sự có mặt các macro hoặc standard cell.')
task('validate_streamout_log','Kiểm transcript streamout có marker kết thúc và không có dấu hiệu thiếu cell/lỗi đọc view trước khi nhận GDS xuất ra.')
task('validate_netgen','Kiểm phần verdict cuối của transcript Netgen và yêu cầu mạch match theo tiêu chí hàm, không suy thành công từ return code đơn thuần.')
task('prototype_sdc','Chỉnh nội dung SDC theo chu kỳ clock prototype yêu cầu trong khi giữ các ràng buộc interface liên quan; trả text cho lượt STA.')
task('timing_metrics','Tìm setup/hold worst slack trong các vùng marker được quy định, yêu cầu đúng một số hữu hạn cho mỗi phép đo rồi trả đơn vị ns.')
task('clock_model','Bổ sung thông tin clock cho mô hình ETM bằng đúng tên cổng clock của hợp đồng top, để Liberty xuất ra được parser nhận interface clock.')
task('item file_item','Tạo mô tả artifact gồm đường dẫn đã chuẩn hóa và dấu kiểm nội dung, dùng trong inputs/outputs/receipts để liên kết file thật với report.')
task('Flow.__init__','Kiểm settings, tag, giới hạn concurrency/timeout và dung lượng trống; tạo work directory cùng hai sổ receipts/outputs cho một phiên EDA.')
task('Flow.log','Mở native log và in phần đầu/cuối hoặc toàn bộ nếu ngắn, giữ đường dẫn đầy đủ để người đọc có thể xem transcript không bị cắt.')
task('Flow.run','Lập danh tính lệnh và input, chụp source nhỏ, chạy process có timeout, stream stdout, ghi native.log/step.json và chỉ trả thành công khi return code cùng outputs hợp lệ.')
task('Flow.container','Gọi bộ dựng lệnh container của runtime standalone với root/work hiện tại; trả argv, không tự chạy tool trong phương thức này.')
task('Flow.render render','Đặt biến môi trường chỉ đúng GDS/top/PNG, chạy KLayout batch với script đã khai báo trong notebook, kiểm chữ ký PNG và đăng ký ảnh trong outputs.')
task('bridge_targets','Đổi các hình pad/strap cần nối sang tọa độ database theo units, trả vị trí bridge ground để worker đối chiếu hình học.')
task('completed_run_log','Chọn đoạn transcript tương ứng đúng transient đã sinh raw file, loại phần chạy batch khác sau đó để không ghép sai waveform với thời gian sample.')
task('read_raw','Đọc header/danh sách biến và các sample của ngspice raw ASCII, yêu cầu một transient thực hợp lệ rồi trả các vector theo tên với time tính bằng giây.')
task('sample','Nội suy vector điện áp/tín hiệu được chọn tại thời gian at_s, cho phép các phép kiểm dùng chung đúng mốc sample.')
task('sampling_witness','Lấy các mốc trong cửa sổ precharge/track/hold, so tín hiệu với ngưỡng high_v/low_v và trả bằng chứng thời gian lấy mẫu khớp điện áp được giữ.')
task('control_block','Tạo khối .control SPICE chạy transient và ghi raw ASCII cùng marker hoàn tất; nhận danh sách vector cần giữ để dữ liệu waveform có thể đọc lại.')
task('summarize','Đọc XML DRC KLayout, gom số marker và thông tin nhóm rule/trạng thái để report có thể trình bày số vi phạm trong scope đã chạy.')
task('full_groups_clean','Kiểm từng nhóm rule bắt buộc thực sự đã được xử lý và không có marker; trả điều kiện clean có scope thay vì chỉ kiểm tổng marker bằng0.')
task('stable_log_cosh','Viết lại biểu thức log(cosh) tương đương về mặt đại số nhưng ổn định ở điện áp Newton thử lớn, tránh overflow của behavioral source.')
task('cards','Ghép dòng SPICE bắt đầu bằng + vào statement trước đó; trả danh sách card logic và báo lỗi khi có continuation mồ côi.')
task('ports','Tìm duy nhất một .subckt có tên yêu cầu trong danh sách card và trả các chân theo thứ tự, bao gồm các chân vốn nằm ở dòng tiếp nối.')
task('name','Chuẩn hóa tên cổng ADC: bỏ tiền tố a_, đổi chỉ số [i] thành _i, bỏ dấu gạch dưới dư và về chữ thường để đối chiếu bảng mapping.')
task('core_node','Ánh xạ chân SAR digital sang rail, clock, comparator, reset và trạng thái EOC của testbench chung; cổng cấu hình giữ tên đã chuẩn hóa.')
task('clock_node','Ánh xạ các chân clockgen/điều khiển sample và bit delay-control sang node của SAR/config trong testbench; cổng lạ bị báo lỗi.')
task('matrix_node','Ánh xạ chân CDAC của phía P/N sang AIN, CTOP, SAMPLE, row/column/binary-control của SAR; kiểm đúng họ tên chân và bit index.')
task('subcircuits edu_subcircuits','Ghép continuation, tách các block .subckt/.ends theo tên và giữ body của từng block; báo cấu trúc dang dở để builder không dùng subcircuit bị cắt.')
task('fast_matrix','Đọc inventory515 tụ signal của CDAC nguồn, giữ tổng điện dung và transmission gate đầu vào, thay bộ lái bottom bằng biểu thức điện áp tương đương để giảm thời gian mô phỏng.')
task('library','Đọc các schematic ADC đã chọn, ghép digital core/clockgen/CDAC/comparator theo mapping chân, bỏ đúng .end giữa file và tùy chọn dùng CDAC rút gọn; trả body SPICE của partition.')
task('bench','Dựng testbench partition ADC với diff/common-mode hợp lệ, nguồn/config/reset/start, transient và các vector cần lưu raw để đo quá trình chuyển đổi.')
task('SharedSpice.__init__','Mở libngspice bằng ctypes, đăng ký callback log/exit/nguồn ngoài và khai báo kiểu C cho các API; tạo lịch sử nguồn để RTL điều khiển simulator theo thời gian.')
task('SharedSpice.__init__.output','Callback nhận thông điệp của ngspice, ghi ngay vào log và đánh dấu error/fatal; chỉ lọc dòng tiến độ lặp lại khỏi phần in notebook.')
task('SharedSpice.__init__.voltage','Callback nguồn ngoài: lấy lịch sử theo tên nguồn và nội suy giá trị tại thời gian simulator yêu cầu, ghi giá trị vào con trỏ C do ngspice truyền vào.')
task('SharedSpice.command','Gửi một lệnh tới ngspice shared API, kiểm return code và các lỗi callback đã bắt; ném lỗi nếu simulator không chấp nhận lệnh.')
task('SharedSpice.initial','Đặt giá trị nguồn ngoài ở t=0 trong bảng lịch sử để solver có điều kiện ban đầu xác định.')
task('SharedSpice.drive','Thêm cạnh điện áp có rise/fall hữu hạn vào lịch sử nguồn tại thời gian hiện tại và đặt breakpoint; solver phải dừng tại cạnh do RTL phát ra.')
task('SharedSpice.vector','Lấy vector thật từ ngGet_Vec_Info, kiểm con trỏ/độ dài rồi sao dữ liệu sang NumPy để Python đọc waveform mà không giữ vùng nhớ C dễ bị đổi.')
task('SharedSpice.advance','Đặt stop time mới, gọi tran hoặc resume và kiểm simulator đã đi đến đúng biên thời gian cho một pha co-simulation.')
task('RTL.__init__','Ghi testbench SAR, biên dịch bằng Icarus rồi mở vvp với stdin/stdout pipe; process RTL sẽ nhận từng quyết định comparator từ Python.')
task('RTL.read','Đọc và parse một dòng STATE từ vvp theo RTL_FIELDS, trả các bit điều khiển CDAC/sample/EOC/result; thiếu dòng hoặc sai format thì báo lỗi.')
task('RTL.clock','Gửi quyết định comparator vào stdin, cho RTL đi qua một chu kỳ clock và đọc state mới để phần analog cập nhật theo đúng quyết định ấy.')
task('RTL.close','Đóng stdin và chờ/dừng process vvp theo quy trình cleanup để co-simulation không để lại process nền.')
task('cap_map','Đọc các instance/cell tụ của adc_array_matrix_12bit, giải ánh xạ chân và giá trị từng tụ; yêu cầu đủ515 phần tử trước khi tính điện áp bottom tương đương.')
task('bottom','Tính trạng thái high/low của mỗi tụ từ các bit SAR rồi cộng C_i*V_bottom_i và chia tổng C; trả điện áp bottom tương đương của một phía CDAC.')
task('bit','Hàm con của bottom giải một tên rail hoặc bit row/column/bincap từ state SAR, báo lỗi nếu không nhận dạng được chân điều khiển.')
task('coupled_deck','Ghép core/acquisition, conditioner và comparator/CDAC transistor với các nguồn bridge do SAR điều khiển; thêm stimulus activation/trọng số cùng các vector phải ghi.')
task('simulate','Mở RTL và shared ngspice, luân phiên advance analog → đọc comparator → clock SAR → cập nhật nguồn điều khiển; ghi case, transcript, raw và summary conversion khi EOC hoàn tất.')
task('bridge','Hàm con của vòng co-simulation chuyển state SAR hiện tại thành mức các nguồn sample/bottom-clock trong ngspice trước khi đi tiếp thời gian.')
task('quantize_context','Với từng phần tử context, chọn mức có dấu gần nhất trong bảng ACT_X2 mà projection O hỗ trợ; trả tensor context lượng tử để lập các payload phép chiếu đầu ra.')
task('Experiment.__init__','Gắn Experiment với flow, kiểm shared ngspice và bộ SAR RTL đã ghim nguồn, lập danh sách input source cùng sổ record/calibration riêng của phiên.')
task('Experiment.payload','Chuẩn hóa activation và trọng số một cột thành case4×4 với các cột khác bằng0; tạo khóa định danh payload để cùng pattern không bị mô phỏng trùng trong phiên.')
task('Experiment.measure','Chạy hoặc lấy record đã có trong chính phiên cho một payload, kiểm input/source của record và đăng ký đường dẫn summary cho consumer.')
task('Experiment.many','Lọc payload trùng, điều phối một nhóm conversion bằng số worker được giới hạn rồi trả mapping các record đã hoàn tất.')
task('Experiment.calibrate calibrate','Đo ba payload calibration riêng, lấy mã ADC của chúng và fit slope/offset chuyển code sang tổng nguyên; cố định tập key calibration trước khi gọi projection/holdout.')
task('Experiment.project','Lập các yêu cầu conversion cho từng hàng/output của projection, đổi code bằng fit đã khóa và ghép các tổng theo mapping chỉ định; trả tensor projection cùng record references.')
task('Experiment.mha mha','Sinh input/weights tiny-MHA xác định, đo các projection Q/K/V, tính attention số, lượng tử context rồi đo O; ghi mha_end_to_end.json và hai chuẩn sai số reference.')
task('catalog','Đọc config/view cần render, lập danh mục tên macro, tên top trong GDS, đường dẫn và yêu cầu bắt buộc; trả các item dùng cho vòng render.')
task('add','Hàm con của catalog kiểm đường dẫn GDS của một item và thêm record tên/tiêu đề/top cell vào danh mục; item bắt buộc thiếu sẽ báo lỗi.')
task('payload','Chuẩn hóa các trường activation/trọng số/column trong case thành biểu diễn so sánh nhất quán để kiểm trùng và đối chiếu source.')
task('truth','Tính lại tổng nguyên của cột đang đo từ activation và ternary trong case; nhãn này độc lập với ADC code và decoder.')
task('parse_states','Tách transcript STATE của SAR thành chuỗi bản ghi bit điều khiển/mã/EOC và kiểm dòng nào thuộc đúng format chứ không lấy số bất kỳ trong log.')
task('validate_case','Đối chiếu summary, stimulus, state SAR và điều kiện hoàn tất conversion; trả record đủ tin cậy cho fit/score hoặc báo đúng điều kiện bị vi phạm.')
task('assert_disjoint','So các payload vật lý của calibration và holdout, ném lỗi nếu giao nhau để fit không được chấm lại trên pattern của chính nó.')
task('estimate','Dùng slope/offset FROZEN đã fit từ calibration để chuyển code ADC của một record thành ước lượng tổng nguyên trước làm tròn.')
task('decode','Làm tròn ước lượng tổng nguyên bằng luật xác định của decoder; kết quả so với truth để đếm integer mismatches, tách khỏi residual chưa làm tròn.')
task('plot_conversion','Đọc raw/state của một conversion, vẽ điện áp input/comparator và các điều khiển SAR quanh quá trình sample/convert; lưu hình trong work của phiên.')
task('plot_mha','Đọc báo cáo ứng dụng vừa đo để vẽ projection/context/output và sai số; figure dùng tensor thật thay vì minh họa tùy ý.')
task('measured_projection','Theo stage/token/output trong mapping jobs, tìm record đã kiểm, decode bằng fit cố định và điền tensor projection với đúng activation yêu cầu.')
task('testbench','Sinh Verilog testbench của SAR theo giao thức cell: cung cấp reset/config/comparator và in STATE hoặc code/EOC để Icarus có thể chạy/kiểm từng case.')
task('run_tool','Chạy lệnh tool host với stdin/môi trường/timeout tùy chọn, thu toàn bộ log, yêu cầu return code hợp lệ và trả transcript cho checker.')
task('routing_progress','Đọc các report OpenROAD của tuyến triển khai và trình bày số liệu/violation theo nhãn thật; phần khai báo vẫn giữ khả năng đọc recipe cũ.')
task('slack','Tìm đúng một giá trị worst slack giữa marker AUTOMX_SETUP hoặc AUTOMX_HOLD, chuyển về float ns và báo lỗi nếu thiếu/nhập nhằng.')
task('guard_settings','So cấu hình phiên với bản đã khóa; báo thay đổi ngoài ý muốn trước khi recipe server dùng các tag hoặc input đó.')
task('project_path','Chuyển một đường dẫn cấu hình thành đường dẫn dưới project root, kiểm phạm vi phù hợp trước khi đọc hoặc ghi artifact phiên.')
task('link','Tạo liên kết hiển thị tới một file kết quả/đường dẫn trong bảng notebook, giữ người đọc có thể mở nguồn của số liệu.')
task('save_session','Ghi trạng thái/các artifact/provenance đang tích lũy của phiên server thành JSON để tiến trình kế tiếp có điểm tiếp nối rõ ràng.')
task('snapshot_sources','Duyệt cấu trúc input của phiên và lưu các source liên quan làm snapshot để kết quả có thể truy lại đúng nội dung đã chạy.')
task('numerical_receipts','Tìm và kiểm các receipt của reference số và schedule trong thư mục yêu cầu, trả danh sách phục vụ bảng nguồn của recipe server.')
task('final_cli_report','Duyệt các dòng output CLI, tìm đối tượng report JSON cuối đã hoàn tất và trả nó; tránh coi dòng log trung gian là kết quả flow.')
task('dependencies','Lập quan hệ các recipe/kết quả cũ và so input artifact khi hàm được gọi; ở tuyến hiện tại cell gọi fresh_activity để trình bày các tool mới của phiên.')
task('final_results','Đọc analog_adc_mha và proof GDS/STA trong flow.outputs, lập bảng calibration, projection, L2 và đường dẫn top GDS của lượt vừa chạy.')
task('read_report','Đọc JSON report tương đối dưới root, kiểm đường dẫn/file theo helper của story và trả nội dung cho bước đọc số đo hoặc kiểm cạnh phụ thuộc.')
task('decoder_errors','Trình bày report chẩn đoán scalar-decoder của recipe cũ với số lỗi và các mức khó; trong tuyến standalone phần này phục vụ giải thích quyết định thay cách đọc.')
task('edu_table','Ghép bảng số liệu bài học thành Markdown trong namespace riêng, để các kết quả nibble, transistor hoặc tile có thể đối chiếu theo từng hàng.')
task('edu_decode','Kiểm nibble0…15 và byte scale hữu hạn0…254, tra dấu/độ lớn E2M1 rồi nhân 2^(E−127); trả các giá trị số thực đã khôi phục.')
task('edu_quantize_block','Nhận đúng32 số hữu hạn, chọn shared scale từ max(abs(x)), tìm mã gần nhất trên bảng E2M1 với luật tie đã chọn và trả codes uint8 cùng byte E8M0.')
task('edu_weight_bits','Kiểm weight là -1/0/+1 rồi trả cặp WPOS/WNEG tương ứng01/00/10; loại giá trị ngoài ternary trước khi sinh netlist/stimulus.')
task('edu_active_paths','Từ trọng số và dấu activation, tính điều kiện bật của bốn nhánh PP/PN/NP/NN; trả dict dùng để chứng minh dấu phép nhân cho45 tổ hợp hợp lệ.')
task('edu_leaf_netlist','Duyệt bảng bốn nhánh, sinh từng transistor trọng số và transistor activation với D/G/S/B đúng node và W/L0.84/0.15µm; trả nguyên subcircuit leaf8T.')
task('edu_subcircuits','Đọc SPICE nguồn, ghép dòng + và tách từng subcircuit theo tên để so nguyên thứ tự chân/instance của leaf, cột và core được tự dựng.')
task('edu_draw_leaf','Vẽ sơ đồ cell với tám ký hiệu NMOS, bốn nhánh, BLP/BLN, node giữa và VGND; gate trọng số/activation và bulk được chú thích để đối chiếu từng dòng SPICE.')
task('edu_nmos','Vẽ một NMOS tăng cường bốn cực theo ký hiệu mạch: kênh ngắt đoạn, gate cách điện, drain/source và đường body; trả/vẽ các nét tại tọa độ để sơ đồ8T dùng cùng một kiểu thiết bị.')
task('edu_draw_device','Vẽ hình phóng to NMOS và các panel active/poly/contact cùng mặt cắt khái niệm; đặt nhãn D/G/S/B và W/L để phân biệt ký hiệu mạch với hình học chế tạo.')
task('edu_column_netlist','Sinh interface của cột với từng cặp wordline/trọng số theo hàng, thêm XCELL_r nối chung BLP/BLN và rail; trả subcircuit4×1 để so source.')
task('edu_core_netlist','Sinh50 chân và bốn XCOL_c, chia sẻ wordline theo hàng còn bitline theo cột; trả netlist core4×4 và phục vụ kiểm16 leaf/128 NFET.')
task('edu_model_of','Tách tên model của một instance SPICE ở ngay trước các tham số có dấu =; giữ đúng tên subcircuit/primitive để bộ đếm đệ quy đi tiếp.')
task('edu_inventory','Đệ quy qua hierarchy, cộng số model nguyên thủy của từng instance, chặn vòng lặp; trả Counter NFET/PFET/MIM của leaf/cột/core/acquisition/conditioner.')
task('edu_leaf_dc','Tự sinh9 bài bias trong cùng deck từ ba trọng số và ba dấu activation, nạp đúng model NFET TT/mismatch rồi chạy ngspice; parse dòng bitline, kiểm dấu/zero và ghi log/JSON thật.')
task('edu_tiled_projection','Nhận ACT_X2 dài32 và ternary32×4, tính8 partial4 hàng và hai phase2 hàng/lát, kiểm cộng không đổi rồi áp alpha×2^(E−128); trả output cùng các partial để so reference.')

# Same spelling, different behavior: these overrides are applied before TASKS.
OVERRIDES={
 ('native-inline-legacy_stage5','_write'):'Tạo thư mục cha và ghi payload dạng văn bản vào file đích, dùng cho script/config/view được Stage5 tự sinh; không mặc định mọi payload là JSON.',
 ('native-inline-adc_partition','power'):'Ánh xạ tên rail vdd/vpwr thành VPWR và vss/vgnd thành node0 cho testbench SPICE; trả None với tên không phải rail, không chạy kiểm power grid.',
 ('native-inline-geometry_common','_rc_audit.find'):'Tìm đại diện nhóm node trong cấu trúc union/find của mạng R/C, dùng để gom các node nối qua điện trở trước khi phát hiện đảo tụ không có đường R hữu hạn.',
 ('native-inline-fresh-pilot','measure_pair.run'):'Tạo và chạy một trong hai pattern của cặp so mức, stream stdout ngspice, giới hạn180s, yêu cầu đủ28 measurement rồi trả record có đường dẫn deck/log và oracle.',
 ('native-restored-archive-030','main'):'Điểm vào của recipe Stage5: đọc các view và receipt hiện có, kiểm file có nội dung và trạng thái rồi trình bày điều kiện triển khai vật lý.',
 ('native-restored-archive-078','summarize_point'):'Gom các job của một bộ corner/VDD/nhiệt độ, tính lại gap của các cặp worst-case và so với baseline để lập bảng smoke PVT.',
 ('native-restored-archive-042','summarize_point'):'Với cùng cặp pattern và một load_ff/pwm_unit_ps, tính gap điện áp, mức zero và thứ tự đọc; trả hàng điều kiện cho sweep schematic.',
}

RUN_CELLS={
 'native-restored-archive-036':'quét độ bao phủ PEX và các case MHA đã chọn',
 'native-restored-archive-039':'đo có mục tiêu cặp tổng bị đảo trên schematic và PEX',
 'native-restored-archive-042':'quét tải/PWM trên schematic của cặp pattern khó',
 'native-restored-archive-045':'kiểm lại các candidate tải/PWM trên PEX',
 'native-restored-archive-048':'quét đầy đủ pattern tại candidate đã được đo/chọn',
 'native-restored-archive-051':'đo các MHA holdout mới với candidate/fit cố định',
 'native-restored-archive-057':'fit scalar decoder từ training và chấm holdout đã đo',
 'native-restored-archive-060':'mở rộng calibration tới các tổng reachable rồi kiểm feature',
 'native-restored-archive-063':'đo holdout mới sau khi xác nhận expanded calibration',
 'native-restored-archive-066':'so các family feature decoding bằng report training/query',
 'native-restored-archive-069':'thử cách đọc2+2 cho các case khó đã chọn',
 'native-restored-archive-078':'smoke PVT trên các pattern quyết định gap nhỏ nhất',
 'native-restored-archive-085':'biên dịch/chạy Icarus regression controller theo oracle fixed-point',
 'native-restored-archive-088':'chạy các kịch bản reset, stall và backpressure RTL',
 'native-restored-archive-091':'kiểm controller và phép cộng partial-sum của protocol2+2',
 'native-restored-archive-095':'triển khai hoặc audit top OpenLane gắn với hard macro',
}

def function_records(source):
    cleaned='\n'.join('# IPython magic' if line.lstrip().startswith(('%','!')) else line for line in source.splitlines())
    root=ast.parse(cleaned)
    result=[]
    def visit(nodes,prefix=''):
        for node in nodes:
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                result.append((prefix+node.name,node))
                visit(node.body,prefix+node.name+'.')
            elif isinstance(node,ast.ClassDef):visit(node.body,prefix+node.name+'.')
            else:
                for field in ('body','orelse','finalbody'):
                    body=getattr(node,field,None)
                    if isinstance(body,list):visit(body,prefix)
                for handler in getattr(node,'handlers',[]):visit(handler.body,prefix)
    visit(root.body)
    return result

def function_task(cell_id,fullname,node):
    key=(cell_id,fullname)
    if key in OVERRIDES:return OVERRIDES[key]
    if fullname=='run' and cell_id in RUN_CELLS:
        if cell_id in ('native-restored-archive-057','native-restored-archive-066'):
            return 'Đọc các report đã đo để '+RUN_CELLS[cell_id]+', tính lại nhãn/sai số và ghi JSON phân tích; hàm này không khởi chạy một mô phỏng transistor mới.'
        if cell_id in ('native-restored-archive-085','native-restored-archive-088','native-restored-archive-091'):
            return 'Điều phối '+RUN_CELLS[cell_id]+': tạo vector/testbench, chạy iverilog/vvp trong timeout, kiểm assertion rồi lưu log và report regression.'
        return ('Điều phối '+RUN_CELLS[cell_id]+': kiểm nguồn/config, tạo jobs và tùy execute chạy tool, '
                'áp timeout/kiểm measurement trước khi ghi report. Kết quả thuộc đúng chiến dịch được chỉ định bởi root/tag của hàm.')
    if fullname=='inspect' and cell_id=='native-restored-archive-054':
        return 'Đọc specification và các report baseline/candidate, phân loại điều kiện đã đạt, thiếu hoặc chưa có phép đo; trả bản inspect để không lẫn prototype với signoff.'
    if fullname=='inspect' and cell_id=='native-restored-archive-095':
        return 'Kiểm pin/size của LEF, hierarchy GDS, blackbox/RTL và sự có mặt OpenLane; trả thông tin gắn macro thật vào top trước khi chạy hoặc audit implementation.'
    for name in (fullname,fullname.split('.')[-1]):
        if name in TASKS:return TASKS[name]
    raise KeyError('Thiếu giải thích hàm '+cell_id+':'+fullname)

# Token; full name / explanation. Matched locally, never a global glossary dump.
GLOSSARY={
 'CIM':'Compute-In-Memory: tính toán tại/gần mảng nhớ; ở prototype này các nhánh transistor tích lũy tín hiệu theo activation và trọng số ternary.',
 'AutoMX':'Tên dự án AutoMX-CIM, nối hợp đồng MXFP4/ternary với macro SKY130, SAR và bài kiểm MHA.',
 'MXFP4':'Microscaling FP4: block32 phần tử E2M1 dùng chung một scale E8M0; không đồng nhất nibble floating-point với số nguyên4 bit.',
 'E2M1':'Định dạng gồm1 bit dấu,2 bit exponent và1 bit fraction; độ lớn ở scale1 là0,0.5,1,1.5,2,3,4,6.',
 'E8M0':'Scale8 bit không dấu/fraction; byte hữu hạn E biểu diễn2^(E−127), byte255 là NaN.',
 'ACT_X2':'Activation E2M1 đã có dấu và nhân2, thuộc0,±1,±2,±3,±4,±6,±8,±12; giao diện RTL dùng lane signed5 bit.',
 'QTEA':'Tên hợp đồng lượng tử trọng số trong source dự án: ternary kèm alpha/beta, col_v và residual tùy payload; adapter đổi trục về K×M. Không suy một cách khai triển chữ viết tắt ngoài source.',
 'MHA':'Multi-Head Attention: attention nhiều head; Q/K/V và output projection là các phép chiếu được kiểm bằng đường CIM.',
 'Q':'Query: tensor truy vấn của attention, được tạo từ X và trọng số W_Q.',
 'K':'Key trong biểu thức attention; khi dùng làm kích thước K thì là trục reduction/input của ma trận trọng số. Ngữ cảnh/shape phân biệt hai cách dùng.',
 'V':'Value trong attention; V khi gắn sau một số điện áp là đơn vị volt, cần đọc theo ngữ cảnh.',
 'O':'Output projection: phép chiếu sau khi ghép các head attention, không phải cổng analog của leaf.',
 'ADC':'Analog-to-Digital Converter: đổi điện áp analog thành mã số; ở đây nhận tín hiệu vi sai sau đường lấy mẫu/mux.',
 'SAR':'Successive Approximation Register: thuật toán/logic ADC lần lượt thử quyết định theo comparator để tạo mã.',
 'DAC':'Digital-to-Analog Converter: tạo mức analog từ điều khiển số; bên trong SAR dùng để tạo điện áp thử.',
 'CDAC':'Capacitive DAC: mạng tụ của SAR; partition giữ inventory tụ nguồn và dùng điều khiển bottom-plate tương ứng.',
 'EOC':'End Of Conversion: tín hiệu ADC báo hoàn tất; consumer kiểm EOC thay vì tự gán mã theo oracle.',
 'OSR':'Oversampling Ratio: chế độ/lượt lấy mẫu tăng cường của ADC nguồn; EOC_OSR là cổng hoàn tất tương ứng trong SAR IP.',
 'TG':'Transmission Gate: NMOS và PMOS điều khiển bổ sung để truyền điện áp analog ở đường sample hoặc mux.',
 'MOS':'Metal-Oxide-Semiconductor transistor: thiết bị4 cực drain/gate/source/bulk, viết D/G/S/B trong SPICE.',
 'NMOS':'MOS kênh n; trong leaf, hai NMOS nối tiếp tạo một nhánh xả có điều kiện.',
 'NFET':'N-channel Field-Effect Transistor: tên thiết bị kênh n trong model SKY130, tương ứng NMOS ở sơ đồ.',
 'PMOS':'MOS kênh p; dùng cho precharge hoặc cùng NMOS tạo transmission gate trong ngoại vi.',
 'PFET':'P-channel Field-Effect Transistor: tên thiết bị kênh p trong model SKY130.',
 'MIM':'Metal-Insulator-Metal capacitor: tụ kim loại–điện môi–kim loại dùng cho hold hoặc tải bitline vật lý.',
 'SRAM':'Static Random-Access Memory: ô lưu bằng latch; leaf8 NMOS của bài này là phần tử compute, trọng số của nó do register controller cấp.',
 'RRAM':'Resistive Random-Access Memory: bộ nhớ dựa trên trạng thái điện trở; không phải thiết bị lưu trọng số của leaf đang vẽ.',
 'DGSB':'Drain/Gate/Source/Bulk: thứ tự bốn đầu cực của instance MOS trong SPICE; bulk không được mặc định nối source trên sơ đồ4 cực.',
 'WPOS':'Weight positive: bit điều khiển trọng số+1; dùng cùng WNEG để mã hóa ternary, 10→+1,01→−1,00→0.',
 'WNEG':'Weight negative: bit điều khiển trọng số−1; mã11 bị giao thức cấu hình loại.',
 'WLP':'Wordline positive: xung PWM cho activation dương, dùng chung theo hàng.',
 'WLN':'Wordline negative: xung PWM cho activation âm, dùng chung theo hàng.',
 'BLP':'Bitline positive: đường bit xả khi tích trọng số×activation dương; khi nó giảm, V(BLN)−V(BLP) tăng.',
 'BLN':'Bitline negative: đường bit xả khi tích âm; khi nó giảm, điện áp vi sai quy ước âm.',
 'HP':'Hold positive: node lấy mẫu/giữ điện áp từ phía BLP của một cột.',
 'HN':'Hold negative: node lấy mẫu/giữ điện áp từ phía BLN của một cột.',
 'AINP':'Analog Input Positive: chân input analog phía P của ADC sau conditioner/mux.',
 'AINN':'Analog Input Negative: chân input analog phía N của ADC sau conditioner/mux.',
 'CTOP':'Common top plate của mảng tụ SAR; phía P/N được ký hiệu CTOPP/CTOPN trong co-simulation.',
 'VPWR':'Tên rail nguồn dương của top/macro; bài thử thường dùng1.8V.',
 'VGND':'Tên rail ground của mạch; không đồng nhất việc tên node tồn tại với đã nối đủ power grid.',
 'VSUBS':'Node bulk/substrate của các NMOS trong schematic leaf; fixture có thể nối nó về ground nhưng sơ đồ vẫn chỉ rõ cực B.',
 'VDD':'Tên nguồn dương trong IP/testbench; helper mapping thường chuyển về VPWR.',
 'VSS':'Tên ground trong IP; helper SPICE ánh xạ về node0.',
 'VCM':'Common-mode Voltage: mức điện áp trung bình của cặp analog vi sai.',
 'PRE_B':'Precharge điều khiển active-low: mức0 mở PMOS nạp bitline, mức1 nhả nạp để compute.',
 'TRACK':'Điều khiển nối đường bit sang tụ hold lúc lấy mẫu; ngắt sau đó giữ điện áp cho ADC.',
 'PWM':'Pulse-Width Modulation: độ rộng xung mang độ lớn activation; gate vẫn dùng hai mức logic, không đổi biên độ theo magnitude.',
 'TT':'Typical–Typical: corner model MOS điển hình của PDK, không tự đại diện cho mọi điện áp/nhiệt độ.',
 'SS':'Slow–Slow: corner transistor chậm trong bộ model PDK.',
 'FF':'Fast–Fast: corner transistor nhanh; khác với ký hiệu fF của điện dung.',
 'PVT':'Process/Voltage/Temperature: điều kiện công nghệ, nguồn và nhiệt độ của phép mô phỏng.',
 'DC':'Direct Current/operating point: bài toán điểm làm việc tĩnh, dùng kiểm dấu dòng leaf, không phải phép đo PWM theo thời gian.',
 'AC':'Small-signal alternating-current analysis: phân tích tín hiệu nhỏ quanh điểm làm việc; không thay transient trong phép đọc CIM.',
 'UIC':'Use Initial Conditions: tùy chọn bỏ giải operating point; recipe tránh dùng nó tùy tiện vì có thể tạo offset do trạng thái tụ PEX.',
 'R/C':'Resistance/Capacitance: điện trở/điện dung ký sinh; dùng để xem đường nối vật lý làm đổi transfer và timing ra sao.',
 'SKY130':'Bộ tiến trình/PDK130nm open-source được dùng cho thiết bị và standard cell trong dự án.',
 'sky130A':'Tên biến thể PDK đang nằm trong bundle, có tech file và model riêng cho analog/digital flow.',
 'PDK':'Process Design Kit: model thiết bị, lớp hình học, rule và thư viện gắn với một tiến trình chế tạo.',
 'SPICE':'Simulation Program with Integrated Circuit Emphasis: dạng netlist/analysis cho mô phỏng mạch; X là instance subcircuit, không tự là một MOS primitive.',
 'ngspice':'Simulator SPICE open-source; CLI chạy deck, còn shared library cho phép Python điều khiển simulator theo pha.',
 'BSIM':'Berkeley Short-channel IGFET Model: họ model transistor dùng bên trong model NFET/PFET của PDK.',
 'RTL':'Register-Transfer Level: mô tả thanh ghi/logic bằng Verilog/SystemVerilog, được kiểm với Icarus và tổng hợp bằng Yosys.',
 'EDA':'Electronic Design Automation: nhóm công cụ tự động thiết kế/kiểm mạch, gồm synthesis, layout, extraction và timing.',
 'GDS':'GDSII: định dạng hình học layout phân cấp; ảnh render đọc từ file này, còn netlist mô tả kết nối logic/thiết bị.',
 'GDSII':'Graphic Data System II: định dạng layout chứa cell, hình và instance; tên GDS trong notebook dùng cùng nghĩa.',
 'LEF':'Library Exchange Format: abstract outline, pin và obstruction của macro/standard-cell cho placer/router.',
 'DEF':'Design Exchange Format: placement, pin và routing của thiết kế top, gắn với các master từ LEF.',
 'ODB':'OpenDB database: cơ sở dữ liệu vật lý của OpenROAD, giữ instance/net/route mà các bước export/PG/RCX đang đọc.',
 'DRC':'Design Rule Check: kiểm hình học theo rule tiến trình; số violation của router và full-layout DRC được báo riêng.',
 'LVS':'Layout Versus Schematic: so kết nối mạch trích xuất với netlist tham chiếu trong scope đã chọn.',
 'PEX':'Parasitic Extraction: trích điện trở/điện dung từ layout rồi đưa vào mô phỏng sau layout.',
 'PG':'Power/Ground: các terminal và rail nguồn/ground; kiểm tín hiệu bỏ PG standard-cell không thay kiểm grid nguồn riêng.',
 'PDN':'Power Distribution Network: lưới phân phối nguồn gồm rail, strap, ring và via nối đến pin macro/cell.',
 'PnR':'Place and Route: đặt cell rồi nối dây; cold PnR bắt đầu từ RTL/macro input, không mở lại routed top cũ.',
 'CTS':'Clock Tree Synthesis: chèn/cân bằng mạng phân phối clock trước routing chi tiết.',
 'RCX':'RC extraction: bước trích mạng điện trở/điện dung của routed design bằng OpenRCX.',
 'STA':'Static Timing Analysis: phân tích setup/hold theo clock và các ràng buộc SDC, không phải mô phỏng transistor.',
 'SDC':'Synopsys Design Constraints: file khai báo clock và các ràng buộc thời gian/interface cho STA.',
 'SPEF':'Standard Parasitic Exchange Format: file mạng R/C của thiết kế đã route để STA đọc lại.',
 'ETM':'Extracted Timing Model: mô hình thời gian ở biên khối, xuất thành Liberty từ timing đã trích parasitic.',
 'Liberty':'Định dạng .lib mô tả pin, clock và cung timing của cell/khối; khác thư viện model SPICE .lib.',
 'LUT':'Look-Up Table: bảng ngưỡng/giá trị đọc theo address; trong controller2+2 có304 threshold12-bit.',
 'IP':'Intellectual Property block: khối mạch/RTL được tích hợp lại, ở đây gồm hard-macro core/conditioner/ADC và SAR nguồn.',
 'API':'Application Programming Interface: các hàm giao tiếp để Python gọi ngspice shared library hoặc điều khiển module khác.',
 'CLI':'Command-Line Interface: gọi executable bằng argv và nhận return code/stdout/stderr.',
 'PID':'Process ID: mã process hệ điều hành để theo dõi hoặc dừng đúng job của phiên.',
 'KLayout':'Công cụ layout open-source đọc/ghi GDS, chạy script/rule và render PNG/SVG theo top cell.',
 'OpenLane':'Flow điều phối Yosys/OpenROAD/Magic/KLayout cùng config/PDK để triển khai top số gắn macro.',
 'OpenROAD':'Công cụ triển khai vật lý dùng OpenDB; thực hiện floorplan, PDN, placement, CTS, routing, PG và timing theo script.',
 'OpenRCX':'Bộ trích parasitic R/C trong OpenROAD, tạo SPEF từ routed database và rule công nghệ.',
 'OpenSTA':'Timing engine đọc Liberty/SDC/SPEF, báo setup/hold và kiểm file timing model.',
 'Yosys':'Công cụ synthesis RTL open-source, dùng Liberty để ánh xạ logic sang standard cells SKY130.',
 'Magic':'Công cụ layout/extraction; trong tuyến đang dùng nó đọc DEF/LEF để tạo netlist vật lý cho LVS.',
 'Netgen':'Công cụ so netlist cho LVS; phải đọc verdict cuối, return code0 không tự chứng minh match.',
 'Icarus':'Icarus Verilog: compiler iverilog cùng runtime vvp dùng mô phỏng SAR/controller RTL.',
 'vvp':'Runtime của Icarus chạy testbench đã compile; stdin/stdout mang decision và STATE trong co-simulation.',
 'Docker':'Runtime container giữ tool image; lệnh standalone chỉ mount bundle để tool không cần checkout cũ.',
 'Tcl':'Tool Command Language: ngôn ngữ script điều khiển OpenROAD/Magic/Netgen trong các lệnh tool.',
 'Python':'Ngôn ngữ điều phối, parse measurement và xây oracle/figure của notebook; không thay phương trình thiết bị SPICE.',
 'NumPy':'Thư viện mảng số Python; shape/dtype xác định cách xếp activation, trọng số và tensor MHA.',
 'Matplotlib':'Thư viện figure của Python, dùng vẽ topology, bảng dấu và các đường số đo trong bài học.',
 'IPython':'Kernel/magic của notebook; các magic tạo namespace/module riêng để các chương ghép được mà không đè biến.',
 'Volare':'Công cụ/cấu trúc cài đặt phiên bản PDK mà các recipe tìm model có hỗ trợ.',
 'Ciel':'Cấu trúc quản lý PDK được helper discovery hỗ trợ; không phải thêm một model công nghệ khác.',
 'JSON':'JavaScript Object Notation: file lưu stimulus, summary, config và manifest theo key/value.',
 'XML':'Extensible Markup Language: dạng report DRC được parser KLayout/checker đọc.',
 'CSV':'Comma-Separated Values: bảng văn bản dùng trong một số report/metrics tool.',
 'PNG':'Ảnh raster được kiểm chữ ký và nhúng vào output notebook sau render.',
 'SVG':'Scalable Vector Graphics: ảnh vector giữ nét/chữ khi phóng to hoặc đưa vào paper.',
 'ASCII':'Mã văn bản; raw ASCII ngspice có header/biến/sample để parser đọc trực tiếp.',
 'SHA':'Secure Hash Algorithm: dấu kiểm nội dung file, chỉ dùng xác nhận nguồn/receipt, không phải thước đo chất lượng mạch.',
 'SHA256':'SHA-256: thuật toán dấu kiểm256-bit dùng trong artifact references; không dùng làm số đo điện hay thay verdict tool.',
 'L2':'Euclidean norm: chuẩn căn tổng bình phương; relative L2 lấy chuẩn sai lệch chia chuẩn reference.',
 'FP32':'Floating-point32-bit: tên reference số gốc; phép tính Python trong source có thể dùng float64 để giảm nhiễu đánh giá.',
 'Q12':'Fixed-point với12 bit phần lẻ ở hệ số, ví dụ alpha_q12 cần đổi thang tương ứng khi khôi phục output.',
 'NaN':'Not a Number: giá trị không phải số hữu hạn; bộ kiểm loại nó trước khi fit/chấm measurement.',
 'Inf':'Infinity: giá trị vô hạn, không được chấp nhận làm số đo/activation hữu hạn ở các checker này.',
 'baseline':'Điều kiện mạch/lần đo gốc để so can thiệp, ở pilot là200fF/100ps.',
 'candidate':'Điểm tải/PWM được chọn sau phép so có kiểm soát, không phải tên một transistor hoặc code ADC.',
 'calibration':'Tập đo để fit hệ số/ngưỡng của decoder; fit được cố định trước khi dùng holdout.',
 'holdout':'Tập pattern chưa dùng để chọn fit/ngưỡng, dành cho đánh giá độc lập.',
 'oracle':'Kết quả chuẩn tính lại từ stimulus số, độc lập với giá trị ngspice hay mã ADC cần chấm.',
 'payload':'Nội dung input của một case: activation, weights, column cùng các trường giao thức cần thiết.',
 'receipt':'Bản ghi một bước tool/measurement có input, lệnh, trạng thái, log và output để consumer kiểm lại nguồn.',
 'manifest':'Danh mục cấu hình, job hoặc artifact liên kết các bước; không tự là measurement.',
 'namespace':'Vùng tên biến/hàm riêng của module; dùng tách lesson, review và native implementation trong cùng kernel.',
 'callback':'Hàm được engine gọi ngược khi cần log/nguồn điện áp hoặc thông báo process, thay vì chỉ được gọi trực tiếp từ cell.',
 'transient':'Mô phỏng theo thời gian để xem PWM, nạp/xả, track/hold và quyết định SAR.',
 'precharge':'Pha nạp bitline về mức ban đầu trước khi các nhánh compute xả điện tích.',
 'wordline':'Dây điều khiển theo hàng; WLP/WLN mang PWM activation trong core.',
 'bitline':'Dây theo cột thu dòng/điện tích từ nhiều leaf; BLP/BLN tạo output vi sai.',
 'leaf':'Cell nhỏ nhất ở hierarchy compute của bài này, gồm8 NMOS/bốn nhánh2T.',
 'macro':'Khối vật lý có outline/pin/view riêng, được top đặt và route quanh như một hard IP.',
 'tile':'Lát phép chiếu dùng lại tài nguyên core; tile logic32×8 và core vật lý4×4 là hai cấp khác nhau.',
 'core':'Mảng compute4×4 hoặc top lõi theo tên đối tượng cụ thể; phải phân biệt core trần với core+acquisition.',
 'softmax':'Chuẩn hóa các score attention bằng hàm mũ và tổng theo trục, thực hiện ở phần số của study.',
 'comparator':'Mạch so điện áp hai phía, quyết định của nó được SAR dùng để thử bit/mã tiếp theo.',
 'common-mode':'Điện áp trung bình của hai node vi sai; khác với điện áp chênh lệch dùng biểu diễn tích/tổng.',
 'setup':'Điều kiện tín hiệu đến trước cạnh clock đủ thời gian; setup slack âm biểu thị chưa đạt tại clock đang ràng buộc.',
 'hold':'Trong STA là điều kiện giữ dữ liệu sau cạnh clock; trong analog sample/hold là pha cô lập tụ để giữ điện áp. Hai nghĩa đọc theo khối đang xét.',
 'floorplan':'Đặt kích thước die/core, IO và vị trí macro trước placement chi tiết.',
 'placement':'Sắp vị trí các instance sao cho hợp lệ hình học và có thể route.',
 'routing':'Vẽ dây/via cho các net giữa pin/cell sau placement và CTS.',
 'poly':'Lớp polysilicon tạo gate khi cắt vùng active trong hình minh họa cấu trúc NMOS.',
 'active':'Ở hình transistor là vùng bán dẫn chứa source/drain/kênh; ở parser, biến active giữ tên subcircuit đang mở; ở pattern rows, active chỉ các hàng đang phát xung. Ngữ cảnh hình/cú pháp tách ba cách dùng.',
 'contact':'Điểm tiếp xúc đưa diffusion/poly/well-tap lên mạng kim loại; không phải giao cắt dây bất kỳ đều có contact.',
 'bulk':'Cực body/substrate B của MOS, được chỉ rõ VSUBS ở leaf để không ngầm nối sai với source.',
 'gate':'Cực G điều khiển kênh MOS qua lớp cách điện; dòng điều khiển không được hiểu là một dây nối tắt xuống kênh.',
 'drain':'Cực D của instance MOS theo thứ tự SPICE; trong nhánh compute nối về phía bitline/node trên.',
 'source':'Trong mô tả MOS là cực S; trong runner là input source file. Chữ ký và bảng chân D/G/S/B phân biệt hai nghĩa.',
}

GLOSSARY.update({
 '8T':'Eight transistors: leaf compute có8 NMOS chia thành4 nhánh2 MOS; không có nghĩa cell này là một SRAM8T chứa latch.',
 '2T':'Two transistors: trong mỗi nhánh leaf,2 NMOS nối tiếp lần lượt nhận gate trọng số và gate activation.',
 'C':'Ở module co-simulation, C là alias của ctypes để gọi API C; trong netlist SPICE, tên instance bắt đầu bằng C biểu diễn tụ.',
 'fF':'Femtofarad =10^−15F, đơn vị load_ff/tụ; phân biệt chữ hoa với corner FF (Fast–Fast).',
 'ps':'Picosecond =10^−12s, đơn vị độ rộng PWM hoặc cạnh trong deck testbench.',
 'ns':'Nanosecond =10^−9s, dùng cho sample time và setup/hold slack được in từ STA.',
 'µm':'Micrometre =10^−6m, đơn vị W/L và hình học LEF/layout.',
 'mV':'Millivolt =10^−3V, thường dùng hiển thị gap hoặc điện áp vi sai nhỏ.',
 'µA':'Microampere =10^−6A, đơn vị biểu đồ dòng bitline DC của leaf.',
 'MHz':'Megahertz =10^6 chu kỳ/s; target25MHz tương ứng chu kỳ clock40ns trong STA prototype.',
 'rne':'Round to Nearest, ties to Even: làm tròn về mức gần nhất và chọn mã có bit thấp chẵn khi đúng giữa hai mức; khác tie=project chọn độ lớn thấp hơn.',
 'np':'Tên viết gọn của module NumPy trong code; np.array/asarray tạo mảng, các toán tử @ và reduction tính oracle trên mảng.',
 'plt':'Tên viết gọn của matplotlib.pyplot, dùng tạo figure/axes, lưu SVG/PDF/PNG và đóng hình sau hiển thị.',
 'pya':'Python API của KLayout; Layout/Cell/Layer/Region của pya đọc hoặc xử lý hình học GDS trong script batch.',
 'subprocess':'Module Python tạo process hệ điều hành, truyền argv/stdin/env và nhận return code/stdout/stderr của tool.',
 'ctypes':'Thư viện Python gọi hàm C và mô tả struct/con trỏ/callback của shared libngspice.',
 're':'Module regular expressions của Python, dùng tách measurement, chân, marker log hoặc tên tín hiệu theo mẫu.',
 'hashlib':'Module Python tính dấu kiểm nội dung file/input để nhận biết dữ liệu đã thay đổi.',
 'stdout':'Standard Output: luồng output chuẩn của tool hoặc cell; native log giữ nội dung luồng này.',
 'stderr':'Standard Error: luồng báo lỗi của process; runner thường gộp vào stdout để transcript giữ đúng thông báo tool.',
 'stdin':'Standard Input: luồng input của process; co-simulation gửi quyết định comparator vào vvp qua đây.',
 'portable':'Tên module runtime automx_standalone được khai báo từ chính cell standalone-runtime, không phải một tool EDA mới.',
 'MHAResult':'Đối tượng kết quả attention số, giữ các tensor Q/K/V/context/output để các phép kiểm cùng dùng đúng mapping.',
 'Mapping':'Kiểu dữ liệu ánh xạ key→value trong annotation Python, ví dụ tên projection→payload trọng số.',
 'Iterable':'Kiểu annotation cho một tập có thể duyệt từng phần tử, ví dụ danh sách level hoặc command của lịch.',
 'Sequence':'Kiểu annotation cho dãy có thứ tự, dùng khi thứ tự chân/vector/lệnh cần được giữ nguyên.',
 'CMOS':'Complementary MOS: logic/mạch phối hợp transistor kênh n và kênh p, được dùng trong bộ lái/decoder của ADC nguồn.',
 'D':'Drain: cực nối về phía bitline của transistor phía trên hoặc node giữa của transistor phía dưới trong leaf.',
 'G':'Gate: cực điều khiển WPOS/WNEG hoặc WLP/WLN, cách điện với kênh.',
 'S':'Source: cực về node giữa hoặc VGND theo thứ tự D/G/S/B của instance đang xét.',
 'B':'Bulk/body: cực nền của NMOS, mang node VSUBS riêng ở schematic leaf.',
 'W':'Channel width: bề rộng kênh, model leaf đặt0.84µm; hình minh họa thiết bị không theo tỉ lệ.',
 'L':'Channel length: chiều dài kênh dưới gate, model leaf đặt0.15µm.',
 'VGS':'Gate-to-Source Voltage: hiệu điện thế V(G)−V(S), điều khiển việc hình thành kênh NMOS.',
 'PP':'Nhánh tích(+weight,+activation), xả BLP; tên instance tương ứng XPP_W/XPP_A.',
 'PN':'Nhánh tích(−weight,−activation), xả BLP trong topology của cell; thứ tự tag là quy ước tên của source.',
 'NP':'Nhánh tích(−weight,+activation), xả BLN trong topology của cell.',
 'NN':'Nhánh tích(+weight,−activation), xả BLN trong topology của cell.',
 'NPP':'Node nối giữa hai NMOS XPP_W và XPP_A; không phải một rail nguồn.',
 'NPN':'Node nối giữa hai NMOS nhánh PN; đây là tên node, không phải ký hiệu transistor bipolar NPN.',
 'NNP':'Node nối giữa hai NMOS nhánh NP của leaf.',
 'NNN':'Node nối giữa hai NMOS nhánh NN của leaf.',
 'M4':'Lớp kim loại met4 của SKY130; pad VGND được nối qua via lên met5 trong PDN của wrapper.',
 'M5':'Lớp kim loại met5 của SKY130; dùng cho strap/bridge nguồn ở cấp top.',
 'met4':'Tên layer database của kim loại4 trong PDK SKY130, dùng khi kiểm pin/strap của macro.',
 'met5':'Tên layer database của kim loại5 trong PDK SKY130, dùng khi kiểm bridge/via của power grid.',
 'sky130_fd_pr__nfet_01v8':'Model primitive NFET1.8V của SKY130, bốn đầu D/G/S/B, tham số W/L tính theo geometric scale của deck.',
 'sky130_fd_pr__pfet_01v8':'Model primitive PFET1.8V của SKY130, dùng cho precharge và nửa PMOS của transmission gate.',
 'sky130_fd_pr__cap_mim_m3_1':'Model tụ MIM của SKY130 mà acquisition/conditioner nguồn sử dụng; inventory đếm phần tử model, không gán mọi tụ cùng điện dung bằng suy đoán.',
 'Sky130MHAConfig':'Đối tượng cấu hình của dự án: hình dạng tiny-MHA/tile, thông số số học và điều kiện mạch SKY130 dùng để sinh cùng một bài kiểm ở nhiều stage.',
 'TinyMHAWeights':'Lớp chứa các ma trận trọng số Q/K/V/O, kiểm shape ngay khi khởi tạo và cung cấp mapping theo projection.',
 'QTEAProjection':'Payload projection theo trục K×M: ternary, hệ số alpha/beta theo nhóm, col_v theo input và residual tùy chọn.',
 'CIMMacroModel':'Surrogate số của macro từ characterization TT; dùng fit điện áp đã đo để ước lượng output và đếm các trường hợp ngoài miền characterization.',
 'Stage1Result':'Đối tượng chứa tensor và các metric của reference tiny-MHA Stage1 để schedule/characterization dùng lại cùng bài toán.',
 'TileCommand':'Bản mô tả một lệnh tile: projection, token, tile output, ID và các phụ thuộc của lịch thực thi.',
 'Stage4Artifact':'Bản mô tả netlist, testbench, measurement và jobs của một cấp cell/cột/macro trong generator Stage4.',
 'Flow':'Đối tượng chạy tool của notebook: giữ root/base/work, settings, receipts và outputs của một phiên.',
 'Settings':'Cấu hình runner gồm root, cache, tag, reuse, timeout và số worker; khác thông số thiết bị trong PDK.',
 'Case':'Một pattern vật lý gồm tên, activation ACT_X2 và ma trận ternary; phương thức sums tính oracle từng cột.',
 'Experiment':'Đối tượng quản lý các conversion SAR, calibration keys, record references và phép ghép projection/MHA trong phiên hiện tại.',
 'SharedSpice':'Lớp bọc shared libngspice, giữ callback và lịch nguồn điện áp để co-simulation đi cùng RTL theo từng pha.',
 'Vector':'Cấu trúc ctypes mô tả vector C của ngspice: tên, kiểu, cờ, con trỏ data và độ dài; phải sao về NumPy trước khi dùng lâu dài.',
 'Path':'Lớp pathlib.Path của Python, dùng ghép/chuẩn hóa đường dẫn file thay vì coi đường dẫn là một node điện.',
 'Counter':'Bộ đếm theo key của Python; ở inventory nó cộng số instance của từng model thiết bị.',
 'Timer':'Bộ hẹn giờ của Python; callback của nó dừng một process mô phỏng khi hết ngân sách thời gian.',
 'Event':'Cờ đồng bộ giữa luồng runner và timer để phân biệt process lỗi với bị dừng do timeout.',
 'ThreadPoolExecutor':'Bộ quản lý worker luồng Python cho các job độc lập; số worker được giới hạn để không làm quá tải simulator/tool.',
 'ctypes':'Thư viện giao tiếp C của Python, khai báo con trỏ/callback/struct để gọi shared libngspice.',
 'callback':'Hàm engine gọi ngược để lấy điện áp nguồn hoặc ghi thông báo; các callback phải giữ lifetime khi C còn dùng.',
 'alpha':'Hệ số nhân của nhóm trọng số/projection; áp dụng ở hợp đồng số sau khi có tổng nguyên, không thay bằng biên độ gate.',
 'beta':'Hệ số hiệu chỉnh affine của payload QTEA; thuộc reference/correction path, không phải bit WPOS/WNEG.',
 'col_v':'Vector hệ số theo trục input K của payload QTEA, dùng trong phép khôi phục projection tổng quát.',
 'residual':'Phần hiệu chỉnh trọng số ngoài ternary-base; study base-only hoặc bài học chọn nó bằng0 theo hợp đồng đã nêu.',
 'gate oxide':'Lớp cách điện dưới gate trong hình cắt khái niệm; gate không tiếp xúc điện trực tiếp với kênh.',
 'D/G/S/B':'Drain/Gate/Source/Bulk: bốn cực của NMOS trong sơ đồ phóng to và thứ tự đầu cực trong SPICE.',
 'W/L':'Width/Length: bề rộng/bề dài kênh, ở leaf là0.84/0.15µm theo source; hình phóng to không vẽ đúng tỉ lệ các lớp.',
 'ROOT':'Biến đường dẫn gốc source bundle trong native flow; helper ghép đường dẫn RTL/PDK/input tương đối từ đây.',
 'WORK':'Thư mục artifact của phiên native hiện tại, chứa cold_pnr, conversion, timing, extraction và render.',
 'BASE':'Ở review là thư mục evidence JSON/hình của lượt chạy; trong recipe cũ có thể là tiền tố cây report. Namespace giữ hai nghĩa tách biệt.',
 'OUT':'Thư mục kết quả review của lượt mới; figure và JSON phân tích được ghi ở đây.',
 'EDU_ROOT':'Root bundle dùng riêng trong bài học cell→macro, trỏ đến inputs và PDK nguồn đi kèm.',
 'EDU_OUT':'Thư mục cell_to_macro của lượt chạy hoặc subset validation; lưu SPICE, hình và log của bài học.',
 'EDU_LEAF':'Chuỗi SPICE leaf8T do bài học tự sinh và đã so topology với schematic nguồn.',
 'EDU_SOURCE':'Mapping tên subcircuit → các dòng SPICE đã parse từ core_acquisition.spice.',
 'EDU_BRANCHES':'Bảng bốn nhánh PP/PN/NP/NN, chứa bitline, gate trọng số, gate activation và node giữa để dùng chung khi sinh netlist và vẽ sơ đồ.',
 'EDU_COLUMN':'Chuỗi SPICE cột4×1 được sinh từ interface leaf, trước khi ghép vào core.',
 'EDU_CORE':'Chuỗi SPICE core4×4 gồm bốn cột và50 chân được đối chiếu với source.',
 'EDU_HIER':'Mapping hierarchy core/acquisition/conditioner dùng cho phép đếm đệ quy linh kiện của bài học.',
 'EDU_MAG':'Bảng tám độ lớn E2M1 dùng tại scale1 trong decoder/bộ lượng tử minh họa.',
 'EDU_ALPHABET':'Tập15 giá trị ACT_X2 có dấu mà các bài kiểm logic và tiling được phép nhận.',
 'EDU_LEAF_MEASURED':'Danh sách9 trạng thái bias DC với dòng vi sai đọc từ transcript ngspice thật của leaf.',
 'INLINE_SOURCES':'Sổ source các module khai báo trực tiếp trong notebook, dùng để truy lại nội dung thực thi của từng helper.',
 'RTL_FIELDS':'Thứ tự trường STATE giữa Icarus và Python, gồm sample, result, EOC và các bit điều khiển CDAC.',
 'EVIDENCE':'Cấu trúc story gom các số đo/quan hệ dữ liệu đã kiểm để trình bày quá trình thiết kế.',
 'FROZEN':'Cặp slope/offset đã được fit từ calibration và giữ nguyên khi decode các case holdout.',
})

# Detailed input, output, next consumer; groups share an actual data contract.
IO={}
def contract(ids,received,produced,next_step):
    for cid in ids.split():IO[cid]=(received,produced,next_step)

contract('argument-bootstrap',
 'IPython truyền line là nhãn cell và cell là nguyên mã Python phía dưới magic. Không cần file waveform hay ADC code ở bước này.',
 'Tạo design_review và standalone_runtime magic, module riêng cho analysis/runtime; thay đổi bảng module trong kernel, chưa tạo kết quả mạch.',
 'standalone-runtime dùng magic để định nghĩa portable; setup và các cell %%design_review dùng vùng biến phân tích vừa tạo.')
contract('full-lab-config',
 'Đọc data/native_lab_cells.json để lấy thứ tự89 native code cells, data/native_lab_outputs.json để biết dữ liệu tham chiếu được giữ, và biến môi trường chế độ chạy.',
 'Tạo native_lab magic cùng _lab_state và nơi ghi kết quả native-lab. Mỗi cell được ghi ID để cuối flow kiểm không thiếu, lặp hoặc đổi thứ tự.',
 'Tất cả các cell %%native_lab; full-lab-inventory đối chiếu danh sách đã xử lý ở cuối notebook.')
contract('native-runall-config',
 'Lấy root từ AUTOMX_CIM_ROOT và thư mục OUT do setup tạo; xác định CACHE/TAG/WORK, các cờ chiến dịch cũ và nơi ghi script trong notebook_sources.',
 'Tạo module/eda_source magic và thư mục phiên trống, ghi fresh_start.json trước các phép đo, gọi portable.start để mở cold PnR nền.',
 'native-inline-support khởi tạo Flow; các cell native inline đăng ký module/script tại đây; synthesis chờ process cold flow này hoàn tất.')
contract('standalone-runtime',
 'root chứa standalone.json, inputs/{core,conditioner,adc}.{gds,lef}, RTL, tools và hai PDK. work là thư mục phiên; flow chứa settings/root/work/receipts/outputs. Các hàm export nhận namespace native và namespace review riêng.',
 'Ghi cold_pnr/design/config.json, native.log và step.json; xuất streamout/{top.gds,top.def,top.lef}, signal_lvs/netgen.log, power/power.json, timing/{SPEF,LIB,SDC}; export ghi review_data/evidence.json rồi publish ghi runall_manifest.json.',
 'native-runall-config gọi start; synthesis/streamout/GDS-audit/signal-lvs/power/timing gọi từng nhóm hàm. standalone-sync-* chuyển report sang validate-evidence, physical-reports và results.')
contract('setup',
 'Nhận thư mục bundle từ AUTOMX_BUNDLE_DIR hoặc working directory, giờ hiện tại để đặt tên lượt mới và chế độ native của review.',
 'Tạo OUT=runs/fresh_* và BASE=OUT/review_data, khởi tạo E, đặt định dạng figure; helper record trả JSON, table in bảng, savefig ghi ảnh trong OUT.',
 'standalone-prepare đọc BUNDLE/OUT; cim-edu-bootstrap tạo EDU_OUT; các cell factorial/ADC/MHA/physical review đọc E và dùng helper trình bày này.')
contract('native-inline-presentation',
 'Nhận dict/list/scalar của report và các tùy chọn in như thụt lề; giữ số đo và trạng thái lấy từ nguồn.',
 'Trả cấu trúc đã lọc trường định danh nội bộ hoặc in JSON/bảng dễ đọc; không sửa file report nguồn hay mã ADC.',
 'Các module history/story và cell recipe cũ gọi pretty để trình bày số đo sau khi đã được kiểm.')
contract('architecture',
 'Nhận tọa độ khối/mũi tên, nhãn đường activation/weight và màu; đây là dữ liệu vẽ kiến trúc, chưa phải measurement.',
 'Tạo figure mô tả chiều dữ liệu CIM → ADC → MHA, trong đó mỗi block/arrow là một primitive hình vẽ có vị trí xác định.',
 'Phần mạch cell→macro và các cell đo ADC/MHA dùng cùng tên giao diện để nối sơ đồ này với stimulus và record thực.')
contract('native-inline-history native-inline-story native-restored-archive-104',
 'Nhận root và đường dẫn report JSON, trường input của report con/cha hoặc file log; file thiếu/đổi nội dung phải được giữ thành trạng thái riêng.',
 'Trả số đo tóm tắt, trạng thái receipt, figure khoảng điện áp hoặc cạnh phụ thuộc parent→child đã đối chiếu với artifact thật.',
 'Các cell story-transfer_error/candidate/decoder/partition và phần dependencies dùng chúng để giải thích các quyết định; phép đo mới đi qua fresh-pilot/Experiment.')
contract('native-restored-archive-009',
 'Nhận working directory và cấu trúc thư mục có package/config/scripts, không nhận netlist hay kết quả mô phỏng.',
 'Trả một project root đã kiểm có các thành phần bắt buộc để import/source paths thống nhất.',
 'Các import của recipe số/circuit cũ dùng root này; standalone active lấy BUNDLE đã thiết lập ở setup.')
contract('native-inline-legacy_attention native-inline-attention',
 'X có shape token×d_model, bốn ma trận Q/K/V/O, số heads hoặc các tensor projection đã có; các payload lượng tử chứa ternary/hệ số nhóm. Kiểm shape và số hữu hạn trước tính.',
 'Trả Q/K/V, context, output MHA và metric giữa reference/candidate; hàm ghi Stage1 còn lưu tensor và JSON, không tự sinh waveform transistor.',
 'legacy_schedule lấy kích thước/projection; characterization/Experiment.mha và mha-recompute dùng reference để so với tổng được đọc qua macro/ADC.')
contract('native-inline-legacy_schedule',
 'Nhận Sky130MHAConfig, số token/head, tile K/M và yêu cầu projection Q/K/V/O.',
 'Trả danh sách TileCommand với command ID và dependency IDs, rồi schedule/manifest JSON sau khi kiểm thứ tự, shape và số giao dịch.',
 'Vector/exporter và các regression RTL dùng lịch để phát activation/weights, gom partial sums và bảo đảm O không chạy trước context.')
contract('native-inline-legacy_stage4_generator',
 'Nhận config rows/cols, VDD/nhiệt độ, path model SKY130, output_root và tập level cần sinh; mã leaf/cột/core có chân theo cùng core_pins.',
 'Ghi file leaf/column/macro SPICE, testbench chứa precharge/PWM/tải, tên phép đo vi sai/delay/energy và manifest jobs kèm oracle tổng nguyên.',
 'legacy_stage4_runner chạy manifest; legacy_stage5 nhận schematic và kết quả trước layout để đối chiếu sau extraction/PEX.')
contract('native-inline-legacy_stage4_runner',
 'Nhận manifest_path do generator ghi, stage filters, executable ngspice, timeout và số worker; mỗi job có deck và tập measurement bắt buộc.',
 'Ghi native log từng job, parse voltage/delay/energy cùng return code và version; tổng hợp report theo level, không nhận một log thiếu measurement là hoàn tất.',
 'Stage5 kiểm receipt của đúng deck trước layout; các bảng Stage4 đọc số đo và quyết định có tiếp tục mở rộng hierarchy hay không.')
contract('native-inline-legacy_stage5 native-restored-archive-030',
 'Nhận core schematic, RTL blackbox, hợp đồng pin/rows/cols, PDK technology files và receipt Stage4 hợp lệ; outline/pin phải cùng core4×4.',
 'Xuất/kiểm GDS, LEF có pad VGND, netlist extraction và PEX cùng receipts DRC/LVS; đếm128 NFET trước Netgen và ghi pre/post deltas nếu có phép đo.',
 'legacy_stage6 fit transfer từ các sample đã xác nhận; các phép quét PEX dùng netlist trích xuất; OpenLane preflight dùng LEF/GDS để gắn core vào top.')
contract('native-inline-legacy_stage6',
 'Nhận Stage1Result, config số và chuỗi report mạch trước/sau layout có các sample theo tổng nguyên/cột; điện áp theo volt, delay theo đơn vị report đã parse.',
 'Ghi characterization TT và mô hình CIMMacroModel gồm gain/miền đã đo; evaluate_mha trả sai số surrogate cùng số lượt ngoại suy, không tạo ADC code.',
 'Các cell phân tích transfer/decoder dùng model để xác định mức khó; reference MHA dùng output surrogate để phân biệt lỗi lượng tử và lỗi transfer.')
contract('native-inline-fresh-pilot native-restored-archive-036 native-restored-archive-039',
 'Nhận Case gồm activation4 hàng theo ACT_X2, weights4×4, PEX hoặc schematic nguồn, corner/VDD/nhiệt độ, load_ff theo fF và pwm_unit_ps theo ps.',
 'Sinh/chạy deck, lưu log và các sample BLP/BLN/vi sai theo cột và thời điểm; tính oracle độc lập, khoảng mức/gap theo volt và report cặp bị đảo thứ tự.',
 'story-transfer_error hiển thị baseline; các sweep tải/PWM dùng lại đúng cặp pattern; export_factorial chuyển bốn điều kiện mới sang factorial-result.')
contract('native-story-transfer_error native-story-candidate_result native-story-partition_result native-story-decoder_errors',
 'Nhận root và report/pilot tương ứng với mốc được trình bày: baseline, candidate, chẩn đoán decoder hoặc can thiệp partition. Dữ liệu có nhãn nguồn và điều kiện đo riêng.',
 'Tạo bảng/figure giữ nguyên số đo, số lỗi hoặc chênh lệch trước/sau; không tạo một conversion mới chỉ từ việc đọc report.',
 'Các cell sweep/decoder tiếp theo dùng nội dung này làm quyết định thiết kế; checker cuối chỉ chấm record fresh do Experiment và standalone-sync-conversions cung cấp.')
contract('native-restored-archive-042 native-restored-archive-045 native-restored-archive-048 factorial-result',
 'Nhận cùng cặp activation/weights đã lộ lỗi và các điểm (load_ff,pwm_unit_ps); report schematic/PEX/log xác định cột, thời điểm sample và netlist đã dùng.',
 'Trả/ghi điện áp từng mức, gap, zero-offset và kết quả ordering tại mỗi điểm. factorial-result đọc log thật để tính bốn ô2×2 và interaction, giữ fF/ps/mV được phân biệt.',
 'Candidate được đưa sang sweep/holdout; calibration-method chỉ tiến hành sau khi điểm đọc có cơ sở ordering, không dùng gap như một mã ADC.')
contract('native-restored-archive-051 native-restored-archive-063',
 'Nhận config MHA, danh sách payload đã dùng, candidate/model/PEX và calibration đã xác nhận; các activation/weights mới phải không trùng tập trước.',
 'Ghi deck/log của holdout mới với metadata và report đo/decoded errors; giữ fit và điều kiện mạch giống calibration để phép so độc lập có nghĩa.',
 'Các cell analyze_decoder/analyze_feature_holdout và bảng holdout đọc report này; không lấy nó quay lại dịch ngưỡng training.')
contract('native-restored-archive-054 native-restored-archive-057 native-restored-archive-060 native-restored-archive-066',
 'Nhận report training/holdout có stimulus, cột, sample time, điện áp vi sai/common-mode và noise/error budget theo volt; labels được tính lại từ input.',
 'Trả ngưỡng midpoint/feature predictor, bảng mức reachable, confusion/error counts và lựa chọn dựa trên training; các hàm analyze chỉ đọc/tính, không tự chạy ADC.',
 'Chọn hard cases và recipe2+2 dùng lỗi đo để đổi protocol; nguồn fit và nguồn đánh giá tiếp tục được tách khi chuyển sang partition/calibration.')
contract('native-restored-archive-069 native-restored-archive-072 native-restored-archive-075',
 'Nhận case4 hàng khó, trọng số16 ô giữ nguyên, hai nhóm hàng0–1/2–3, input/model/PEX đã kiểm và budget điện áp; calibration có mức reachable, holdout có pattern chưa dùng.',
 'Tạo hai deck con/case, đo partial sum theo phase/cột, fit các ngưỡng riêng trên calibration rồi decode/cộng lại cho holdout; ghi report calibration hoặc holdout của2+2.',
 'Partition-result giải thích kết quả; giao thức/threshold tương ứng là đầu vào cho controller regression2+2, không hoán đổi với fit affine ba điểm của SAR study.')
contract('native-restored-archive-078',
 'Nhận tên .lib corner thực trong model, bộ (corner,VDD,temperature) và các worst-case pair quyết định gap từ report TT trước đó.',
 'Sinh deck smoke PVT giữ pattern/PEX nhất quán, parse điện áp/gap tại từng điểm và ghi report so với TT.',
 'Bảng điều kiện vật lý dùng các điểm đã đo để nêu phạm vi kết quả; không đổi report chuẩn bị thành bằng chứng một full corner campaign đã hoàn tất.')
contract('native-restored-archive-085 native-restored-archive-088 native-restored-archive-091',
 'Nhận oracle fixed-point, ACT_X2/ternary, hệ số alpha_q12/scale và lịch handshake; stress bổ sung reset giữa giao dịch hoặc result_ready thấp,2+2 bổ sung phase.',
 'Ghi vector và testbench Verilog, biên dịch iverilog, chạy vvp, kiểm expected output/transaction count và lưu transcript/report regression.',
 'Top/controller implementation dùng interface đã kiểm; các phép chấm ADC và MHA phía sau vẫn đọc kết quả transistor/SAR riêng, không lấy RTL model lý tưởng thay số đo.')
contract('native-restored-archive-095 native-restored-archive-101',
 'Nhận root/tag, OpenLane config, wrapper RTL/blackbox, LEF/GDS của macro, macro placement và PDK; kiểm danh sách pin, SIZE và vị trí VGND pad.',
 'Trả preflight/audit với lỗi cụ thể hoặc ghi snapshot/metrics/view của recipe triển khai; graph GDS chỉ xác nhận hiện diện hierarchy, không tự chứng minh LVS.',
 'Cold runtime hiện tại dựng config mới từ bundle; streamout/GDS-audit/LVS/PG/STA kiểm các view và netlist thực sau routing.')
contract('native-inline-geometry_common native-inline-support',
 'Nhận Settings gồm root/cache/tag/reuse/timeout/jobs; runner nhận argv, cwd, env, input files và output files bắt buộc. Helper timing nhận text STA/SDC/Liberty; helper RC nhận mạng trích xuất.',
 'Tạo Flow và sổ outputs/receipts, ghi script snapshot/native.log/step.json, trả metric/check hoặc đường dẫn artifact đã kiểm. Runner báo lỗi khi timeout, return code hoặc file bắt buộc không hợp lệ.',
 'Các cell native environment/synthesis/render/LVS/power/timing gọi Flow.run; publish và fresh_activity dùng receipts để bàn giao và xác nhận kết quả thuộc phiên mới.')
contract('native-inline-pg-worker-source',
 'Nhận hệ số database units và geometry đã xác định của pad/strap M4/M5 ở vị trí macro.',
 'Trả tọa độ bridge theo đơn vị database để script kiểm/vẽ liên kết nguồn. Đây là helper được giữ để đọc cách xây geometry.',
 'Đường active power của standalone-runtime dùng native Tcl check_power_grid trên ODB mới và kiểm lỗi log; không nhận riêng tọa độ bridge là rail đã nối.')
contract('native-inline-waveforms raw-reader',
 'Nhận path raw ASCII của đúng conversion, transcript ngspice cùng tên vector/time window; thời gian trả về theo giây, điện áp theo volt.',
 'Trả dict time/node arrays, mẫu nội suy tại at_s và sampling witness gồm các mốc track/hold/settle; control_block tạo lệnh ghi đúng bộ vector vào raw.',
 'adc-waveform và waveform dùng vector để vẽ/kiểm thời điểm; conversion checker liên hệ witness với summary và SAR STATE tương ứng.')
contract('native-inline-klayout_checks',
 'Nhận file XML DRC và danh sách nhóm rule bắt buộc; phân biệt nhóm đã bật/đã hoàn tất với file report mới chỉ có phần đầu.',
 'Trả thống kê marker theo nhóm và điều kiện full_groups_clean có scope rõ; report timeout phải giữ trạng thái chưa hoàn tất.',
 'audit_gds/physical-reports dùng kết quả để trình bày DRC; số0 của router không được thay cho kết quả full-layout deck.')
contract('native-inline-adc_partition',
 'Nhận schematic nguồn ADC với subcircuit/chân và inventory515 signal capacitors, model PDK, diff/common-mode trong giới hạn nguồn cùng thời gian reset/start.',
 'Trả SPICE library/bench với node P/N, clock, sample và CDAC được mapping; fast_matrix giữ tụ và TG đầu vào, dùng bottom drivers tương đương để giảm thời gian giải.',
 'native-inline-cosim dùng cùng mapping/inventory để ghép SAR RTL với comparator và nguồn analog; mã ADC sau đó phải đến từ state/eoc thực của vòng co-simulation.')
contract('native-inline-cosim',
 'Nhận root, work, libngspice, activation4 hàng, ternary4×4 và column; RTL.read nhận STATE theo RTL_FIELDS, callback analog nhận thời gian và tên nguồn C API yêu cầu.',
 'Ghi case.json, rtl.log, ngspice.log, coupled.raw và summary.json cho conversion; trả ADC code, control timeline và các phép kiểm hoàn tất. Mỗi lần advance/clock trao đổi quyết định comparator giữa hai engine.',
 'Experiment.measure/many thu record, calibrate fit từ3 record riêng; validate-evidence/holdout/MHA đọc lại log/state và summary để chấm độc lập.')
contract('native-runall-partition-sources native-runall-calibration native-runall-measured-mha',
 'Nhận Flow, source SAR/analog/PDK đã kiểm và payload activation_x2, weights, column. Calibration dùng3 input riêng; projection nhận ma trận activation/trọng số và nhãn Q/K/V/O.',
 'Trả các receipt conversion cùng fit slope/offset, projection tensors và mha_end_to_end.json. Trong phiên có32 projection transactions nhưng30 payload projection duy nhất; case trùng chỉ dùng lại record của chính phiên.',
 'standalone-sync-conversions đo thêm8 challenge sau khóa fit, tạo evidence41 case; calibration-holdout và mha-recompute kiểm lại fit, mapping và các tensor từ record này.')
contract('native-runall-render-macros native-runall-render-top',
 'Nhận config/path GDS của core_acquisition, conditioner, ADC hoặc top và tên top cell cụ thể; có cờ required/leaves để chọn item cần xem.',
 'Ghi PNG dưới render_<name>/ và hiển thị trong output; catalog trả danh mục path/top, runner kiểm file ảnh hợp lệ trước khi đăng ký outputs.',
 'standalone-sync-physical sao ảnh của view đã kiểm sang review_data/figures; physical-reports hiển thị chúng cùng LVS/PG/STA, không dùng một ảnh từ lần chạy khác.')
contract('validate-evidence',
 'Nhận E[ cases ] trỏ stimulus/summary/log, mỗi stimulus có activation_x2, weights và column; log SAR phải có STATE/EOC/code nhất quán.',
 'Trả tập record hợp lệ, payload chuẩn hóa và oracle tổng nguyên; assert_disjoint xác nhận calibration và holdout không giao payload, lỗi bị reject trước chấm điểm.',
 'negative-controls cố tình làm hỏng bản sao record để thử checker; calibration-holdout fit/chấm chỉ trên record đã qua kiểm.')
contract('calibration-holdout',
 'Nhận3 calibration codes và oracle đã kiểm để tạo FROZEN=[slope,offset]; các case holdout mới chỉ cung cấp code và truth để chấm, không để fit lại.',
 'estimate trả tổng ước lượng chưa làm tròn; decode trả tổng nguyên; bảng observations lưu residual và mismatch trên38 holdouts.',
 'challenge-result và mha-recompute dùng cùng FROZEN; argument-verdict so lại fit với protocol đã ghi trước challenge.')
contract('native-runall-adc-waveform native-runall-mha-plots',
 'Nhận Flow cùng case receipt hoặc MHA report của phiên; case chỉ rõ raw/state/log, report chỉ rõ tensor/projected records.',
 'Ghi figure waveform comparator/sample/SAR hoặc figure tensor/error vào work directory, hiển thị ảnh với cùng đơn vị/node của record nguồn.',
 'Người đọc so trực quan với validate-evidence và mha-recompute; manifest và phần review giữ liên kết đến những ảnh của đúng phiên.')
contract('mha-recompute',
 'Nhận jobs mapping stage/row/column→case, activation/weights, record ADC đã kiểm và FROZEN; Q/K/V/O phải ghép theo đúng trục token/head.',
 'Trả tensor projection đo được, attention/context/output và hai relative L2: reference context lượng tử và reference context số thực; không lấy recorded_output làm oracle.',
 'results và argument-verdict tổng hợp sự đồng ý decode cùng sai số lượng tử ứng dụng; các con số được ghi trong review_results.json.')
contract('rtl-testbench rtl-native',
 'Nhận SAR RTL nguồn, stimulus/cấu hình/reset và code/control states cần đối chiếu; run_tool nhận argv, stdin tùy chọn, env và timeout.',
 'Ghi/biên dịch testbench, chạy vvp từng case, trả transcript cùng bảng pass/code/EOC. Dữ liệu so đến từ41 record đã kiểm của phiên.',
 'results nêu fresh_native_rtl_cases; đây là kiểm lại giao diện SAR và state, không thay phần ngspice đã tạo code analog ở conversion.')
contract('native-story-routing_progress',
 'Nhận root và các report/receipt implementation được chỉ định; số đo có tên tool/stage và trạng thái chạy riêng.',
 'Trả bảng tiến trình routing/violation và source của view đang được nối tới bước export; phần gọi ở phiên hiện tại chỉ dùng đường standalone được cấu hình.',
 'streamout lấy đúng routed database; GDS-audit, render và signal-lvs sau đó kiểm các view vừa xuất.')
contract('physical-reports',
 'Nhận E[physical] trỏ geometry.json, power.json, drc_summary.json, timing.native.log và netgen.log của top mới. slack nhận SETUP hoặc HOLD làm nhãn vùng marker.',
 'Trả setup/hold ns từ đúng đoạn log, in verdict Netgen cuối, rail status, số cell/instance/master và DRC status; hiển thị các PNG macro/top từ cùng review_data.',
 'klayout-native đọc GDS nén và render lại độc lập; argument-verdict/results đưa đúng scope vật lý và slack này vào kết luận.')
contract('native-restored-server-flow-provenance native-restored-server-flow-mha native-restored-server-flow-execute',
 'Nhận SETTINGS/tag của recipe server, root và các đường dẫn source/receipt; phần thân nằm dưới RUN_LEGACY_CAMPAIGNS nên định nghĩa có thể được giữ mà không gọi chiến dịch cũ.',
 'Hàm provenance trả file items/session snapshot; numerical_receipts trả nguồn reference/schedule; final_cli_report parse JSON report cuối nếu recipe CLI được chạy.',
 'Các cell server-flow review/render/postroute của cùng recipe dùng các object này; tuyến standalone active vẫn bàn giao từ flow.outputs mới ở runall-manifest.')
contract('native-story-dependencies native-story-final_results',
 'Nhận Flow cùng các refs outputs/receipts; final_results mở analog_adc_mha và gds_geometry_proof, dùng nominal_timing đã đo.',
 'Trả/in bảng calibration codes,32 transactions/30 pattern, L2, geometry, slack và top GDS; phần gọi dependencies của tuyến hiện tại ghi fresh_activity.json từ log mới.',
 'runall-manifest kiểm view cần bàn giao rồi full-lab-inventory xác nhận thứ tự89 native cells; không dùng vị trí cell trong notebook để suy provenance.')
contract('cim-edu-bootstrap',
 'Nhận _design_review_namespace với BUNDLE và OUT đã tạo, không mở checkout cũ hoặc result cũ.',
 'Tạo module riêng và magic cim_lesson; đặt EDU_ROOT=BUNDLE, EDU_OUT=OUT/cell_to_macro, chưa sinh mạch hay chạy solver.',
 'Tất cả các cell %%cim_lesson phía sau dùng chung bảng topology và helper trong module này mà không đè biến native/review.')
contract('cim-edu-format',
 'edu_decode nhận codes0…15 và scale_byte0…254; edu_quantize_block nhận vector32 số hữu hạn cùng tie=project/rne. Bảng EDU_MAG định nghĩa tám độ lớn E2M1.',
 'Trả giá trị decode hoặc cặp codes:uint8[32]/byte scale, in bảng16 nibble và ví dụ tie0.75; assert công thức ACT_X2×2^(E−128) và block exact-representable.',
 'ternary lesson dùng bảng ACT_X2; tiling lesson dùng decoder/scale để so tổng integer với phép chiếu đã decode.')
contract('cim-edu-ternary',
 'Nhận weight thuộc{-1,0,+1} và một trong15 activation ACT_X2 có dấu; sign activation chọn WLP/WLN.',
 'Trả mask WPOS/WNEG và dict PP/PN/NP/NN; vòng kiểm45 tổ hợp so tích nguyên với hướng bitline xả.',
 'leaf builder dùng cùng bốn trường hợp dấu để sinh transistor; bài DC9 dùng weight_bits để bias các gate đúng mã.')
contract('cim-edu-leaf',
 'Nhận EDU_BRANCHES chứa tag nhánh, BLP/BLN, gate trọng số, gate activation, node NPP/NPN/NNP/NNN; parser nhận văn bản inputs/core_acquisition.spice.',
 'Ghi ternary_cell.spice với tám NFET W/L0.84/0.15µm, trả EDU_SOURCE mapping subcircuit và assert từng dòng leaf khớp nguồn.',
 'schematic dùng bảng này để vẽ cùng tên thiết bị; column/array nhúng đúng interface; analog inventory và DC test mở rộng từ leaf vừa kiểm.')
contract('cim-edu-schematic cim-edu-device',
 'Nhận bảng bốn nhánh và các tọa độ vẽ; cực MOS mang D/G/S/B, gate WPOS/WNEG hoặc WLP/WLN, bulk VSUBS và W/L lấy từ source.',
 'Tạo sơ đồ vector và PNG có ký hiệu NMOS4 cực, phóng to thiết bị và minh họa active/poly/contact. Hình cấu trúc là khái niệm có chú thích, không phải GDS hay phép đo kích thước từ GDS.',
 'Người đọc so ký hiệu với tám dòng SPICE của leaf, sau đó theo column/array và các cell KLayout để xem view vật lý thực.')
contract('cim-edu-column',
 'Nhận rows=4 và interface leaf BLP/BLN/WLP/WLN/WPOS/WNEG/VGND/VSUBS đã đối chiếu; mỗi hàng có mask/control riêng.',
 'Trả subcircuit cột với4 XCELL dùng chung2 bitline,20 chân,32 NFET; ghi column_4x1.spice và assert khớp nguồn.',
 'core builder đặt bốn cột với bitline riêng, chia sẻ wordline theo hàng và mở32 chân trọng số của16 giao điểm.')
contract('cim-edu-array',
 'Nhận rows=4,cols=4 và các quy tắc đánh số chân; WPOS_r_c/WNEG_r_c theo giao điểm, WLP/WLN theo hàng, BLP/BLN theo cột.',
 'Trả core4×4 với4 XCOL,50 chân,16 leaf/128 NFET; ghi core_4x4.spice, kiểm source và vẽ sơ đồ tổ chức mảng.',
 'analog inventory thêm XACQ để thành core_acquisition; tiling chứng minh cách dùng lại core4 hàng cho block32 của định dạng số.')
contract('cim-edu-analog',
 'Nhận các block trong core_acquisition.spice và conditioner.spice; parser phân biệt model primitive với một subcircuit cần mở đệ quy.',
 'Trả Counter theo model, ghi hierarchy_inventory.json và bảng138 NFET/18 PFET/168 MIM của core+acquisition; assert riêng8 hold caps và160 load caps.',
 'Phần đọc macro giải thích HP/HN, mux và ADC; các phép đo native phía sau dùng schematic/PEX nguồn này thay vì một model tích ma trận lý tưởng.')
contract('cim-edu-leaf-spice',
 'Nhận EDU_LEAF đúng nguồn, NFET TT/mismatch của PDK và9 cặp weight/sign; fixture giữ hai bitline1V, gate0/1.8V, temperature27°C và geometric scale1µm.',
 'Ghi leaf_dc9.spice, native log và JSON với differential_current_a; đọc I(VBN)−I(VBP), kiểm sign/zero9 trạng thái và vẽ dòng theoµA.',
 'Kết quả xác nhận hướng dòng leaf; PWM/tải/sample theo thời gian tiếp tục được kiểm ở factorial/PEX/ADC waveform, không suy tuyến tính transient từ9 điểm DC.')
contract('cim-edu-tiling',
 'Nhận ACT_X2[32], ternary[32,4], scale_byte và alpha[4]; ví dụ chọn col_v=1, beta/residual0 để giữ đúng bài base-only.',
 'Trả output[4], partial[8,4] và phases[8,2,4]; assert phase sum=tile sum, tile sum=ACT_X2@T và output=reference đã decode scale.',
 'Schedule/controller2+2 mở rộng cùng hợp đồng sang64 conversion cho block32×4; MHA study dùng mapping record riêng được kiểm ở các cell phía sau.')

def data_contract(cell_id):
    if cell_id not in IO:raise KeyError('Thiếu mô tả dữ liệu '+cell_id)
    return IO[cell_id]

def glossary_for(text):
    found=[]
    semiconductor=bool(re.search(r'\b(?:NMOS|NFET|PMOS|PFET|transistor|MOS)\b',text,re.I))
    for term,description in GLOSSARY.items():
        if term in ('D','G','S','B','W','L','D/G/S/B','W/L') and not semiconductor:continue
        # Unicode word boundaries avoid treating the D in Vietnamese "Dữ"
        # as a drain terminal. Underscores may delimit signal-name segments.
        pattern=r'(?<![^\W_])'+re.escape(term)+r'(?![^\W_])'
        if term in ('8T','2T'):pattern=re.escape(term)+r'(?![^\W_])'
        if term in {'fF','ps','ns','µm','mV','µA','MHz'}:
            pattern=r'(?<![^\W\d_])'+re.escape(term)+r'(?![^\W_])'
        sensitive={'DEF','FF','Q','K','V','O','D','G','S','B','W','L','C','fF','ps','ns','µm','mV','µA','MHz'}
        flags=0 if term in sensitive else re.I
        if re.search(pattern,text,flags):found.append((term,description))
    return found


# Output reader uses measured fields and regenerates plots from packed JSON.
OVERRIDES[('native-inline-history','review_reports')]='Đọc JSON của phép đo hoặc report hiện tại, chọn số liệu chính thành bảng, ghi nguồn/ngày của số liệu và dựng đường transfer khi có các khoảng đo; không chạy lại simulator khi chỉ đọc report.'
OVERRIDES[('native-inline-history','review_reports.scan')]='Duyệt trường scalar và các cột phân tích, giữ số lỗi, overlap, gap, sai số và kết quả kiểm; bỏ dữ liệu debug dài trước khi chọn các dòng kết quả chính.'
OVERRIDES[('native-inline-history','plot_saved_transfer')]='Dựng lại hình điện áp vi sai theo tổng nguyên từ các khoảng min/max có thật trong JSON; đọc đúng report đi kèm notebook và trả True khi đã vẽ được.'
