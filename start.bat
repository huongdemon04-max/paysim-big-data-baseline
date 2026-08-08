@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\prepare-data.ps1"
if errorlevel 1 (
  echo Không thể chuẩn bị bộ dữ liệu PaySim.
  pause
  exit /b 1
)

echo Khởi động hệ thống PaySim Big Data...
docker compose up -d --build
if errorlevel 1 (
  echo Khởi động Docker Compose thất bại.
  echo.
  echo Trạng thái dịch vụ:
  docker compose ps -a
  echo.
  echo Nhật ký NameNode, DataNode và Spark:
  docker compose logs --no-color --tail=200 namenode datanode spark
  echo.
  echo Nếu nhật ký báo SafeModeException hoặc corrupt blocks, chạy reset.bat.
  pause
  exit /b 1
)

echo Đang chờ bảng điều khiển khởi động...
timeout /t 20 /nobreak >nul
start http://127.0.0.1:8501
echo Bảng điều khiển: http://127.0.0.1:8501
echo Giao diện HDFS:  http://127.0.0.1:9870
echo Giao diện Spark: http://127.0.0.1:4040
pause
