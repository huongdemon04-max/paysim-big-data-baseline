@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File ".\scripts\start.ps1"
set "START_RESULT=%ERRORLEVEL%"
pause
exit /b %START_RESULT%
