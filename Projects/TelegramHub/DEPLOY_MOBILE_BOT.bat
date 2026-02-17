@echo off
chcp 65001 > nul
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0deploy_mobile_bot_now.ps1"
pause
