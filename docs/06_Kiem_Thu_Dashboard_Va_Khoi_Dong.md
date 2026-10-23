# KIỂM THỬ DASHBOARD VÀ SCRIPT KHỞI ĐỘNG PAYSIM

## 1. Môi trường và phạm vi

Thực nghiệm ngày 23/10/2026 trên WSL Ubuntu, Docker Desktop 4.47.0 / Engine 28.4.0, Linux AMD64; Docker VM có khoảng 7.76 GiB RAM. Windows PowerShell 5.1 và CMD được gọi qua Windows interop để kiểm thử launcher với Docker giả.

Đã xóa 18 container có sẵn theo yêu cầu trước khi chạy. Images và volumes được giữ nguyên. Vì vậy đây là **dựng lại container, giữ dữ liệu**, không phải reset toàn bộ dữ liệu. Thông tin kiểm kê riêng của các project khác không đưa vào repository.

Không có kết quả chạy native Mac ARM hoặc một máy Windows độc lập trong biên bản này. Không thể bảo đảm “mọi máy” khi chưa biết cấu hình RAM/CPU, trạng thái Docker daemon, proxy, cổng bận và phiên bản source trên máy đó.

## 2. Ba phiên bản giao diện

Ảnh gốc chụp bằng Chromium/Playwright, không chỉnh sửa. Desktop 1600 × 1600; mobile 390 × 844, sidebar được đóng bằng nút có sẵn. Đây là ảnh viewport; những trang dài hơn vẫn cần cuộn. Các trang dài được kiểm tra nội dung bằng AppTest.

| Giao diện | Live | 10 tracks | Fraud & Business | Giao dịch | Mobile |
|---|---|---|---|---|---|
| BEFORE | [Ảnh](evidence/dashboard-ui/baseline-1-desktop.png) | [Ảnh](evidence/dashboard-ui/baseline-2-desktop.png) | [Ảnh](evidence/dashboard-ui/baseline-3-desktop.png) | [Ảnh](evidence/dashboard-ui/baseline-4-desktop.png) | [Ảnh](evidence/dashboard-ui/baseline-mobile.png) |
| 9A Operations | [Ảnh](evidence/dashboard-ui/operations-1-desktop.png) | [Ảnh](evidence/dashboard-ui/operations-2-desktop.png) | [Ảnh](evidence/dashboard-ui/operations-3-desktop.png) | [Ảnh](evidence/dashboard-ui/operations-4-desktop.png) | [Ảnh](evidence/dashboard-ui/operations-mobile.png) |
| 9B Report | [Ảnh](evidence/dashboard-ui/report-1-desktop.png) | [Ảnh](evidence/dashboard-ui/report-2-desktop.png) | [Ảnh](evidence/dashboard-ui/report-3-desktop.png) | [Ảnh](evidence/dashboard-ui/report-4-desktop.png) | [Ảnh](evidence/dashboard-ui/report-mobile.png) |
| 9C Studio | [Ảnh](evidence/dashboard-ui/studio-1-desktop.png) | [Ảnh](evidence/dashboard-ui/studio-2-desktop.png) | [Ảnh](evidence/dashboard-ui/studio-3-desktop.png) | [Ảnh](evidence/dashboard-ui/studio-4-desktop.png) | [Ảnh](evidence/dashboard-ui/studio-mobile.png) |

### BEFORE

![BEFORE](evidence/dashboard-ui/baseline-1-desktop.png)

### AFTER 9A

![Operations](evidence/dashboard-ui/operations-1-desktop.png)

### AFTER 9B

![Report](evidence/dashboard-ui/report-1-desktop.png)

### AFTER 9C

![Studio — trang mặc định là giao dịch](evidence/dashboard-ui/studio-4-desktop.png)

## 3. Nguồn dữ liệu và bằng chứng giữ nguyên kết quả

Snapshot lấy từ **pipeline thật** Kafka → Spark → HDFS/MongoDB, run `run-20261023-155039`, lúc `2026-10-23T15:52:33Z`. Dữ liệu được sao chép vào database riêng `paysim_ui_evidence_20261023`, không ghi đè nguồn.

| Chỉ số chung trên cả bốn giao diện | Giá trị |
|---|---:|
| Nguồn đã phát | 5.200 |
| Spark đã xử lý | 4.700 |
| Đang chờ | 500 |
| Fraud alerts | 1.004 |
| Alert rate | 21,36% |
| Ingest | 50,0 events/s |
| Processing throughput | 70,3 events/s |
| End-to-end p95 | 14.905 ms |

Snapshot gồm 10 micro-batch, 5 nhóm nghiệp vụ, 60 giao dịch gần nhất và 1.004 alert documents; trang Fraud vẫn chỉ lấy 300 alerts mới nhất như BEFORE. Tổng nhóm = processed và alert count = TP + FP đã được kiểm tra trước khi sao chép. `processed_total` của telemetry mới nhất cũng khớp evaluation; revision evaluation không đổi trong quá trình đọc.

**Nhãn LIVE trong ảnh là trạng thái run được sao chép**, không có nghĩa database evidence tiếp tục nhận giao dịch. Freshness và thời gian query thay đổi theo thời điểm mở màn hình. Không dùng các số đó để chứng minh bằng nhau tuyệt đối.

- [Snapshot gốc và metadata](evidence/dashboard-ui/snapshot.json)
- [Đối chiếu KPI trên snapshot thật](evidence/dashboard-ui/browser-equivalence.json)
- [Kết quả browser và các KPI đọc từ DOM](evidence/dashboard-ui/browser-results.json)
- [Code lấy snapshot](../tests/snapshot_dashboard.py)
- [Code chạy browser/chụp ảnh](../tests/capture_dashboard.py)

AppTest đối chiếu sáu KPI chung của ba AFTER với BEFORE trên fixture cố định ở cả bốn trang. Bốn trường hợp database rỗng hiển thị trạng thái chờ và không exception. Biểu đồ và bố cục khác nhau theo mục đích mỗi phiên bản; không yêu cầu toàn bộ cấu trúc chart giống nhau. [Đối chiếu AST](evidence/dashboard-ui/data-logic-preservation.json) xác nhận các phép gán truy vấn/tính toán snapshot được giữ nguyên khi tách lớp trình bày.

## 4. Điều tra launcher và các sửa đổi

| Phát hiện | Sửa đổi | Cách kiểm chứng |
|---|---|---|
| `docker compose up --help \| grep -q` dưới `pipefail` có thể báo nhầm Compose cũ khi output dài nhiều dòng | Đọc hết help vào biến, kiểm tra chuỗi sau khi lệnh kết thúc | Bản HEAD cũ tái hiện exit 1; bản sửa đạt với cùng output giả. [Evidence](evidence/dashboard-ui/launcher-before-regression.json) |
| `stop.bat` không kiểm tra exit code, vẫn in thông báo đã dừng | Kiểm tra `errorlevel`, trả exit 1 khi Docker lỗi | CMD thật + docker.exe giả trả 7; wrapper trả 1 và không báo thành công |
| `stop/reset` gọi Compose không chỉ rõ file, dễ chịu ảnh hưởng `COMPOSE_FILE` khác với startup | Dùng rõ `-f docker-compose.yml` | Kiểm tra lệnh và test wrapper; stop/down không cần cấu hình tài nguyên overlay để nhận diện cùng project |
| Cấu hình Compose sai chỉ được phát hiện sau bước chuẩn bị dữ liệu | `compose config --quiet` trước khi chuẩn bị dữ liệu | Test cấu hình lỗi: không tải data, không gọi `up` |
| Mở browser thất bại có thể khiến PowerShell báo startup thất bại dù dịch vụ đã lên | Tách lỗi mở browser khỏi trạng thái Docker | PowerShell thật, tình huống không có browser trả thành công |
| Windows PowerShell dùng parser mặc định của `Invoke-WebRequest` | `-UseBasicParsing`, TLS 1.2, timeout, retry; dọn tệp tải dở | Review nhánh tải; không cố ý tải lại toàn bộ dataset trên Windows trong lần này |
| Bash có thể để lại tệp tải dở nếu curl thất bại | Trap dọn `.download`, connect timeout và tổng timeout | Kiểm tra shell và đường đi lỗi |
| Comment bài thực hành bị bỏ dấu `#` làm Python lỗi sau khi container chạy | Compile Python ngay lúc build image Spark và dashboard | Build thật và kiểm tra cú pháp |
| `/tmp/pipeline-ready` còn trong container qua stop/start | Entry point xóa dấu ready cũ trước tiến trình Spark mới | Kiểm tra restart thật; không thay đổi công thức pipeline |
| Thông báo yêu cầu gửi log cho một vai trò cụ thể, kèm dump log dài trên terminal | Văn phong trung lập; chỉ báo file `startup-diagnostics.txt`, giữ log chi tiết trong file | Rà code và test nhánh startup lỗi |

Các lỗi trên **không chứng minh** nguyên nhân mọi feedback trước đây. Không có log máy sinh viên trong yêu cầu hiện tại. Lỗi Docker daemon/WSL hoặc source cũ cần kiểm tra trên chính máy xảy ra lỗi; reset volumes không sửa được việc Docker daemon không hoạt động.

Lần chạy đầu đã lên healthy, nhưng exit cuối của shell bị ảnh hưởng vì file launcher đang được sửa trong lúc nó chạy. Lần đó không được tính là launcher PASS. Các lần xác nhận cuối dùng file ổn định và ghi mã thoát riêng.

## 5. Kiểm thử và kết quả cuối

| Kiểm tra | Kết quả | Evidence |
|---|---|---|
| Vòng kiểm thử launcher/download và UI trước khi đổi bố cục lần cuối | 22 test đạt, 23 tình huống con đạt | [Log](evidence/dashboard-ui/unit-tests.txt) |
| UI sau khi viết lại ba bố cục | 7 test đạt (gồm đối chiếu 3 × 4 trang và trạng thái rỗng) | [Log](evidence/dashboard-ui/ui-redesign-tests.txt) |
| Wrapper Windows CMD | start truyền mã lỗi; stop báo lỗi; reset hủy; reset lỗi đều đúng | [Log bổ sung](evidence/dashboard-ui/windows-batch-tests.txt) |
| KPI trên snapshot thật | 12/12 cặp trang có sáu KPI chung bằng nhau | [JSON](evidence/dashboard-ui/browser-equivalence.json) |
| Browser | 16 trang desktop + 4 mobile, không exception; đủ bốn trang mỗi phiên bản | [JSON](evidence/dashboard-ui/browser-results.json) |
| Dashboard chạy trong image cuối | HTTP 8501 và render Operations, không exception | [Ảnh Docker thật](evidence/dashboard-ui/docker-live.png), [DOM](evidence/dashboard-ui/docker-live.json) |
| `start.sh` tiêu chuẩn | Exit 0; Spark, MongoDB, Kafka, NameNode và Streamlit healthy | [Log startup](evidence/dashboard-ui/startup-standard.txt) |
| `stop.sh` | Exit 0, các container đã dừng | [Log](evidence/dashboard-ui/stop.txt) |
| `reset.sh` hủy thao tác | Exit 0, không xóa volumes | [Log](evidence/dashboard-ui/reset-cancel.txt) |
| Restart Spark | Dấu ready cũ bị xóa, health `starting` trước query mới | [Log](evidence/dashboard-ui/readiness-restart.txt) |
| Chế độ nhẹ, model chưa tồn tại | Train 300.000 dòng thành công; Spark healthy; run mới xử lý 300/300 events, khoảng 10 events/s, aggregate/transformation PASS | [Startup](evidence/dashboard-ui/startup-low-memory.txt), [Spark](evidence/dashboard-ui/low-memory-spark.txt), [Số liệu](evidence/dashboard-ui/low-memory-live.json), [Giới hạn RAM](evidence/dashboard-ui/low-memory-runtime.txt) |

Lượt nhẹ dùng đúng overlay của dự án, Spark heap 768 MiB / giới hạn container 1.5 GiB, model mới tại `validation-low-memory-20261023-decision-tree-v1`. Docker VM vẫn có 7.76 GiB: đây là kiểm chứng **giới hạn từng container**, chưa phải kiểm chứng tổng VM chỉ có 4 GB hoặc chạy bền nhiều giờ. Mô hình nghiệp vụ và 300.000 dòng train không bị rút gọn.

Một lượt test Windows interop gặp `WSL ERROR: UtilAcceptVsock ... accept4 failed 110` trước khi PowerShell thực thi script; lượt chạy lại khi stack đã dừng đạt. Lỗi này được phân loại là môi trường kiểm thử, không dùng làm bằng chứng lỗi launcher.

Các test cần POSIX Bash được skip trên Python Windows native; các test PowerShell/CMD được skip nếu không có shell tương ứng. Log của phiên này chạy trên WSL có Windows interop, không thay cho xác nhận một máy Windows độc lập.

Sau thực nghiệm, đã trả hệ thống về cấu hình tiêu chuẩn bằng `start.sh`, exit 0. Dashboard mặc định là 9A tại <http://127.0.0.1:8501>.

- [Log khởi động lại cấu hình tiêu chuẩn](evidence/dashboard-ui/startup-restored-standard.txt)
- [Trạng thái các dịch vụ cuối](evidence/dashboard-ui/final-services.txt)
- [Phiên bản runtime](evidence/dashboard-ui/runtime-versions.txt)
- [Đối chiếu SHA-256 của năm file dashboard với image đang chạy](evidence/dashboard-ui/image-source-verification.json)
- [SHA-256 source dùng kiểm thử](evidence/dashboard-ui/source-sha256.txt)

Database snapshot riêng và model kiểm thử chế độ nhẹ được giữ để có thể tra cứu/tái lập; không thay đổi đường dẫn model mặc định trong Compose.

## 6. Tái lập kiểm tra giao diện

Khởi động pipeline rồi tạo database evidence **mới**; script từ chối ghi đè database đã tồn tại:

```bash
python tests/snapshot_dashboard.py --database paysim_ui_evidence_new --output snapshot.json
```

macOS/Linux:

```bash
MONGO_DATABASE=paysim_ui_evidence_new python tests/capture_dashboard.py --output captures
```

PowerShell:

```powershell
$env:MONGO_DATABASE = 'paysim_ui_evidence_new'
python tests/capture_dashboard.py --output captures
```

Cài Chromium trước bằng `python -m playwright install chromium`. Công cụ chụp dùng cổng 8510 và entrypoint tạm trỏ vào đúng lõi/các module giao diện; không tự đổi lựa chọn trong `dashboard/app.py`. Snapshot không phải giao dịch MongoDB nhiều collection; để đóng băng tuyệt đối, tạm dừng các tiến trình ghi sau khi batch hoàn tất rồi lấy snapshot.
