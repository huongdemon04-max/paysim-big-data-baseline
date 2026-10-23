@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo Lệnh này xóa dữ liệu Docker của riêng baseline PaySim: Kafka, HDFS và MongoDB.
set "CONFIRMATION="
set /p "CONFIRMATION=Nhập RESET để tiếp tục: "
if not "%CONFIRMATION%"=="RESET" (
  echo Đã hủy.
  pause
  exit /b 0
)

docker compose -f docker-compose.yml down -v --remove-orphans
if errorlevel 1 (
  echo Không thể đặt lại dữ liệu Docker của baseline.
  pause
  exit /b 1
)

echo Hệ thống đã được đặt lại. Tệp paysim.csv gốc không bị thay đổi.
pause
exit /b 0
