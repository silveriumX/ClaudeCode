@echo off
title TelegramHub Launcher
color 0B

echo.
echo ========================================
echo        TelegramHub CRM Launcher
echo ========================================
echo.

cd /d "C:\Users\Admin\Documents\Cursor\Projects\TelegramHub\server"

echo [*] Starting Main Server (port 8765)...
start "TelegramHub Main" cmd /k "python main.py"

timeout /t 3 /nobreak >nul

echo [*] Starting Auth Server (port 8766)...
start "TelegramHub Auth" cmd /k "python auth_web.py"

echo.
echo ========================================
echo          Servers Started!
echo ========================================
echo.
echo   Main Panel:    http://127.0.0.1:8765
echo   Auth Panel:    http://127.0.0.1:8766
echo.
echo   Close this window when done.
echo   Server windows will stay open.
echo.

pause
