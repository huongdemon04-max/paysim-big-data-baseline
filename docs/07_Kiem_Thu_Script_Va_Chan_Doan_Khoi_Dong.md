# KIỂM THỬ SCRIPT VÀ CHẨN ĐOÁN KHỞI ĐỘNG PAYSIM

## 1. Phạm vi bàn giao

Kiểm tra ngày 24/10/2026: `start.sh`, `stop.sh`, `reset.sh`, `start.bat`, `stop.bat`, `reset.bat` và các script chuẩn bị dữ liệu/entrypoint liên quan. Không thay công thức Spark, model, truy vấn MongoDB hoặc giao diện.

Các lượt RESET xác nhận dùng project Docker kiểm thử riêng, nhận diện qua `COMPOSE_PROJECT_NAME`. Volume của project thực hành `paysim-big-data-baseline` được giữ nguyên. Đây là kiểm thử xóa volume thật của project thử nghiệm, không chỉ thử nhánh hủy.

---

## 2. Ảnh lỗi NameNode trên Mac ARM nói lên điều gì?

Ảnh cung cấp ba bằng chứng:

1. Docker host là `linux/arm64/v8`, nhưng image Hadoop dùng để chạy là `linux/amd64`.
2. NameNode không đạt healthcheck; Compose kết thúc với `dependency failed to start`.
3. Spark, replayer và dashboard còn ở trạng thái `Created` vì phụ thuộc NameNode.

**Ảnh chưa cho biết tiến trình NameNode lỗi ở đâu.** Cảnh báo kiến trúc xác nhận có runtime khác kiến trúc máy; muốn kết luận crash QEMU, thiếu RAM hay lỗi metadata phải đọc log và trạng thái container.

Trong đợt điều tra trước của dự án, đã có log Hadoop cũ báo `qemu: uncaught target signal 11` khi chạy AMD64 trên ARM. Bản sửa native đã có trong source hiện tại: Hadoop dùng `build: ./hadoop`; Java chọn native architecture, thư viện native AMD64 được loại khỏi runtime; healthcheck dùng Python/JMX thay vì khởi động thêm JVM. Launcher chọn `linux/arm64` khi Docker daemon báo ARM64. Kết quả cũ không được dùng để khẳng định chiếc máy trong ảnh cũng gặp đúng crash đó.

Dòng `FROM --platform=linux/amd64 apache/hadoop:3.4.1` trong stage `distribution` của Dockerfile chỉ lấy các file Hadoop. Stage runtime phía sau dùng Java native; không chạy binary AMD64 của stage nguồn. Vì vậy cần kiểm tra **image container đang chạy**, không suy ra kiến trúc runtime chỉ từ stage nguồn.

### Đối chiếu trên máy gặp lỗi

Chạy trong thư mục dự án, dùng được trong PowerShell và terminal macOS/Linux:

```bash
git log -1 --oneline
git status --short
docker info --format '{{.Architecture}}'
docker compose -f docker-compose.yml images
docker compose -f docker-compose.yml ps -a
docker compose -f docker-compose.yml logs --no-color --tail=150 namenode datanode
```

Lấy container ID của NameNode:

```bash
docker compose -f docker-compose.yml ps -aq namenode
```

Thay `CONTAINER_ID` trong lệnh dưới bằng ID vừa lấy:

```bash
docker inspect --format '{{.Config.Image}} {{json .State}} {{json .Config.Healthcheck}}' CONTAINER_ID
```

Bản hiện tại phải dùng healthcheck `/usr/local/bin/hdfs-healthcheck`, timeout 30 giây. Nếu còn image runtime `apache/hadoop:3.4.1` hoặc healthcheck JVM cũ, kiểm tra source/cấu hình và build lại bằng launcher. Giữ lại bài làm đang sửa trước khi cập nhật source; không reset volume để chữa lỗi sai image.

---

## 3. `startup-diagnostics.txt` không phải nguyên nhân lỗi

Thông báo này chỉ xuất hiện khi lệnh `docker compose ... up --build --wait` trả mã lỗi. Một thông báo chung có thể đại diện cho nhiều nguyên nhân:

| Bằng chứng cần tìm | Nhóm nguyên nhân | Hướng xử lý |
|---|---|---|
| `failed to solve`, tải package/image thất bại | Build hoặc kết nối mạng/registry | Đọc lỗi đầu tiên trong `startup-output.log` |
| `SyntaxError`, marker BEFORE/AFTER mất dấu `#` | Source bài thực hành không hợp lệ | Sửa đúng dòng Python rồi build lại |
| Cảnh báo AMD64/ARM64 kèm `qemu ... signal 11` | Runtime sai kiến trúc và crash khi giả lập | Dùng source native hiện tại, build bằng launcher |
| `OOMKilled: true` | Container bị hết bộ nhớ | Kiểm tra giới hạn RAM/overlay và bộ nhớ Docker |
| `Safe mode ON` rồi tự hết | HDFS đang chờ DataNode/block report | Chờ readiness; không tự kết luận hỏng dữ liệu |
| `no live DataNode`, DataNode crash | NameNode chưa có DataNode hoạt động | Đọc log cả hai dịch vụ |
| Metadata không đầy đủ / cluster ID không khớp | Volume hoặc metadata HDFS | Giữ dữ liệu, xác minh log trước khi quyết định phục hồi/reset |
| `port is already allocated` | Cổng host đã bị chiếm | Xác định dịch vụ đang dùng cổng |
| Docker daemon không truy cập được | Docker Desktop/WSL chưa sẵn sàng | Kiểm tra `docker version` và `docker info` |

Các lỗi preflight như chưa mở Docker, Compose không phù hợp, thiếu RAM hoặc dữ liệu sai checksum được báo trước lệnh `up`; không phải tất cả đều tạo diagnostics. Kiểm tra thời gian trong file để tránh đọc nhầm file của lượt cũ.

### Khoảng trống đã sửa trong lượt này

Trước đây diagnostics chỉ gom trạng thái và log container sau khi `up` lỗi. Nếu **build thất bại trước khi tạo container**, file có thể không chứa lỗi build gốc. Cả Bash và PowerShell nay ghi output build/start vào `startup-output.log`, đưa nội dung đó cùng mã thoát Compose vào `startup-diagnostics.txt`. Đã thử lỗi build có chủ đích `TEST_BUILD_FAILURE`/exit 42 trên Docker thật; cả hai launcher trả exit 1 và giữ được nguyên nhân trong diagnostics.

Thông báo runtime và README dùng văn phong trung lập, không còn yêu cầu gửi log cho giảng viên. Giữ file chẩn đoán vì nó cần để tìm nguyên nhân, không xóa cơ chế thu thập lỗi.

---

## 4. Quyền chạy và lỗi RESET trên Windows

- Tất cả file `.sh`, kể cả `hadoop/entrypoint.sh`, có quyền executable và dùng LF. Git ghi nhận thay đổi mode của entrypoint từ `100644` sang `100755`.
- `.bat` dùng CRLF. Windows chạy bằng CMD; không cần bit executable của POSIX.
- Hai file PowerShell giữ UTF-8 BOM để Windows PowerShell 5.1 đọc đúng tiếng Việt. `start.bat` gọi bằng `-ExecutionPolicy Bypass` cho tiến trình đó.
- Đã kiểm tra đường dẫn có dấu cách và gọi script từ thư mục khác.
- `reset.bat` xóa biến `CONFIRMATION` trước `set /p`. Trước sửa, biến môi trường kế thừa `CONFIRMATION=RESET` có thể khiến nhấn Enter rỗng vẫn xác nhận xóa. Sau sửa, Enter rỗng hủy; chỉ nhập đúng `RESET` mới xóa. [Test tái hiện trên bản cũ](evidence/scripts-20261024/reset-before-regression.txt) thất bại đúng nhánh này; bản sửa đạt.
- `reset.bat` trả exit 0 rõ ràng khi thành công, exit 1 khi Docker lỗi. Các script stop/reset không báo thành công khi lệnh Docker thất bại.

Nếu phân phối bằng ZIP hoặc qua filesystem làm mất quyền Unix, chạy một lần:

```bash
chmod +x start.sh stop.sh reset.sh scripts/prepare-data.sh hadoop/entrypoint.sh spark/entrypoint.sh
```

Git clone giữ mode đã commit. Thay đổi mode còn trong working tree chỉ có hiệu lực với bản bàn giao sau khi được đưa vào commit/gói phát hành.

---

## 5. Kết quả và evidence

Kết quả từng lượt được ghi tại [thư mục evidence](evidence/scripts-20261024/). Bản kiểm thử dùng WSL Ubuntu AMD64, Docker Desktop Engine 28.4.0, Docker VM khoảng 7,76 GiB RAM. Bộ `.bat` chạy bằng Windows CMD + Windows PowerShell 5.1 và `docker.exe` thật, trên cùng Docker Desktop của máy này.

Không có máy Mac ARM vật lý trong lượt thử ngày 24/10; không suy rộng thành bảo đảm mọi hệ điều hành/cấu hình đều chạy được. Các tình huống chọn ARM/native và chế độ nhẹ được kiểm tra bằng test launcher; đây không phải chạy lại toàn pipeline trên Mac ARM hoặc VM RAM 4 GB.

| Kiểm tra | Kết quả | Evidence |
|---|---|---|
| Bash start trên volume mới và chạy lại | Exit 0, các dịch vụ có healthcheck đều healthy | [Start mới](evidence/scripts-20261024/start-linux.txt), [start bản cuối](evidence/scripts-20261024/start-linux-final.txt), [trạng thái](evidence/scripts-20261024/linux-healthy.txt) |
| Bash stop, hủy reset, xác nhận reset | Exit 0; hủy giữ 9 container; stop không còn container chạy; reset xóa container/volume kiểm thử, giữ CSV | [Kết quả](evidence/scripts-20261024/linux-cycle.json) |
| Windows start/stop/reset | Cả bốn lượt exit 0; start healthy; Enter rỗng hủy dù kế thừa RESET; stop/reset xác nhận đúng | [Kết quả](evidence/scripts-20261024/windows-cycle.json), [start](evidence/scripts-20261024/start-windows.txt), [trạng thái](evidence/scripts-20261024/windows-healthy.txt), [stop](evidence/scripts-20261024/stop-windows.txt), [reset](evidence/scripts-20261024/reset-windows-confirm.txt) |
| Lỗi build thật trên Bash và Windows | Exit 1; diagnostics giữ `TEST_BUILD_FAILURE` và mã thoát Compose | [Kết quả](evidence/scripts-20261024/build-failure.json), [Bash](evidence/scripts-20261024/diagnostics-build-linux.txt), [Windows](evidence/scripts-20261024/diagnostics-build-windows.txt) |
| Regression launcher, download, quyền chạy và nhánh lỗi | 17 test đạt, 23 tình huống con đạt | [Log](evidence/scripts-20261024/tests-final.txt) |
| Quyền executable, LF/CRLF, BOM và cú pháp Bash | PASS | [Danh sách file và SHA-256](evidence/scripts-20261024/handoff-files.json) |

### Chạy lại bộ kiểm thử không xóa dữ liệu Docker

```bash
python -m pytest -q tests/test_startup.py tests/test_prepare_data.py tests/test_windows_launcher.py tests/test_windows_batch.py tests/test_script_handoff.py
```

Dùng môi trường Python có `pytest` theo `tests/requirements.txt`. Các bài kiểm thử nhánh lỗi dùng Docker giả hoặc dữ liệu tạm; các lượt Docker thật được ghi riêng phía trên. Test Windows sẽ skip nếu không có CMD/PowerShell; test Bash sẽ skip trên Python Windows native.

Sau kiểm thử, các project thử nghiệm không còn container hoặc volume. Project thực hành ban đầu vẫn giữ chín container ở trạng thái dừng và bốn volume như trước lượt chạy: [bằng chứng giữ dữ liệu](evidence/scripts-20261024/original-project-preserved.json).
