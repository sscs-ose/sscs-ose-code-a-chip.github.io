# Rà soát hồ sơ Code-a-Chip ISSCC 2027 — 31/10/2026

## Kết luận

Repo đã có notebook, mã nguồn, license, tác giả, tài liệu tái lập và bằng
chứng kết quả để đóng gói bài nộp. Hai archive đã có trên Drive với quyền
anyone/reader, xác minh qua metadata ngày 31/10/2026. Người dùng đã chỉ định
Dang Vinh Pham làm đại diện đội; TEAM.json và README đã được cập nhật.
Đây là rà soát tĩnh; không chạy notebook, mô phỏng, kiểm thử, huấn luyện,
layout, hay các script verify/quick_review của dự án.

## Quy định đối chiếu

- README chính thức: https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/README.md
- How to Apply: https://github.com/sscs-ose/sscs-ose-code-a-chip.github.io/blob/main/howtoapply.md
- Thư mục: `ISSCC27/submitted_notebooks/AutoMX_CIM/`.
- Chỉ thêm/sửa file trong thư mục dự án này ở repo cuộc thi.
- Hạn: 31/10/2026, 11:59 AM Pacific, tức 01:59 ngày 01/11/2026 tại Việt Nam.
- How to Apply còn ghi ISSCC26; đường dẫn ISSCC27 ở README hiện hành được ưu tiên.
- Không sửa PR sau hạn. Không thấy yêu cầu nộp riêng paper PDF, video hay slide.

## Những gì đã có

| Hạng mục | Bằng chứng trong repo |
|---|---|
| Notebook có kết quả để đọc | 509 cell: 304 Markdown, 205 code; cả 205 code có execution count và output; không có output loại error; 49 output chứa hình |
| Ý tưởng, thiết kế, phương pháp, kết quả | Introduction, các chương từ MXFP4/8T/core đến SAR, MHA, physical implementation, application và electrical closure |
| Thành viên và liên hệ | Bảng ở đầu notebook, TEAM.json, CITATION.cff; bốn thành viên, contact Minh D. Nguyen |
| License mở | LICENSE Apache-2.0, NOTICE.md, licenses/, license của IP và SAR upstream |
| Trích dẫn | Mục References trong notebook và README; data/notebook_references.md |
| Mã nguồn và cấu hình | automx_cim/, scripts/, rtl/, ip/, configs/, third_party/ |
| Môi trường và toolchain | environment.yml, requirements.txt, standalone.json, docs/MEASUREMENT_TOOLCHAIN.md, docs/opensta_version.json |
| Tái lập | docs/REPRODUCIBILITY.md, RELEASE_ASSETS.md, runtime_assets.json, launcher và script restore |
| Kết quả gốc | results/final_run/, results/execution/, data/checkpoints/, exports/ |
| Layout | Hai GDS nén và hình render trong exports/; cuộc thi không bắt buộc GDS |

Kiểm kê ban đầu: 2.311 file Git, 110.643.933 byte (~105,52 MiB).
Notebook 12.669.329 byte (~12,08 MiB); file lớn nhất là archive MHA IP
29.431.993 byte (~28,07 MiB). Không file nào vượt 50 MiB hoặc 100 MiB.
Đây là dung lượng file làm việc, không phải kích thước dữ liệu Git sau nén.
49 module nội bộ được tham chiếu bằng import trực tiếp trong notebook đều
có file/module tương ứng. Các liên kết Markdown đến file cục bộ trong
README, NOTICE, RELEASE_ASSETS và hướng dẫn tái lập không bị thiếu.

Các số liệu và PASS lịch sử là kết quả đã lưu của lần chạy trước. Rà soát
này không xác minh lại tính đúng của phép đo hoặc khả năng Run All trên máy mới.

## Việc cần làm trước khi nộp

1. **Đã xác minh quyền public của bộ runtime.** Folder và cả hai archive
   có quyền `anyone / reader`, kiểm tra qua metadata Drive ngày 31/10/2026.
   Tên và dung lượng khớp manifest. Không tải toàn bộ archive trong phiên này.
   - `AutoMX_CIM_runtime_inputs_20261030.tar.gz`: 1.454.841.643 byte,
     bắt buộc cho fresh full run.
   - `AutoMX_CIM_measurement_records_20261029.tar.gz`: 429.895.973 byte,
     tùy chọn để xem hồ sơ chi tiết.
   Không cần tải lên lại hoặc đẩy hai archive lớn này vào Git của cuộc thi.
   Đã cập nhật runtime_assets.json và tài liệu tái lập để phản ánh quyền public.
2. **Đã chỉ định đại diện đội: Dang Vinh Pham.** Người dùng đã xác nhận
   người đại diện nhận giải, dự ISSCC 2027 trực tiếp và trình bày poster
   nếu được chọn. Thông tin đã có trong TEAM.json, README và bản nháp PR.
   Minh D. Nguyen vẫn là Lead/contact. Không bắt buộc là thành viên IEEE/SSCS.
3. **Fork và push nhánh đã chuẩn bị.** Bản clone nằm trong
   `.submission/code-a-chip/`, nhánh `submit/automx-cim-isscc27`, remote
   `upstream` trỏ về repo chính thức. Toàn bộ bộ hồ sơ được đặt trong thư
   mục dự án quy định; không lồng thêm `.git` của AutoMX-CIM.
4. **Mở PR về `sscs-ose/sscs-ose-code-a-chip.github.io:main`.** Tiêu đề và
   nội dung gợi ý ở `.submission/PR_TITLE.txt` và `.submission/PR_BODY.md`.
   Kiểm tra tab Files changed chỉ có đường dẫn dự án. Fork hoặc push đơn
   thuần chưa phải là nộp bài; phải có PR trước hạn.

## Những điểm đã sửa và nên cân nhắc

- Chỉ sửa tài liệu NOTICE và operating contract để thay các tham chiếu
  đến file provenance/release không tồn tại bằng file có thật trong bộ nộp.
- Thêm quy tắc bỏ qua `/.submission/` để bản clone cuộc thi không bị đưa
  ngược vào repo dự án.
- Không sửa notebook, mã thực thi, kết quả hoặc log cũ.
- Metadata notebook vẫn chứa các bản ghi kiểm tra lịch sử với số cell cũ,
  đường dẫn Linux gốc và email rỗng trong một trường metadata. Bảng tác giả
  hiển thị và TEAM.json có email; các giá trị lịch sử không phải lỗi output
  hiện tại. Có thể giữ để bảo toàn provenance; không cần chạy lại để nộp.
- Công bố đúng phạm vi: native sáu frame/384 conversion dùng ideal-50-ps
  diagnostic; tiết kiệm 60,943% là child-digital energy trong phép so sánh
  đã chỉ định. Không biến thành tuyên bố toàn chip tốt hơn digital baseline
  hoặc clean foundry signoff. README hiện đã giải thích giới hạn này.

## Tình trạng GitHub trong phiên chuẩn bị

Đã tải repo chính thức và chuẩn bị bản sao cục bộ. Người dùng đã yêu cầu
fork, commit và push sau khi hoàn thành hai việc trên. Windows Credential
Manager xác minh được tài khoản GitHub `Chris1606` ngoài sandbox; bản chuẩn
bị dùng tài khoản này để fork và push, giữ nguyên remote repo AutoMX-CIM gốc.

Trạng thái, URL và SHA sau publish được lưu cục bộ trong
`.submission/PUBLISH_RESULT.json`. Tiêu đề và nội dung PR đã được soạn ở
`.submission/PR_TITLE.txt` và `.submission/PR_BODY.md`, gồm người đại diện
Dang Vinh Pham và trạng thái chia sẻ Drive. Push nhánh chưa được tính là
nộp bài: cần mở PR về repo chính thức, base `main`, trước hạn.
