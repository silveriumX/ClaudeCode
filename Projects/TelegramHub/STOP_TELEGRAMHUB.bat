@echo off
title TelegramHub Stop
color 0C

echo.
echo ========================================
echo       Stopping TelegramHub...
echo ========================================
echo.

taskkill /F /IM python.exe 2>nul

echo.
echo [+] All Python processes stopped.
echo.

timeout /t 2 /nobreak >nul
