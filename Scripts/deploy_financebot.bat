@REM NOTE: Set VPS_LINUX_PASSWORD env var before running
@echo off
chcp 65001 >nul
echo === Finance Bot Deploy via plink/pscp ===
echo.

set VPS_HOST=45.12.72.147
set VPS_USER=root
set VPS_PATH=/root/finance_bot
set LOCAL_BASE=C:\Users\Admin\Documents\Cursor\Projects\FinanceBot

echo [1] Uploading sheets.py...
pscp -pw "%VPS_LINUX_PASSWORD%" "%LOCAL_BASE%\sheets.py" %VPS_USER%@%VPS_HOST%:%VPS_PATH%/sheets.py
if errorlevel 1 (
    echo ERROR: Failed to upload sheets.py
    pause
    exit /b 1
)

echo [2] Uploading handlers/request.py...
pscp -pw "%VPS_LINUX_PASSWORD%" "%LOCAL_BASE%\handlers\request.py" %VPS_USER%@%VPS_HOST%:%VPS_PATH%/handlers/request.py
if errorlevel 1 (
    echo ERROR: Failed to upload request.py
    pause
    exit /b 1
)

echo [3] Uploading handlers/start.py...
pscp -pw "%VPS_LINUX_PASSWORD%" "%LOCAL_BASE%\handlers\start.py" %VPS_USER%@%VPS_HOST%:%VPS_PATH%/handlers/start.py
if errorlevel 1 (
    echo ERROR: Failed to upload start.py
    pause
    exit /b 1
)

echo [4] Uploading config.py...
pscp -pw "%VPS_LINUX_PASSWORD%" "%LOCAL_BASE%\config.py" %VPS_USER%@%VPS_HOST%:%VPS_PATH%/config.py
if errorlevel 1 (
    echo ERROR: Failed to upload config.py
    pause
    exit /b 1
)

echo.
echo [5] Restarting bot...
plink -pw "%VPS_LINUX_PASSWORD%" %VPS_USER%@%VPS_HOST% "systemctl restart financebot"

echo.
echo [6] Checking status...
plink -pw "%VPS_LINUX_PASSWORD%" %VPS_USER%@%VPS_HOST% "systemctl status financebot --no-pager -n 15"

echo.
echo [7] Checking logs...
plink -pw "%VPS_LINUX_PASSWORD%" %VPS_USER%@%VPS_HOST% "journalctl -u financebot -n 30 --no-pager"

echo.
echo === DEPLOY COMPLETE ===
pause
