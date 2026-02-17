@echo off
chcp 65001 >nul
echo ========================================
echo Деплой Finance Bot на VPS
echo ========================================
echo.

cd /d "%~dp0"
python deploy_finance_bot.py

echo.
pause
