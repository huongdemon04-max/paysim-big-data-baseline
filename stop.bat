@echo off
chcp 65001 >nul
cd /d "%~dp0"
docker compose -f docker-compose.yml stop
if errorlevel 1 (
  echo Không thể dừng hệ thống. Kiểm tra Docker Desktop.
  pause
  exit /b 1
)
echo Đã dừng hệ thống.
pause
exit /b 0
